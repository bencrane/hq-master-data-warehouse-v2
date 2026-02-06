import csv
import io
import json
from fastapi import APIRouter
from db import get_pool
from routers.workflows import normalize_record

router = APIRouter(prefix="/api/hq", tags=["hq"])

# Known columns to extract from CSV
KNOWN_COLUMNS = {
    "first_name", "last_name", "full_name", "person_linkedin_url",
    "person_city", "person_state", "person_country", "work_email",
    "phone_number", "company_name", "domain", "company_linkedin_url",
    "company_city", "company_state", "company_country"
}


@router.post("/clients")
async def get_clients(payload: dict = {}):
    """
    Get all HQ clients for dropdown selection.

    Returns all clients with their details.
    """
    pool = get_pool()

    rows = await pool.fetch("""
        SELECT id, name, domain, status, service, created_at, updated_at
        FROM hq.clients
        ORDER BY name
    """)

    return {
        "data": [dict(r) for r in rows],
        "meta": {"total": len(rows)}
    }


@router.post("/clients/upload-csv")
async def upload_client_csv(payload: dict):
    """
    Upload CSV data for a client.

    Payload: {
        "client_domain": "securitypalhq.com",
        "csv_data": "first_name,last_name,work_email,...\\nJohn,Doe,john@example.com,..."
    }

    1. Parses CSV and inserts into hq.clients_raw_data (raw, as-is)
    2. Normalizes and inserts into hq.clients_normalized_crm_data

    Known columns are extracted to their own fields.
    All data (including title, status, notes, extras) goes into raw_payload JSONB.
    """
    client_domain = payload.get("client_domain", "").strip()
    csv_data = payload.get("csv_data", "").strip()

    if not client_domain:
        return {"success": False, "error": "client_domain is required"}
    if not csv_data:
        return {"success": False, "error": "csv_data is required"}

    pool = get_pool()

    # Verify client exists
    client = await pool.fetchrow(
        "SELECT domain FROM hq.clients WHERE domain = $1", client_domain
    )
    if not client:
        return {"success": False, "error": f"Client '{client_domain}' not found in hq.clients"}

    # Parse CSV
    reader = csv.DictReader(io.StringIO(csv_data))
    rows_inserted = 0
    rows_normalized = 0
    errors = []

    for i, row in enumerate(reader):
        try:
            # Extract known columns (normalize keys to lowercase/underscore)
            csv_row = {}
            for key, value in row.items():
                # Normalize key: lowercase, replace spaces with underscores
                norm_key = key.lower().strip().replace(" ", "_").replace("-", "_")
                csv_row[norm_key] = value.strip() if value else None

            # Build insert values for raw table
            raw_values = {
                "client_domain": client_domain,
                "first_name": csv_row.get("first_name"),
                "last_name": csv_row.get("last_name"),
                "full_name": csv_row.get("full_name"),
                "person_linkedin_url": csv_row.get("person_linkedin_url"),
                "person_city": csv_row.get("person_city"),
                "person_state": csv_row.get("person_state"),
                "person_country": csv_row.get("person_country"),
                "work_email": csv_row.get("work_email"),
                "phone_number": csv_row.get("phone_number"),
                "company_name": csv_row.get("company_name"),
                "domain": csv_row.get("domain"),
                "company_linkedin_url": csv_row.get("company_linkedin_url"),
                "company_city": csv_row.get("company_city"),
                "company_state": csv_row.get("company_state"),
                "company_country": csv_row.get("company_country"),
                "raw_payload": json.dumps(csv_row),
            }

            # 1. Insert into raw table and get the ID back
            raw_id = await pool.fetchval("""
                INSERT INTO hq.clients_raw_data (
                    client_domain, first_name, last_name, full_name,
                    person_linkedin_url, person_city, person_state, person_country,
                    work_email, phone_number, company_name, domain,
                    company_linkedin_url, company_city, company_state, company_country,
                    raw_payload
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
                )
                RETURNING id
            """,
                raw_values["client_domain"],
                raw_values["first_name"],
                raw_values["last_name"],
                raw_values["full_name"],
                raw_values["person_linkedin_url"],
                raw_values["person_city"],
                raw_values["person_state"],
                raw_values["person_country"],
                raw_values["work_email"],
                raw_values["phone_number"],
                raw_values["company_name"],
                raw_values["domain"],
                raw_values["company_linkedin_url"],
                raw_values["company_city"],
                raw_values["company_state"],
                raw_values["company_country"],
                raw_values["raw_payload"],
            )
            rows_inserted += 1

            # 2. Normalize the record
            raw_record = {
                "id": raw_id,
                "client_domain": client_domain,
                "first_name": raw_values["first_name"],
                "last_name": raw_values["last_name"],
                "full_name": raw_values["full_name"],
                "person_linkedin_url": raw_values["person_linkedin_url"],
                "person_city": raw_values["person_city"],
                "person_state": raw_values["person_state"],
                "person_country": raw_values["person_country"],
                "work_email": raw_values["work_email"],
                "phone_number": raw_values["phone_number"],
                "company_name": raw_values["company_name"],
                "domain": raw_values["domain"],
                "company_linkedin_url": raw_values["company_linkedin_url"],
                "company_city": raw_values["company_city"],
                "company_state": raw_values["company_state"],
                "company_country": raw_values["company_country"],
                "raw_payload": csv_row,  # Pass the dict, not JSON string
            }
            normalized = normalize_record(raw_record)

            # 3. Insert into normalized table
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
            rows_normalized += 1

        except Exception as e:
            errors.append({"row": i + 1, "error": str(e)})

    return {
        "success": True,
        "client_domain": client_domain,
        "rows_inserted": rows_inserted,
        "rows_normalized": rows_normalized,
        "errors": errors if errors else None
    }


