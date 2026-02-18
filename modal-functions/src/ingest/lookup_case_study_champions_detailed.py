"""
Case Study Champions Detailed Lookup Endpoint

Returns champions with testimonials for a given vendor domain.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class ChampionsDetailedLookupRequest(BaseModel):
    """Request model for detailed champions lookup."""
    domain: str  # origin_company_domain (vendor domain)


DATABASE_URL = "postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_champions_detailed(request: ChampionsDetailedLookupRequest) -> dict:
    """
    Lookup case study champions with testimonials by vendor domain.
    Joins core.case_study_champions with extracted.parallel_case_study_champions for testimonials.
    """
    import psycopg2

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Query champions with testimonials
        query = """
            SELECT
                csc.full_name,
                csc.job_title,
                csc.company_name,
                csc.company_domain,
                csc.case_study_url,
                csc.source,
                pcc.testimonial,
                cf.linkedin_url as company_linkedin_url
            FROM core.case_study_champions csc
            LEFT JOIN extracted.parallel_case_study_champions pcc
                ON LOWER(TRIM(csc.full_name)) = LOWER(TRIM(pcc.full_name))
                AND csc.company_domain = pcc.customer_company_domain
            LEFT JOIN core.companies_full cf
                ON csc.company_domain = cf.domain
            WHERE csc.origin_company_domain = %s
        """
        cur.execute(query, (request.domain,))
        rows = cur.fetchall()

        champions = []
        for row in rows:
            champions.append({
                "full_name": row[0],
                "job_title": row[1],
                "company_name": row[2],
                "company_domain": row[3],
                "case_study_url": row[4],
                "source": row[5],
                "testimonial": row[6],
                "company_linkedin_url": row[7],
            })

        cur.close()
        conn.close()

        return {
            "success": True,
            "domain": request.domain,
            "champion_count": len(champions),
            "champions": champions,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "domain": request.domain,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
