import os
import re
import json
import httpx
from fastapi import APIRouter
from db import get_pool

MODAL_SEARCH_PARALLEL_AI_URL = os.getenv(
    "MODAL_SEARCH_PARALLEL_AI_URL",
    "https://bencrane--hq-master-data-ingest-search-parallel-ai.modal.run"
)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def normalize_null(value):
    """Convert 'null' string to None, trim whitespace."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.lower() == "null" or value == "":
            return None
    return value


def normalize_title_case(value):
    """Trim, null check, and title case."""
    value = normalize_null(value)
    if value is None:
        return None
    return value.title()


def normalize_domain(value):
    """
    Strip https://, http://, www., trailing slashes, URL paths.
    Result: clean domain only (e.g., 'stripe.com').
    """
    value = normalize_null(value)
    if value is None:
        return None

    # Remove protocol
    value = re.sub(r'^https?://', '', value, flags=re.IGNORECASE)
    # Remove www.
    value = re.sub(r'^www\.', '', value, flags=re.IGNORECASE)
    # Remove paths, query strings, fragments (keep only domain)
    value = value.split('/')[0].split('?')[0].split('#')[0]
    # Remove trailing dots
    value = value.rstrip('.')
    # Lowercase
    value = value.lower()

    return value if value else None


def normalize_email(value):
    """Trim, lowercase, null check."""
    value = normalize_null(value)
    if value is None:
        return None
    return value.lower()


def normalize_linkedin_person_url(value):
    """
    Normalize to format: https://www.linkedin.com/in/{slug}
    Strip query params, trailing slashes, fix http:// to https://, add www.
    """
    value = normalize_null(value)
    if value is None:
        return None

    # Extract the slug from various formats
    # Patterns: linkedin.com/in/slug, www.linkedin.com/in/slug, etc.
    match = re.search(r'linkedin\.com/in/([^/?#]+)', value, re.IGNORECASE)
    if match:
        slug = match.group(1).rstrip('/')
        return f"https://www.linkedin.com/in/{slug}"

    return value  # Return as-is if pattern doesn't match


def normalize_linkedin_company_url(value):
    """
    Normalize to format: https://www.linkedin.com/company/{slug}
    Strip query params, trailing slashes, fix http:// to https://, add www.
    """
    value = normalize_null(value)
    if value is None:
        return None

    # Extract the slug from various formats
    match = re.search(r'linkedin\.com/company/([^/?#]+)', value, re.IGNORECASE)
    if match:
        slug = match.group(1).rstrip('/')
        return f"https://www.linkedin.com/company/{slug}"

    return value  # Return as-is if pattern doesn't match


def normalize_full_name(first_name, last_name, raw_full_name):
    """
    Build full_name from normalized first/last.
    If first_name/last_name are null but full_name exists, use and split it.
    """
    # If we have both first and last, build from them
    if first_name and last_name:
        return f"{first_name} {last_name}"

    # If we have only one, use what we have
    if first_name and not last_name:
        return first_name
    if last_name and not first_name:
        return last_name

    # If no first/last but we have raw full_name, use it
    raw_full_name = normalize_null(raw_full_name)
    if raw_full_name:
        return raw_full_name.title()

    return None


def derive_first_last_from_full(full_name):
    """
    Split full_name on first space to derive first_name and last_name.
    Returns (first_name, last_name) tuple.
    """
    if not full_name:
        return None, None

    parts = full_name.strip().split(' ', 1)
    first_name = parts[0].title() if parts[0] else None
    last_name = parts[1].title() if len(parts) > 1 and parts[1] else None

    return first_name, last_name


def normalize_record(raw_record):
    """Apply all normalization rules to a raw record."""
    # Get raw_payload for fields that might only be there
    raw_payload = raw_record.get("raw_payload") or {}
    if isinstance(raw_payload, str):
        raw_payload = json.loads(raw_payload)

    # Normalize first_name and last_name
    first_name = normalize_title_case(raw_record.get("first_name"))
    last_name = normalize_title_case(raw_record.get("last_name"))
    raw_full_name = raw_record.get("full_name")

    # If first_name/last_name are null but full_name exists, derive them
    if not first_name and not last_name and raw_full_name:
        derived_first, derived_last = derive_first_last_from_full(normalize_null(raw_full_name))
        first_name = derived_first
        last_name = derived_last

    # Build full_name
    full_name = normalize_full_name(first_name, last_name, raw_full_name)

    return {
        "raw_data_id": raw_record.get("id"),
        "client_domain": raw_record.get("client_domain"),

        # Person fields
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "person_linkedin_url": normalize_linkedin_person_url(raw_record.get("person_linkedin_url")),
        "person_city": normalize_title_case(raw_record.get("person_city")),
        "person_state": normalize_title_case(raw_record.get("person_state")),
        "person_country": normalize_title_case(raw_record.get("person_country")),
        "work_email": normalize_email(raw_record.get("work_email")),
        "phone_number": normalize_null(raw_record.get("phone_number")),

        # Company fields (company_name: trim only, no casing)
        "company_name": normalize_null(raw_record.get("company_name")),
        "domain": normalize_domain(raw_record.get("domain")),
        "company_linkedin_url": normalize_linkedin_company_url(raw_record.get("company_linkedin_url")),
        "company_city": normalize_title_case(raw_record.get("company_city")),
        "company_state": normalize_title_case(raw_record.get("company_state")),
        "company_country": normalize_title_case(raw_record.get("company_country")),

        # Additional fields from raw_payload
        "title": normalize_null(raw_payload.get("title")),
        "status": normalize_null(raw_payload.get("status")),
        "notes": normalize_null(raw_payload.get("notes")),
    }


@router.post("/normalize")
async def normalize_records(payload: dict):
    """
    Normalize a batch of raw records from hq.clients_raw_data.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_raw_data
    }

    Or to normalize all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Writes normalized results to hq.clients_normalized_crm_data.
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch raw records
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, client_domain, first_name, last_name, full_name,
                   person_linkedin_url, person_city, person_state, person_country,
                   work_email, phone_number, company_name, domain,
                   company_linkedin_url, company_city, company_state, company_country,
                   raw_payload
            FROM hq.clients_raw_data
            WHERE id = ANY($1::uuid[])
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, client_domain, first_name, last_name, full_name,
                   person_linkedin_url, person_city, person_state, person_country,
                   work_email, phone_number, company_name, domain,
                   company_linkedin_url, company_city, company_state, company_country,
                   raw_payload
            FROM hq.clients_raw_data
            WHERE client_domain = $1
        """, client_domain)

    if not rows:
        return {"success": True, "records_processed": 0, "message": "No records found"}

    # Normalize and insert
    records_processed = 0
    errors = []

    for raw_record in rows:
        try:
            normalized = normalize_record(dict(raw_record))

            await pool.execute("""
                INSERT INTO hq.clients_normalized_crm_data (
                    raw_data_id, client_domain,
                    first_name, last_name, full_name,
                    person_linkedin_url, person_city, person_state, person_country,
                    work_email, phone_number,
                    company_name, domain, company_linkedin_url,
                    company_city, company_state, company_country,
                    title, status, notes
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT (raw_data_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    full_name = EXCLUDED.full_name,
                    person_linkedin_url = EXCLUDED.person_linkedin_url,
                    person_city = EXCLUDED.person_city,
                    person_state = EXCLUDED.person_state,
                    person_country = EXCLUDED.person_country,
                    work_email = EXCLUDED.work_email,
                    phone_number = EXCLUDED.phone_number,
                    company_name = EXCLUDED.company_name,
                    domain = EXCLUDED.domain,
                    company_linkedin_url = EXCLUDED.company_linkedin_url,
                    company_city = EXCLUDED.company_city,
                    company_state = EXCLUDED.company_state,
                    company_country = EXCLUDED.company_country,
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    notes = EXCLUDED.notes,
                    normalized_at = NOW(),
                    updated_at = NOW()
            """,
                normalized["raw_data_id"],
                normalized["client_domain"],
                normalized["first_name"],
                normalized["last_name"],
                normalized["full_name"],
                normalized["person_linkedin_url"],
                normalized["person_city"],
                normalized["person_state"],
                normalized["person_country"],
                normalized["work_email"],
                normalized["phone_number"],
                normalized["company_name"],
                normalized["domain"],
                normalized["company_linkedin_url"],
                normalized["company_city"],
                normalized["company_state"],
                normalized["company_country"],
                normalized["title"],
                normalized["status"],
                normalized["notes"],
            )
            records_processed += 1

        except Exception as e:
            errors.append({"raw_data_id": str(raw_record["id"]), "error": str(e)})

    return {
        "success": True,
        "records_processed": records_processed,
        "errors": errors if errors else None
    }


async def call_parallel_ai_for_company_name(domain: str) -> str | None:
    """
    Call Parallel AI to get cleaned company name for a domain.
    Returns the cleaned company name or None if failed.
    """
    objective = (
        f"Given this domain: {domain}, return the company name formatted as you would use it "
        "in a professional email. Example: stripe.com → Stripe. "
        "Not all caps, not all lowercase, not the legal entity name. "
        "Return ONLY the company name, nothing else."
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                MODAL_SEARCH_PARALLEL_AI_URL,
                json={
                    "objective": objective,
                    "domain": domain,
                    "mode": "fast",
                    "max_results": 1,
                }
            )
            if response.status_code == 200:
                result = response.json()
                # Extract the answer from Parallel AI response
                answer = result.get("answer") or result.get("result") or result.get("response")
                if answer and isinstance(answer, str):
                    # Clean up the response - take first line, strip whitespace
                    cleaned = answer.strip().split('\n')[0].strip()
                    # Remove quotes if present
                    cleaned = cleaned.strip('"\'')
                    return cleaned if cleaned else None
    except Exception as e:
        print(f"Parallel AI error for {domain}: {e}")

    return None


@router.post("/resolve-company-name")
async def resolve_company_name(payload: dict):
    """
    Resolve cleaned company names for normalized records.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_normalized_crm_data
    }

    Or to resolve all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Logic:
    1. Look up domain in extracted.cleaned_company_names
    2. If found → use it, source = "matched-extracted.cleaned_company_names"
    3. If not found → call Parallel AI, source = "parallel"
       Also writes new mapping to extracted.cleaned_company_names

    Updates hq.clients_normalized_crm_data with cleaned_company_name and source.
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch normalized records that need company name resolution
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, domain, company_name
            FROM hq.clients_normalized_crm_data
            WHERE id = ANY($1::uuid[])
              AND domain IS NOT NULL
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, domain, company_name
            FROM hq.clients_normalized_crm_data
            WHERE client_domain = $1
              AND domain IS NOT NULL
        """, client_domain)

    if not rows:
        return {"success": True, "records_processed": 0, "message": "No records found with domain"}

    # Get unique domains to look up
    domains = list(set(row["domain"] for row in rows if row["domain"]))

    # Batch lookup existing cleaned company names
    existing_mappings = {}
    if domains:
        existing = await pool.fetch("""
            SELECT domain, cleaned_company_name, source
            FROM extracted.cleaned_company_names
            WHERE domain = ANY($1)
              AND cleaned_company_name IS NOT NULL
        """, domains)
        for row in existing:
            existing_mappings[row["domain"]] = {
                "cleaned_company_name": row["cleaned_company_name"],
                "source": row["source"]
            }

    # Process records
    records_evaluated = len(rows)
    fields_updated = 0
    records_already_had_value = 0
    records_matched = 0
    records_from_parallel = 0
    errors = []

    # Check which records already have cleaned_company_name
    record_ids_list = [row["id"] for row in rows]
    existing_cleaned = await pool.fetch("""
        SELECT id, cleaned_company_name
        FROM hq.clients_normalized_crm_data
        WHERE id = ANY($1::uuid[])
    """, record_ids_list)
    already_cleaned = {row["id"]: row["cleaned_company_name"] for row in existing_cleaned}

    for record in rows:
        try:
            record_id = record["id"]
            domain = record["domain"]
            original_company_name = record["company_name"]

            # Skip if already has a cleaned_company_name value
            if already_cleaned.get(record_id):
                records_already_had_value += 1
                continue

            cleaned_company_name = None
            source = None

            # Check if we have an existing mapping
            if domain in existing_mappings:
                cleaned_company_name = existing_mappings[domain]["cleaned_company_name"]
                source = "matched-extracted.cleaned_company_names"
                records_matched += 1
            else:
                # Call Parallel AI
                cleaned_company_name = await call_parallel_ai_for_company_name(domain)

                if cleaned_company_name:
                    source = "parallel"
                    records_from_parallel += 1

                    # Write to extracted.cleaned_company_names for future lookups
                    await pool.execute("""
                        INSERT INTO extracted.cleaned_company_names
                            (domain, original_company_name, cleaned_company_name, source)
                        VALUES ($1, $2, $3, 'parallel')
                        ON CONFLICT (domain) DO UPDATE SET
                            cleaned_company_name = EXCLUDED.cleaned_company_name,
                            source = 'parallel',
                            updated_at = NOW()
                    """, domain, original_company_name, cleaned_company_name)

                    # Add to cache for other records with same domain
                    existing_mappings[domain] = {
                        "cleaned_company_name": cleaned_company_name,
                        "source": "parallel"
                    }

            # Update the normalized record
            if cleaned_company_name:
                await pool.execute("""
                    UPDATE hq.clients_normalized_crm_data
                    SET cleaned_company_name = $1,
                        cleaned_company_name_source = $2,
                        updated_at = NOW()
                    WHERE id = $3
                """, cleaned_company_name, source, record_id)
                fields_updated += 1

        except Exception as e:
            errors.append({"record_id": str(record["id"]), "domain": record["domain"], "error": str(e)})

    return {
        "success": True,
        "records_evaluated": records_evaluated,
        "fields_updated": fields_updated,
        "records_already_had_value": records_already_had_value,
        "records_matched": records_matched,
        "records_from_parallel": records_from_parallel,
        "errors": errors if errors else None
    }


@router.post("/resolve-domain-from-linkedin")
async def resolve_domain_from_linkedin(payload: dict):
    """
    Resolve domain from company_linkedin_url by matching against core.companies.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_normalized_crm_data
    }

    Or to resolve all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Logic:
    1. Get records that have company_linkedin_url
    2. Match against core.companies.linkedin_url
    3. If match → populate domain from core.companies.domain

    Updates hq.clients_normalized_crm_data.domain
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch normalized records that have company_linkedin_url
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, company_linkedin_url, domain
            FROM hq.clients_normalized_crm_data
            WHERE id = ANY($1::uuid[])
              AND company_linkedin_url IS NOT NULL
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, company_linkedin_url, domain
            FROM hq.clients_normalized_crm_data
            WHERE client_domain = $1
              AND company_linkedin_url IS NOT NULL
        """, client_domain)

    if not rows:
        return {"success": True, "records_processed": 0, "message": "No records found with company_linkedin_url"}

    # Get unique LinkedIn URLs to look up
    linkedin_urls = list(set(row["company_linkedin_url"] for row in rows if row["company_linkedin_url"]))

    # Batch lookup domains from core.companies
    linkedin_to_domain = {}
    if linkedin_urls:
        existing = await pool.fetch("""
            SELECT linkedin_url, domain
            FROM core.companies
            WHERE linkedin_url = ANY($1)
              AND domain IS NOT NULL
        """, linkedin_urls)
        for row in existing:
            linkedin_to_domain[row["linkedin_url"]] = row["domain"]

    # Process records
    records_evaluated = len(rows)
    fields_updated = 0
    records_already_had_value = 0
    records_matched = 0
    records_no_match = 0
    errors = []

    for record in rows:
        try:
            record_id = record["id"]
            linkedin_url = record["company_linkedin_url"]
            current_domain = record["domain"]

            # Skip if already has a domain value
            if current_domain:
                records_already_had_value += 1
                continue

            # Check if we have a match
            if linkedin_url in linkedin_to_domain:
                matched_domain = linkedin_to_domain[linkedin_url]
                records_matched += 1

                # Update the domain
                await pool.execute("""
                    UPDATE hq.clients_normalized_crm_data
                    SET domain = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, matched_domain, record_id)
                fields_updated += 1
            else:
                records_no_match += 1

        except Exception as e:
            errors.append({"record_id": str(record["id"]), "linkedin_url": record["company_linkedin_url"], "error": str(e)})

    return {
        "success": True,
        "records_evaluated": records_evaluated,
        "fields_updated": fields_updated,
        "records_already_had_value": records_already_had_value,
        "records_matched": records_matched,
        "records_no_match": records_no_match,
        "errors": errors if errors else None
    }