@router.post("/clients/raw-leads")
async def get_raw_leads(payload: dict):
    """
    Get raw leads data from hq.clients_raw_data.

    Payload: {
        "client_domain": "securitypalhq.com",
        "limit": 100,
        "offset": 0
    }
    """
    client_domain = payload.get("client_domain", "").strip()
    limit = payload.get("limit", 100)
    offset = payload.get("offset", 0)

    if not client_domain:
        return {"success": False, "error": "client_domain is required"}

    pool = get_pool()

    # Get total count
    count_row = await pool.fetchrow("""
        SELECT COUNT(*) as total
        FROM hq.clients_raw_data
        WHERE client_domain = $1
    """, client_domain)
    total = count_row["total"] if count_row else 0

    # Get data
    rows = await pool.fetch("""
        SELECT id, client_domain, first_name, last_name, full_name,
               person_linkedin_url, person_city, person_state, person_country,
               work_email, phone_number, company_name, domain,
               company_linkedin_url, company_city, company_state, company_country,
               raw_payload, created_at
        FROM hq.clients_raw_data
        WHERE client_domain = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
    """, client_domain, limit, offset)

    return {
        "success": True,
        "data": [dict(r) for r in rows],
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "client_domain": client_domain
        }
    }


@router.post("/clients/normalized-leads")
async def get_normalized_leads(payload: dict):
    """
    Get normalized leads data from hq.clients_normalized_crm_data.

    Payload: {
        "client_domain": "securitypalhq.com",
        "limit": 100,
        "offset": 0
    }
    """
    client_domain = payload.get("client_domain", "").strip()
    limit = payload.get("limit", 100)
    offset = payload.get("offset", 0)

    if not client_domain:
        return {"success": False, "error": "client_domain is required"}

    pool = get_pool()

    # Get total count
    count_row = await pool.fetchrow("""
        SELECT COUNT(*) as total
        FROM hq.clients_normalized_crm_data
        WHERE client_domain = $1
    """, client_domain)
    total = count_row["total"] if count_row else 0

    # Get data
    rows = await pool.fetch("""
        SELECT id, raw_data_id, client_domain, first_name, last_name, full_name,
               person_linkedin_url, person_city, person_state, person_country,
               work_email, phone_number, company_name, domain,
               company_linkedin_url, company_city, company_state, company_country,
               title, status, notes,
               cleaned_company_name, cleaned_company_name_source,
               normalized_at, created_at, updated_at
        FROM hq.clients_normalized_crm_data
        WHERE client_domain = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
    """, client_domain, limit, offset)

    return {
        "success": True,
        "data": [dict(r) for r in rows],
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "client_domain": client_domain
        }
    }
