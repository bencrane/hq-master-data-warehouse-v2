import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from db import get_pool
from routers.workflows import (
    extract_domain_from_email,
    normalize_email,
    normalize_linkedin_company_url,
)

router = APIRouter(prefix="/api/workflows", tags=["workflows-single"])

INGEST_API_KEY = os.getenv("INGEST_API_KEY")
GENERIC_EMAIL_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "protonmail.com",
    "mail.com",
}


class ResolveDomainFromEmailSingleRequest(BaseModel):
    work_email: str | None = None


class ResolveDomainFromLinkedinSingleRequest(BaseModel):
    company_linkedin_url: str | None = None


def _require_ingest_key(x_api_key: str | None) -> None:
    if not INGEST_API_KEY:
        raise HTTPException(status_code=500, detail="INGEST_API_KEY is not configured")
    if x_api_key != INGEST_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/resolve-domain-from-email/single")
async def resolve_domain_from_email_single(
    request: ResolveDomainFromEmailSingleRequest,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_ingest_key(x_api_key)

    work_email = normalize_email(request.work_email)
    if not work_email:
        return {"resolved": False, "reason": "missing_input"}

    pool = get_pool()

    lookup_row = await pool.fetchrow(
        """
        SELECT domain
        FROM reference.email_to_person
        WHERE email = $1
          AND domain IS NOT NULL
        LIMIT 1
        """,
        work_email,
    )

    if lookup_row and lookup_row["domain"]:
        return {
            "resolved": True,
            "domain": lookup_row["domain"].strip().lower(),
            "source": "reference.email_to_person",
        }

    raw_domain = extract_domain_from_email(work_email)
    if not raw_domain:
        return {"resolved": False, "reason": "missing_input"}

    if raw_domain in GENERIC_EMAIL_PROVIDERS:
        return {
            "resolved": False,
            "reason": "generic_email_provider",
            "raw_domain": raw_domain,
        }

    return {"resolved": True, "domain": raw_domain, "source": "email_extract"}


@router.post("/resolve-domain-from-linkedin/single")
async def resolve_domain_from_linkedin_single(
    request: ResolveDomainFromLinkedinSingleRequest,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_ingest_key(x_api_key)

    company_linkedin_url = normalize_linkedin_company_url(request.company_linkedin_url)
    if not company_linkedin_url:
        return {"resolved": False, "reason": "missing_input"}

    pool = get_pool()
    match_row = await pool.fetchrow(
        """
        SELECT domain
        FROM core.companies
        WHERE linkedin_url = $1
          AND domain IS NOT NULL
        LIMIT 1
        """,
        company_linkedin_url,
    )

    if not match_row or not match_row["domain"]:
        return {"resolved": False, "reason": "not_found_in_core_companies"}

    return {
        "resolved": True,
        "domain": match_row["domain"].strip().lower(),
        "source": "core.companies",
    }