def extract_domain_from_email(email: str) -> str | None:
    """Extract domain from email address (part after @)."""
    if not email or "@" not in email:
        return None
    return email.split("@")[1].lower().strip()


@router.post("/resolve-domain-from-email")
async def resolve_domain_from_email(payload: dict):
    """
    Resolve domain from work_email.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_normalized_crm_data
    }

    Or to resolve all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Logic:
    1. Try to match work_email against reference.email_to_person to get domain
    2. If no match, extract domain from email (part after @)
    3. Does NOT write back to lookup table

    Updates hq.clients_normalized_crm_data.domain
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch normalized records that have work_email but missing domain
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, work_email, domain
            FROM hq.clients_normalized_crm_data
            WHERE id = ANY($1::uuid[])
              AND work_email IS NOT NULL
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, work_email, domain
            FROM hq.clients_normalized_crm_data
            WHERE client_domain = $1
              AND work_email IS NOT NULL
        """, client_domain)

    if not rows:
        return {"success": True, "records_evaluated": 0, "fields_updated": 0, "message": "No records found with work_email"}

    # Get unique emails to look up
    emails = list(set(row["work_email"] for row in rows if row["work_email"]))

    # Batch lookup domains from reference.email_to_person
    email_to_domain = {}
    if emails:
        existing = await pool.fetch("""
            SELECT email, domain
            FROM reference.email_to_person
            WHERE email = ANY($1)
              AND domain IS NOT NULL
        """, emails)
        for row in existing:
            email_to_domain[row["email"]] = row["domain"]

    # Process records
    records_evaluated = len(rows)
    fields_updated = 0
    records_already_had_value = 0
    records_from_lookup = 0
    records_from_extraction = 0
    errors = []

    for record in rows:
        try:
            record_id = record["id"]
            work_email = record["work_email"]
            current_domain = record["domain"]

            # Skip if already has a domain value
            if current_domain:
                records_already_had_value += 1
                continue

            resolved_domain = None
            source = None

            # Try lookup first
            if work_email in email_to_domain:
                resolved_domain = email_to_domain[work_email]
                source = "lookup"
                records_from_lookup += 1
            else:
                # Fall back to extraction
                resolved_domain = extract_domain_from_email(work_email)
                if resolved_domain:
                    source = "extracted"
                    records_from_extraction += 1

            # Update the domain if we resolved one
            if resolved_domain:
                await pool.execute("""
                    UPDATE hq.clients_normalized_crm_data
                    SET domain = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, resolved_domain, record_id)
                fields_updated += 1

        except Exception as e:
            errors.append({"record_id": str(record["id"]), "work_email": record["work_email"], "error": str(e)})

    return {
        "success": True,
        "records_evaluated": records_evaluated,
        "fields_updated": fields_updated,
        "records_already_had_value": records_already_had_value,
        "records_from_lookup": records_from_lookup,
        "records_from_extraction": records_from_extraction,
        "errors": errors if errors else None
    }


@router.post("/resolve-linkedin-from-domain")
async def resolve_linkedin_from_domain(payload: dict):
    """
    Resolve company_linkedin_url from domain by matching against core.companies.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_normalized_crm_data
    }

    Or to resolve all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Logic:
    1. Get records that have domain
    2. Match against core.companies.domain
    3. If match → populate company_linkedin_url from core.companies.linkedin_url

    Updates hq.clients_normalized_crm_data.company_linkedin_url
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch normalized records that have domain
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, domain, company_linkedin_url
            FROM hq.clients_normalized_crm_data
            WHERE id = ANY($1::uuid[])
              AND domain IS NOT NULL
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, domain, company_linkedin_url
            FROM hq.clients_normalized_crm_data
            WHERE client_domain = $1
              AND domain IS NOT NULL
        """, client_domain)

    if not rows:
        return {"success": True, "records_evaluated": 0, "fields_updated": 0, "message": "No records found with domain"}

    # Get unique domains to look up
    domains = list(set(row["domain"] for row in rows if row["domain"]))

    # Batch lookup LinkedIn URLs from core.companies
    domain_to_linkedin = {}
    if domains:
        existing = await pool.fetch("""
            SELECT domain, linkedin_url
            FROM core.companies
            WHERE domain = ANY($1)
              AND linkedin_url IS NOT NULL
        """, domains)
        for row in existing:
            domain_to_linkedin[row["domain"]] = row["linkedin_url"]

    # Process records
    records_evaluated = len(rows)
    fields_updated = 0
    records_already_had_value = 0
    records_matched = 0
    records_no_match = 0
    errors = []

    for record in rows:
        try:
            record_id = record["id"]
            domain = record["domain"]
            current_linkedin = record["company_linkedin_url"]

            # Skip if already has a company_linkedin_url value
            if current_linkedin:
                records_already_had_value += 1
                continue

            # Check if we have a match
            if domain in domain_to_linkedin:
                linkedin_url = domain_to_linkedin[domain]
                records_matched += 1

                # Update the company_linkedin_url
                await pool.execute("""
                    UPDATE hq.clients_normalized_crm_data
                    SET company_linkedin_url = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, linkedin_url, record_id)
                fields_updated += 1
            else:
                records_no_match += 1

        except Exception as e:
            errors.append({"record_id": str(record["id"]), "domain": record["domain"], "error": str(e)})

    return {
        "success": True,
        "records_evaluated": records_evaluated,
        "fields_updated": fields_updated,
        "records_already_had_value": records_already_had_value,
        "records_matched": records_matched,
        "records_no_match": records_no_match,
        "errors": errors if errors else None
    }


