import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from db import get_pool
from routers.workflows import (
    extract_domain_from_email,
    normalize_domain,
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


class ResolveCompanyNameSingleRequest(BaseModel):
    company_name: str | None = None


class ResolveLinkedinFromDomainSingleRequest(BaseModel):
    domain: str | None = None


class ResolvePersonLinkedinFromEmailSingleRequest(BaseModel):
    work_email: str | None = None


class ResolveCompanyLocationFromDomainSingleRequest(BaseModel):
    domain: str | None = None


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


def _normalize_company_name_input(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


@router.post("/resolve-company-name/single")
async def resolve_company_name_single(
    request: ResolveCompanyNameSingleRequest,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_ingest_key(x_api_key)

    company_name = _normalize_company_name_input(request.company_name)
    if not company_name:
        return {"resolved": False, "reason": "missing_input"}

    pool = get_pool()
    existing_row = await pool.fetchrow(
        """
        SELECT domain, cleaned_company_name
        FROM extracted.cleaned_company_names
        WHERE lower(trim(original_company_name)) = lower($1)
           OR lower(trim(cleaned_company_name)) = lower($1)
        ORDER BY CASE
            WHEN lower(trim(cleaned_company_name)) = lower($1) THEN 0
            ELSE 1
        END, updated_at DESC NULLS LAST
        LIMIT 1
        """,
        company_name,
    )

    if existing_row and existing_row["domain"]:
        return {
            "resolved": True,
            "domain": normalize_domain(existing_row["domain"]),
            "cleaned_company_name": _normalize_company_name_input(existing_row["cleaned_company_name"]),
            "source": "extracted.cleaned_company_names",
        }

    return {
        "resolved": False,
        "reason": "not_found_in_extracted_cleaned_company_names",
    }


@router.post("/resolve-linkedin-from-domain/single")
async def resolve_linkedin_from_domain_single(
    request: ResolveLinkedinFromDomainSingleRequest,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_ingest_key(x_api_key)

    domain = normalize_domain(request.domain)
    if not domain:
        return {"resolved": False, "reason": "missing_input"}

    pool = get_pool()
    match_row = await pool.fetchrow(
        """
        SELECT linkedin_url
        FROM core.companies
        WHERE domain = $1
          AND linkedin_url IS NOT NULL
        LIMIT 1
        """,
        domain,
    )

    if not match_row or not match_row["linkedin_url"]:
        return {"resolved": False, "reason": "not_found_in_core_companies"}

    return {
        "resolved": True,
        "company_linkedin_url": match_row["linkedin_url"],
        "source": "core.companies",
    }


@router.post("/resolve-person-linkedin-from-email/single")
async def resolve_person_linkedin_from_email_single(
    request: ResolvePersonLinkedinFromEmailSingleRequest,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_ingest_key(x_api_key)

    work_email = normalize_email(request.work_email)
    if not work_email:
        return {"resolved": False, "reason": "missing_input"}

    pool = get_pool()
    match_row = await pool.fetchrow(
        """
        SELECT person_linkedin_url
        FROM reference.email_to_person
        WHERE email = $1
          AND person_linkedin_url IS NOT NULL
        LIMIT 1
        """,
        work_email,
    )

    if not match_row or not match_row["person_linkedin_url"]:
        return {"resolved": False, "reason": "not_found_in_reference"}

    return {
        "resolved": True,
        "person_linkedin_url": match_row["person_linkedin_url"],
        "source": "reference.email_to_person",
    }


@router.post("/resolve-company-location-from-domain/single")
async def resolve_company_location_from_domain_single(
    request: ResolveCompanyLocationFromDomainSingleRequest,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    _require_ingest_key(x_api_key)

    domain = normalize_domain(request.domain)
    if not domain:
        return {"resolved": False, "reason": "missing_input"}

    pool = get_pool()
    match_row = await pool.fetchrow(
        """
        SELECT city, state, country
        FROM core.company_locations
        WHERE domain = $1
          AND (city IS NOT NULL OR state IS NOT NULL OR country IS NOT NULL)
        LIMIT 1
        """,
        domain,
    )

    if not match_row:
        return {"resolved": False, "reason": "not_found_in_core_company_locations"}

    return {
        "resolved": True,
        "company_city": match_row["city"],
        "company_state": match_row["state"],
        "company_country": match_row["country"],
        "source": "core.company_locations",
    }


