"""
Bright Data Job Posting Validation.

Checks whether a job posting appears active based on Bright Data Indeed and
LinkedIn job listing tables using domain-first matching with optional
company-name fallback.
"""

import os

import modal

from config import app, image

DATABASE_URL = os.getenv("DATABASE_URL")


def _query_indeed_matches(cur, company_domain: str, job_title: str, company_name: str | None) -> dict:
    cur.execute(
        """
        SELECT
            COUNT(*)::int AS match_count,
            COALESCE(BOOL_OR(is_expired), false) AS any_expired,
            COALESCE(BOOL_AND(COALESCE(is_expired, false)), false) AS all_expired,
            MAX(ingested_at) AS most_recent_ingested_at
        FROM raw.brightdata_indeed_job_listings
        WHERE resolved_company_domain = %s
          AND job_title ILIKE %s
        """,
        (company_domain, f"%{job_title}%"),
    )
    row = cur.fetchone()
    match_count = int(row[0] or 0)
    if match_count > 0:
        return {
            "match_count": match_count,
            "any_expired": bool(row[1]),
            "all_expired": bool(row[2]),
            "most_recent_ingested_at": row[3],
            "matched_by": "domain",
        }

    if company_name:
        cur.execute(
            """
            SELECT
                COUNT(*)::int AS match_count,
                COALESCE(BOOL_OR(is_expired), false) AS any_expired,
                COALESCE(BOOL_AND(COALESCE(is_expired, false)), false) AS all_expired,
                MAX(ingested_at) AS most_recent_ingested_at
            FROM raw.brightdata_indeed_job_listings
            WHERE company_name ILIKE %s
              AND job_title ILIKE %s
            """,
            (f"%{company_name}%", f"%{job_title}%"),
        )
        row = cur.fetchone()
        fallback_count = int(row[0] or 0)
        if fallback_count > 0:
            return {
                "match_count": fallback_count,
                "any_expired": bool(row[1]),
                "all_expired": bool(row[2]),
                "most_recent_ingested_at": row[3],
                "matched_by": "company_name",
            }

    return {
        "match_count": 0,
        "any_expired": False,
        "all_expired": False,
        "most_recent_ingested_at": None,
        "matched_by": "none",
    }


def _query_linkedin_matches(cur, company_domain: str, job_title: str, company_name: str | None) -> dict:
    cur.execute(
        """
        SELECT
            COUNT(*)::int AS match_count,
            MAX(ingested_at) AS most_recent_ingested_at
        FROM raw.brightdata_linkedin_job_listings
        WHERE resolved_company_domain = %s
          AND job_title ILIKE %s
        """,
        (company_domain, f"%{job_title}%"),
    )
    row = cur.fetchone()
    match_count = int(row[0] or 0)
    if match_count > 0:
        return {
            "match_count": match_count,
            "most_recent_ingested_at": row[1],
            "matched_by": "domain",
        }

    if company_name:
        cur.execute(
            """
            SELECT
                COUNT(*)::int AS match_count,
                MAX(ingested_at) AS most_recent_ingested_at
            FROM raw.brightdata_linkedin_job_listings
            WHERE company_name ILIKE %s
              AND job_title ILIKE %s
            """,
            (f"%{company_name}%", f"%{job_title}%"),
        )
        row = cur.fetchone()
        fallback_count = int(row[0] or 0)
        if fallback_count > 0:
            return {
                "match_count": fallback_count,
                "most_recent_ingested_at": row[1],
                "matched_by": "company_name",
            }

    return {
        "match_count": 0,
        "most_recent_ingested_at": None,
        "matched_by": "none",
    }


def _derive_validation_result(indeed: dict, linkedin: dict) -> str:
    found_any = indeed["match_count"] > 0 or linkedin["match_count"] > 0
    indeed_found = indeed["match_count"] > 0

    if not found_any:
        return "unknown"
    if indeed_found and indeed["all_expired"]:
        return "expired"
    if found_any and not indeed["any_expired"]:
        return "active"
    return "likely_closed"


def _derive_confidence(indeed: dict, linkedin: dict) -> str:
    if indeed["matched_by"] == "domain" or linkedin["matched_by"] == "domain":
        return "high"
    if indeed["match_count"] > 0 or linkedin["match_count"] > 0:
        return "medium"
    return "low"


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("brightdata-db-url"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def validate_job_posting_active(
    company_domain: str,
    job_title: str,
    company_name: str | None = None,
) -> dict:
    import psycopg2

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not configured")

    company_domain_norm = (company_domain or "").strip().lower()
    job_title_norm = (job_title or "").strip()
    company_name_norm = (company_name or "").strip() or None

    if not company_domain_norm:
        raise ValueError("company_domain is required")
    if not job_title_norm:
        raise ValueError("job_title is required")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            indeed_stats = _query_indeed_matches(
                cur=cur,
                company_domain=company_domain_norm,
                job_title=job_title_norm,
                company_name=company_name_norm,
            )
            linkedin_stats = _query_linkedin_matches(
                cur=cur,
                company_domain=company_domain_norm,
                job_title=job_title_norm,
                company_name=company_name_norm,
            )

        validation_result = _derive_validation_result(indeed_stats, linkedin_stats)
        confidence = _derive_confidence(indeed_stats, linkedin_stats)

        return {
            "company_domain": company_domain_norm,
            "job_title": job_title_norm,
            "company_name": company_name_norm,
            "indeed": {
                "found": indeed_stats["match_count"] > 0,
                "match_count": indeed_stats["match_count"],
                "any_expired": indeed_stats["any_expired"],
                "most_recent_ingested_at": (
                    indeed_stats["most_recent_ingested_at"].isoformat()
                    if indeed_stats["most_recent_ingested_at"]
                    else None
                ),
                "matched_by": indeed_stats["matched_by"],
            },
            "linkedin": {
                "found": linkedin_stats["match_count"] > 0,
                "match_count": linkedin_stats["match_count"],
                "most_recent_ingested_at": (
                    linkedin_stats["most_recent_ingested_at"].isoformat()
                    if linkedin_stats["most_recent_ingested_at"]
                    else None
                ),
                "matched_by": linkedin_stats["matched_by"],
            },
            "validation_result": validation_result,
            "confidence": confidence,
        }
    finally:
        conn.close()