@router.post("/resolve-person-linkedin-from-email")
async def resolve_person_linkedin_from_email(payload: dict):
    """
    Resolve person_linkedin_url from work_email by matching against reference.email_to_person.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_normalized_crm_data
    }

    Or to resolve all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Logic:
    1. Get records that have work_email
    2. Match against reference.email_to_person.email
    3. If match → populate person_linkedin_url from reference.email_to_person.person_linkedin_url

    Updates hq.clients_normalized_crm_data.person_linkedin_url
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch normalized records that have work_email
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, work_email, person_linkedin_url
            FROM hq.clients_normalized_crm_data
            WHERE id = ANY($1::uuid[])
              AND work_email IS NOT NULL
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, work_email, person_linkedin_url
            FROM hq.clients_normalized_crm_data
            WHERE client_domain = $1
              AND work_email IS NOT NULL
        """, client_domain)

    if not rows:
        return {"success": True, "records_evaluated": 0, "fields_updated": 0, "message": "No records found with work_email"}

    # Get unique emails to look up
    emails = list(set(row["work_email"] for row in rows if row["work_email"]))

    # Batch lookup LinkedIn URLs from reference.email_to_person
    email_to_linkedin = {}
    if emails:
        existing = await pool.fetch("""
            SELECT email, person_linkedin_url
            FROM reference.email_to_person
            WHERE email = ANY($1)
              AND person_linkedin_url IS NOT NULL
        """, emails)
        for row in existing:
            email_to_linkedin[row["email"]] = row["person_linkedin_url"]

    # Process records
    records_evaluated = len(rows)
    fields_updated = 0
    records_already_had_value = 0
    records_matched = 0
    records_no_match = 0
    errors = []

    for record in rows:
        try:
            record_id = record["id"]
            work_email = record["work_email"]
            current_linkedin = record["person_linkedin_url"]

            # Skip if already has a person_linkedin_url value
            if current_linkedin:
                records_already_had_value += 1
                continue

            # Check if we have a match
            if work_email in email_to_linkedin:
                linkedin_url = email_to_linkedin[work_email]
                records_matched += 1

                # Update the person_linkedin_url
                await pool.execute("""
                    UPDATE hq.clients_normalized_crm_data
                    SET person_linkedin_url = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, linkedin_url, record_id)
                fields_updated += 1
            else:
                records_no_match += 1

        except Exception as e:
            errors.append({"record_id": str(record["id"]), "work_email": record["work_email"], "error": str(e)})

    return {
        "success": True,
        "records_evaluated": records_evaluated,
        "fields_updated": fields_updated,
        "records_already_had_value": records_already_had_value,
        "records_matched": records_matched,
        "records_no_match": records_no_match,
        "errors": errors if errors else None
    }


@router.post("/resolve-company-location-from-domain")
async def resolve_company_location_from_domain(payload: dict):
    """
    Resolve company_city, company_state, company_country from domain
    by matching against core.company_locations.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_normalized_crm_data
    }

    Or to resolve all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Logic:
    1. Get records that have domain
    2. Match against core.company_locations.domain
    3. If match → populate company_city, company_state, company_country

    Updates hq.clients_normalized_crm_data location fields
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch normalized records that have domain
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, domain
            FROM hq.clients_normalized_crm_data
            WHERE id = ANY($1::uuid[])
              AND domain IS NOT NULL
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, domain
            FROM hq.clients_normalized_crm_data
            WHERE client_domain = $1
              AND domain IS NOT NULL
        """, client_domain)

    if not rows:
        return {"success": True, "records_evaluated": 0, "fields_updated": {"city": 0, "state": 0, "country": 0}, "message": "No records found with domain"}

    # Get unique domains to look up
    domains = list(set(row["domain"] for row in rows if row["domain"]))

    # Batch lookup locations from core.company_locations
    domain_to_location = {}
    if domains:
        existing = await pool.fetch("""
            SELECT domain, city, state, country
            FROM core.company_locations
            WHERE domain = ANY($1)
              AND (city IS NOT NULL OR state IS NOT NULL OR country IS NOT NULL)
        """, domains)
        for row in existing:
            domain_to_location[row["domain"]] = {
                "city": row["city"],
                "state": row["state"],
                "country": row["country"]
            }

    # Get current values to check what's already filled
    record_ids_list = [row["id"] for row in rows]
    current_values = await pool.fetch("""
        SELECT id, company_city, company_state, company_country
        FROM hq.clients_normalized_crm_data
        WHERE id = ANY($1::uuid[])
    """, record_ids_list)
    current_map = {row["id"]: row for row in current_values}

    # Process records
    records_evaluated = len(rows)
    fields_updated = {"city": 0, "state": 0, "country": 0}
    records_matched = 0
    records_no_match = 0
    records_all_fields_had_value = 0
    errors = []

    for record in rows:
        try:
            record_id = record["id"]
            domain = record["domain"]
            current = current_map.get(record_id, {})

            # Check if we have a match
            if domain in domain_to_location:
                location = domain_to_location[domain]
                records_matched += 1

                # Check which fields need updating
                city_to_update = location["city"] if not current.get("company_city") and location["city"] else None
                state_to_update = location["state"] if not current.get("company_state") and location["state"] else None
                country_to_update = location["country"] if not current.get("company_country") and location["country"] else None

                # Skip if all fields already have values
                if not city_to_update and not state_to_update and not country_to_update:
                    records_all_fields_had_value += 1
                    continue

                # Update the location fields (only fill in missing values)
                await pool.execute("""
                    UPDATE hq.clients_normalized_crm_data
                    SET company_city = COALESCE(company_city, $1),
                        company_state = COALESCE(company_state, $2),
                        company_country = COALESCE(company_country, $3),
                        updated_at = NOW()
                    WHERE id = $4
                """, location["city"], location["state"], location["country"], record_id)

                if city_to_update:
                    fields_updated["city"] += 1
                if state_to_update:
                    fields_updated["state"] += 1
                if country_to_update:
                    fields_updated["country"] += 1
            else:
                records_no_match += 1

        except Exception as e:
            errors.append({"record_id": str(record["id"]), "domain": record["domain"], "error": str(e)})

    return {
        "success": True,
        "records_evaluated": records_evaluated,
        "fields_updated": fields_updated,
        "records_all_fields_had_value": records_all_fields_had_value,
        "records_matched": records_matched,
        "records_no_match": records_no_match,
        "errors": errors if errors else None
    }


@router.post("/resolve-person-location-from-linkedin")
async def resolve_person_location_from_linkedin(payload: dict):
    """
    Resolve person_city, person_state, person_country from person_linkedin_url
    by matching against extracted.person_discovery_location_parsed.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_normalized_crm_data
    }

    Or to resolve all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Logic:
    1. Get records that have person_linkedin_url
    2. Match against extracted.person_discovery_location_parsed.linkedin_url
    3. If match → populate person_city, person_state, person_country

    Updates hq.clients_normalized_crm_data person location fields
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch normalized records that have person_linkedin_url
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, person_linkedin_url
            FROM hq.clients_normalized_crm_data
            WHERE id = ANY($1::uuid[])
              AND person_linkedin_url IS NOT NULL
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, person_linkedin_url
            FROM hq.clients_normalized_crm_data
            WHERE client_domain = $1
              AND person_linkedin_url IS NOT NULL
        """, client_domain)

    if not rows:
        return {"success": True, "records_evaluated": 0, "fields_updated": {"city": 0, "state": 0, "country": 0}, "message": "No records found with person_linkedin_url"}

    # Get unique LinkedIn URLs to look up
    linkedin_urls = list(set(row["person_linkedin_url"] for row in rows if row["person_linkedin_url"]))

    # Batch lookup locations from extracted.person_discovery_location_parsed
    linkedin_to_location = {}
    if linkedin_urls:
        existing = await pool.fetch("""
            SELECT linkedin_url, city, state, country
            FROM extracted.person_discovery_location_parsed
            WHERE linkedin_url = ANY($1)
              AND (city IS NOT NULL OR state IS NOT NULL OR country IS NOT NULL)
        """, linkedin_urls)
        for row in existing:
            linkedin_to_location[row["linkedin_url"]] = {
                "city": row["city"],
                "state": row["state"],
                "country": row["country"]
            }

    # Get current values to check what's already filled
    record_ids_list = [row["id"] for row in rows]
    current_values = await pool.fetch("""
        SELECT id, person_city, person_state, person_country
        FROM hq.clients_normalized_crm_data
        WHERE id = ANY($1::uuid[])
    """, record_ids_list)
    current_map = {row["id"]: row for row in current_values}

    # Process records
    records_evaluated = len(rows)
    fields_updated = {"city": 0, "state": 0, "country": 0}
    records_matched = 0
    records_no_match = 0
    records_all_fields_had_value = 0
    errors = []

    for record in rows:
        try:
            record_id = record["id"]
            linkedin_url = record["person_linkedin_url"]
            current = current_map.get(record_id, {})

            # Check if we have a match
            if linkedin_url in linkedin_to_location:
                location = linkedin_to_location[linkedin_url]
                records_matched += 1

                # Check which fields need updating
                city_to_update = location["city"] if not current.get("person_city") and location["city"] else None
                state_to_update = location["state"] if not current.get("person_state") and location["state"] else None
                country_to_update = location["country"] if not current.get("person_country") and location["country"] else None

                # Skip if all fields already have values
                if not city_to_update and not state_to_update and not country_to_update:
                    records_all_fields_had_value += 1
                    continue

                # Update the location fields (only fill in missing values)
                await pool.execute("""
                    UPDATE hq.clients_normalized_crm_data
                    SET person_city = COALESCE(person_city, $1),
                        person_state = COALESCE(person_state, $2),
                        person_country = COALESCE(person_country, $3),
                        updated_at = NOW()
                    WHERE id = $4
                """, location["city"], location["state"], location["country"], record_id)

                if city_to_update:
                    fields_updated["city"] += 1
                if state_to_update:
                    fields_updated["state"] += 1
                if country_to_update:
                    fields_updated["country"] += 1
            else:
                records_no_match += 1

        except Exception as e:
            errors.append({"record_id": str(record["id"]), "linkedin_url": record["person_linkedin_url"], "error": str(e)})

    return {
        "success": True,
        "records_evaluated": records_evaluated,
        "fields_updated": fields_updated,
        "records_all_fields_had_value": records_all_fields_had_value,
        "records_matched": records_matched,
        "records_no_match": records_no_match,
        "errors": errors if errors else None
    }
