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


@router.post("/clients/workflow-sequences")
async def get_workflow_sequences(payload: dict):
    """
    Get workflow sequences for a client.

    Payload: {
        "client_domain": "securitypalhq.com"
    }

    Returns workflows in sequence order.
    """
    client_domain = payload.get("client_domain", "").strip()

    if not client_domain:
        return {"success": False, "error": "client_domain is required"}

    pool = get_pool()

    rows = await pool.fetch("""
        SELECT id, client_domain, workflow_slug, endpoint_url, description,
               sequence_order, created_at, updated_at
        FROM hq.client_workflow_sequences
        WHERE client_domain = $1
        ORDER BY sequence_order ASC
    """, client_domain)

    return {
        "success": True,
        "data": [dict(r) for r in rows],
        "meta": {"total": len(rows), "client_domain": client_domain}
    }


@router.post("/clients/workflow-sequences/add")
async def add_workflow_sequence(payload: dict):
    """
    Add a workflow step to a client's sequence.

    Payload: {
        "client_domain": "securitypalhq.com",
        "workflow_slug": "resolve-company-name",
        "endpoint_url": "https://api.revenueinfra.com/api/workflows/resolve-company-name",
        "description": "Resolve cleaned company names",
        "sequence_order": 1
    }
    """
    client_domain = payload.get("client_domain", "").strip()
    workflow_slug = payload.get("workflow_slug", "").strip()
    endpoint_url = payload.get("endpoint_url", "").strip()
    description = payload.get("description", "").strip() or None
    sequence_order = payload.get("sequence_order", 0)

    if not client_domain:
        return {"success": False, "error": "client_domain is required"}
    if not workflow_slug:
        return {"success": False, "error": "workflow_slug is required"}
    if not endpoint_url:
        return {"success": False, "error": "endpoint_url is required"}

    pool = get_pool()

    try:
        row = await pool.fetchrow("""
            INSERT INTO hq.client_workflow_sequences
                (client_domain, workflow_slug, endpoint_url, description, sequence_order)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (client_domain, workflow_slug) DO UPDATE SET
                endpoint_url = EXCLUDED.endpoint_url,
                description = EXCLUDED.description,
                sequence_order = EXCLUDED.sequence_order,
                updated_at = NOW()
            RETURNING id, client_domain, workflow_slug, endpoint_url, description, sequence_order
        """, client_domain, workflow_slug, endpoint_url, description, sequence_order)

        return {
            "success": True,
            "data": dict(row)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/clients/workflow-sequences/update")
async def update_workflow_sequence(payload: dict):
    """
    Update a workflow step.

    Payload: {
        "id": "uuid",
        "workflow_slug": "new-slug",  // optional
        "endpoint_url": "new-url",    // optional
        "description": "new desc",    // optional
        "sequence_order": 2           // optional
    }
    """
    sequence_id = payload.get("id", "").strip()

    if not sequence_id:
        return {"success": False, "error": "id is required"}

    pool = get_pool()

    # Build dynamic update
    updates = []
    values = [sequence_id]
    param_idx = 2

    if "workflow_slug" in payload:
        updates.append(f"workflow_slug = ${param_idx}")
        values.append(payload["workflow_slug"])
        param_idx += 1
    if "endpoint_url" in payload:
        updates.append(f"endpoint_url = ${param_idx}")
        values.append(payload["endpoint_url"])
        param_idx += 1
    if "description" in payload:
        updates.append(f"description = ${param_idx}")
        values.append(payload["description"])
        param_idx += 1
    if "sequence_order" in payload:
        updates.append(f"sequence_order = ${param_idx}")
        values.append(payload["sequence_order"])
        param_idx += 1

    if not updates:
        return {"success": False, "error": "No fields to update"}

    updates.append("updated_at = NOW()")

    query = f"""
        UPDATE hq.client_workflow_sequences
        SET {', '.join(updates)}
        WHERE id = $1
        RETURNING id, client_domain, workflow_slug, endpoint_url, description, sequence_order
    """

    try:
        row = await pool.fetchrow(query, *values)
        if row:
            return {"success": True, "data": dict(row)}
        else:
            return {"success": False, "error": "Workflow sequence not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/clients/workflow-sequences/delete")
async def delete_workflow_sequence(payload: dict):
    """
    Delete a workflow step.

    Payload: {
        "id": "uuid"
    }
    """
    sequence_id = payload.get("id", "").strip()

    if not sequence_id:
        return {"success": False, "error": "id is required"}

    pool = get_pool()

    result = await pool.execute("""
        DELETE FROM hq.client_workflow_sequences
        WHERE id = $1
    """, sequence_id)

    if result == "DELETE 1":
        return {"success": True, "deleted": True}
    else:
        return {"success": False, "error": "Workflow sequence not found"}


@router.post("/clients/salesnav-template")
async def get_salesnav_template(payload: dict):
    """
    Get Sales Navigator template config for a client.

    Payload: {
        "client_domain": "securitypalhq.com"
    }

    Returns the template URL and customer company details.
    """
    client_domain = payload.get("client_domain", "").strip()

    if not client_domain:
        return {"success": False, "error": "client_domain is required"}

    pool = get_pool()

    row = await pool.fetchrow("""
        SELECT
            id,
            client_domain,
            template_url,
            current_customer_linkedin_org_id,
            customer_company_name,
            customer_company_domain,
            created_at
        FROM hq.client_salesnav_templates
        WHERE client_domain = $1
        ORDER BY created_at DESC
        LIMIT 1
    """, client_domain)

    if not row:
        return {"success": False, "error": f"No salesnav template found for '{client_domain}'"}

    return {
        "success": True,
        "data": dict(row)
    }
