"""
Enrichment API endpoints.

Wraps Modal functions for data enrichment operations.
"""

import os
import json
import httpx
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any
from db import core, extracted, raw, get_pool

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


# ============================================================================
# Workflow Registry
# ============================================================================

@router.get("/workflows")
async def get_workflows(
    entity_type: Optional[str] = Query(None, description="Filter by entity type: company, person, target_client"),
    coalesces_to_core: Optional[bool] = Query(None, description="Filter by whether data flows to core schema"),
    payload_type: Optional[str] = Query(None, description="Filter by payload type: enrichment, inference, signal, etc."),
    usage_category: Optional[str] = Query(None, description="Filter by usage category: client, internal-hq"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type: ingest, calls_ai, lookup, utility, backfill"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    has_api_wrapper: Optional[bool] = Query(None, description="Filter by whether workflow has an API wrapper endpoint"),
):
    """
    Get all enrichment workflows from the registry.

    Use coalesces_to_core=true to see workflows that write to core tables.
    Use coalesces_to_core=false to see workflows that only write to raw/extracted.
    Use usage_category=client to see client-facing workflows (signals).
    Use usage_category=internal-hq to see internal HQ workflows.
    Use has_api_wrapper=true to see only workflows with /run/* API endpoints.
    """
    from db import reference

    query = (
        reference()
        .from_("enrichment_workflow_registry")
        .select("workflow_slug, new_workflow_slug, provider, platform, payload_type, entity_type, description, raw_table, extracted_table, core_table, coalesces_to_core, usage_category, workflow_type, is_active, modal_function_name, modal_endpoint_url, api_endpoint_url")
        .order("new_workflow_slug", nullsfirst=False)
        .order("workflow_slug")
    )

    if entity_type:
        query = query.eq("entity_type", entity_type)
    if coalesces_to_core is not None:
        query = query.eq("coalesces_to_core", coalesces_to_core)
    if payload_type:
        query = query.eq("payload_type", payload_type)
    if usage_category:
        query = query.eq("usage_category", usage_category)
    if workflow_type:
        query = query.eq("workflow_type", workflow_type)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if has_api_wrapper is True:
        query = query.not_.is_("api_endpoint_url", "null")
    elif has_api_wrapper is False:
        query = query.is_("api_endpoint_url", "null")

    result = query.execute()

    # Group by coalesces_to_core for summary
    in_core = [w for w in result.data if w.get("coalesces_to_core")]
    not_in_core = [w for w in result.data if not w.get("coalesces_to_core")]
    client_workflows = [w for w in result.data if w.get("usage_category") == "client"]
    internal_workflows = [w for w in result.data if w.get("usage_category") == "internal-hq"]
    with_api_wrapper = [w for w in result.data if w.get("api_endpoint_url")]

    return {
        "data": result.data,
        "meta": {
            "total": len(result.data),
            "in_core_count": len(in_core),
            "not_in_core_count": len(not_in_core),
            "client_count": len(client_workflows),
            "internal_hq_count": len(internal_workflows),
            "with_api_wrapper_count": len(with_api_wrapper),
            "filters": {
                "entity_type": entity_type,
                "coalesces_to_core": coalesces_to_core,
                "payload_type": payload_type,
                "usage_category": usage_category,
                "workflow_type": workflow_type,
                "is_active": is_active,
                "has_api_wrapper": has_api_wrapper,
            }
        }
    }


@router.get("/workflows/summary")
async def get_workflows_summary():
    """
    Get a summary of workflow counts by entity type, core status, and usage category.
    """
    from db import reference

    result = (
        reference()
        .from_("enrichment_workflow_registry")
        .select("entity_type, payload_type, coalesces_to_core, usage_category, workflow_type")
        .eq("is_active", True)
        .execute()
    )

    # Build summary
    by_entity = {}
    by_payload = {}
    by_usage = {"client": 0, "internal-hq": 0}
    by_workflow_type = {}

    for w in result.data:
        entity = w.get("entity_type", "unknown")
        payload = w.get("payload_type", "unknown")
        in_core = w.get("coalesces_to_core", False)
        usage = w.get("usage_category", "internal-hq")
        wf_type = w.get("workflow_type", "unknown")

        # By entity
        if entity not in by_entity:
            by_entity[entity] = {"total": 0, "in_core": 0, "not_in_core": 0}
        by_entity[entity]["total"] += 1
        if in_core:
            by_entity[entity]["in_core"] += 1
        else:
            by_entity[entity]["not_in_core"] += 1

        # By payload type
        if payload not in by_payload:
            by_payload[payload] = {"total": 0, "in_core": 0, "not_in_core": 0}
        by_payload[payload]["total"] += 1
        if in_core:
            by_payload[payload]["in_core"] += 1
        else:
            by_payload[payload]["not_in_core"] += 1

        # By usage category
        by_usage[usage] = by_usage.get(usage, 0) + 1

        # By workflow type
        by_workflow_type[wf_type] = by_workflow_type.get(wf_type, 0) + 1

    total_in_core = sum(e["in_core"] for e in by_entity.values())
    total_not_in_core = sum(e["not_in_core"] for e in by_entity.values())

    return {
        "total_workflows": len(result.data),
        "total_in_core": total_in_core,
        "total_not_in_core": total_not_in_core,
        "by_entity_type": by_entity,
        "by_payload_type": by_payload,
        "by_workflow_type": by_workflow_type,
        "by_usage_category": by_usage,
    }

MODAL_PROCESS_QUEUE_URL = os.getenv(
    "MODAL_PROCESS_QUEUE_URL",
    "https://bencrane--hq-master-data-ingest-process-similar-companies-queue.modal.run"
)


class BatchSubmitRequest(BaseModel):
    batch_size: int = 200
    similarity_weight: float = 0.0  # -1 to 1. Positive = more similar, Negative = more established
    country_code: Optional[str] = None  # 2-letter code e.g., "US", "GB"


@router.get("/similar-companies/pending")
async def get_pending_similar_companies(
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    """
    Get domains that have customer data but no similar companies data.
    These are candidates for enrichment.
    """
    # Get customer domains
    customers_result = (
        core()
        .from_("company_customers")
        .select("customer_domain")
        .not_.is_("customer_domain", "null")
        .execute()
    )

    if not customers_result.data:
        return {
            "success": True,
            "pending_domains": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    # Get unique customer domains
    customer_domains = list(set(
        row["customer_domain"] for row in customers_result.data
        if row.get("customer_domain") and row["customer_domain"].strip()
    ))

    # Get domains that already have similar companies data
    existing_result = (
        extracted()
        .from_("company_enrich_similar")
        .select("input_domain")
        .execute()
    )

    existing_domains = set(
        row["input_domain"] for row in existing_result.data
        if row.get("input_domain")
    )

    # Find domains without similar companies
    pending_domains = [d for d in customer_domains if d not in existing_domains]
    pending_domains.sort()

    # Apply pagination
    total = len(pending_domains)
    paginated = pending_domains[offset:offset + limit]

    return {
        "success": True,
        "pending_domains": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@router.post("/similar-companies/batch")
async def submit_similar_companies_batch(request: BatchSubmitRequest):
    """
    Process pending domains for similar companies enrichment.

    Queries pending domains directly, inserts into queue, triggers processing.
    Frontend just specifies batch_size - no need to send domains.
    """
    try:
        # Get customer domains directly from DB
        customers_result = (
            core()
            .from_("company_customers")
            .select("customer_domain")
            .not_.is_("customer_domain", "null")
            .execute()
        )

        if not customers_result.data:
            return {"success": False, "error": "No customer domains found"}

        customer_domains = list(set(
            row["customer_domain"] for row in customers_result.data
            if row.get("customer_domain") and row["customer_domain"].strip()
        ))

        # Get domains already enriched
        existing_result = (
            extracted()
            .from_("company_enrich_similar")
            .select("input_domain")
            .execute()
        )
        existing_domains = set(
            row["input_domain"] for row in existing_result.data
            if row.get("input_domain")
        )

        # Get domains already in queue
        queued_result = (
            raw()
            .from_("company_enrich_similar_queue")
            .select("domain")
            .execute()
        )
        queued_domains = set(
            row["domain"] for row in queued_result.data
            if row.get("domain")
        )

        # Find domains that need processing (not enriched, not already queued)
        pending_domains = [
            d for d in customer_domains
            if d not in existing_domains and d not in queued_domains
        ]

        if not pending_domains:
            return {
                "success": True,
                "message": "No new domains to process - all are either enriched or already queued",
                "queued_domains": 0,
            }

        # Limit to batch_size
        domains_to_queue = pending_domains[:request.batch_size]

        # Insert into queue
        queue_records = [{"domain": d, "status": "pending"} for d in domains_to_queue]
        raw().from_("company_enrich_similar_queue").insert(queue_records).execute()

        # Trigger Modal to process
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                MODAL_PROCESS_QUEUE_URL,
                json={
                    "batch_size": len(domains_to_queue),
                    "similarity_weight": request.similarity_weight,
                    "country_code": request.country_code,
                },
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to trigger processing: {response.status_code}",
                    "queued_domains": len(domains_to_queue),
                }

            modal_result = response.json()

        return {
            "success": True,
            "queued_domains": len(domains_to_queue),
            "remaining_pending": len(pending_domains) - len(domains_to_queue),
            "batch_id": modal_result.get("batch_id"),
            "domains_processing": modal_result.get("domains_to_process", 0),
            "estimated_time_seconds": modal_result.get("estimated_time_seconds"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/similar-companies/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """
    Get status of a similar companies batch.
    """
    try:
        batch_result = (
            raw()
            .from_("company_enrich_similar_batches")
            .select("*")
            .eq("id", batch_id)
            .limit(1)
            .execute()
        )

        if not batch_result.data:
            raise HTTPException(status_code=404, detail="Batch not found")

        batch = batch_result.data[0]

        response = {
            "success": True,
            "batch_id": batch["id"],
            "status": batch["status"],
            "total_domains": batch["total_domains"],
            "processed_domains": batch["processed_domains"],
            "progress_percent": round(
                (batch["processed_domains"] / batch["total_domains"]) * 100
                if batch["total_domains"] > 0 else 0,
                1
            ),
            "created_at": batch["created_at"],
            "completed_at": batch["completed_at"],
            "error_message": batch.get("error_message"),
        }

        # If completed, get result counts
        if batch["status"] in ("completed", "completed_with_errors"):
            results = (
                extracted()
                .from_("company_enrich_similar")
                .select("input_domain", count="exact", head=True)
                .eq("batch_id", batch_id)
                .execute()
            )
            response["similar_companies_found"] = results.count or 0

        return response

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.delete("/similar-companies/queue/clear")
async def clear_queue(include_processing: bool = False):
    """
    Clear items from the queue.
    By default leaves 'processing' items alone.
    Set include_processing=true to clear stuck processing items too.
    """
    try:
        # Delete done items
        raw().from_("company_enrich_similar_queue").delete().eq("status", "done").execute()
        # Delete error items
        raw().from_("company_enrich_similar_queue").delete().eq("status", "error").execute()
        # Delete pending items
        raw().from_("company_enrich_similar_queue").delete().eq("status", "pending").execute()

        if include_processing:
            raw().from_("company_enrich_similar_queue").delete().eq("status", "processing").execute()
            return {"success": True, "message": "Queue fully cleared (including stuck processing items)"}

        return {"success": True, "message": "Queue cleared (done/error/pending removed)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/similar-companies/queue/status")
async def get_queue_status():
    """
    Get overall queue status - pending, processing, done, error counts.
    """
    try:
        all_items = (
            raw()
            .from_("company_enrich_similar_queue")
            .select("status")
            .execute()
        )

        counts = {"pending": 0, "processing": 0, "done": 0, "error": 0}
        for item in all_items.data:
            status = item.get("status", "pending")
            counts[status] = counts.get(status, 0) + 1

        return {
            "success": True,
            "total": len(all_items.data),
            **counts,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# BuiltWith Tech Stack Ingestion
# ============================================================================

class BuiltWithIngestRequest(BaseModel):
    domain: str
    builtwith_payload: Any  # Raw BuiltWith data - either array or {"matchesFound": [...]}
    clay_table_url: Optional[str] = None


@router.post("/builtwith")
async def ingest_builtwith(request: BuiltWithIngestRequest):
    """
    Ingest BuiltWith tech stack data for a domain.

    Flow:
    1. Store raw payload → raw.builtwith_payloads
    2. Extract each tech → extracted.company_builtwith
    3. Auto-populate → reference.technologies (ON CONFLICT DO NOTHING)
    4. Map to core → core.company_technologies
    """
    pool = get_pool()

    # Handle both formats: direct array or {"matchesFound": [...]}
    payload = request.builtwith_payload
    if isinstance(payload, dict) and "matchesFound" in payload:
        technologies = payload["matchesFound"]
    elif isinstance(payload, list):
        technologies = payload
    else:
        raise HTTPException(status_code=400, detail="builtwith_payload must be an array or {matchesFound: [...]}")

    try:
        async with pool.acquire() as conn:
            # 1. Insert raw payload
            raw_payload_id = await conn.fetchval("""
                INSERT INTO raw.builtwith_payloads (domain, payload, clay_table_url)
                VALUES ($1, $2::jsonb, $3)
                RETURNING id
            """, request.domain, json.dumps(payload), request.clay_table_url)

            technologies_count = 0

            for tech in technologies:
                if not isinstance(tech, dict):
                    continue

                tech_name = tech.get("Name") or tech.get("name")
                if not tech_name:
                    continue

                # Extract fields
                tech_url = tech.get("Link") or tech.get("link")
                tech_description = tech.get("Description") or tech.get("description")
                tech_parent = tech.get("Parent") or tech.get("parent")
                categories = tech.get("Tag") or tech.get("tag") or tech.get("Categories") or tech.get("categories")
                first_detected = tech.get("FirstDetected") or tech.get("first_detected")
                last_detected = tech.get("LastDetected") or tech.get("last_detected")

                # Convert categories to JSON string if it's a list
                categories_json = json.dumps(categories) if categories else None

                # 2. Insert into extracted
                await conn.execute("""
                    INSERT INTO extracted.company_builtwith
                    (raw_payload_id, domain, technology_name, technology_url,
                     technology_description, technology_parent, categories,
                     first_detected, last_detected)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)
                """, raw_payload_id, request.domain, tech_name, tech_url,
                     tech_description, tech_parent, categories_json,
                     first_detected, last_detected)

                # 3. Upsert into reference.technologies
                await conn.execute("""
                    INSERT INTO reference.technologies (name, url, description, parent, categories)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    ON CONFLICT (name) DO NOTHING
                """, tech_name, tech_url, tech_description, tech_parent, categories_json)

                # 4. Map to core.company_technologies
                await conn.execute("""
                    INSERT INTO core.company_technologies (domain, technology_id, first_detected, last_detected)
                    SELECT $1, t.id, $3, $4
                    FROM reference.technologies t
                    WHERE t.name = $2
                    ON CONFLICT (domain, technology_id) DO UPDATE
                    SET last_detected = EXCLUDED.last_detected,
                        updated_at = NOW()
                """, request.domain, tech_name, first_detected, last_detected)

                technologies_count += 1

            return {
                "success": True,
                "domain": request.domain,
                "raw_payload_id": str(raw_payload_id),
                "technologies_count": technologies_count,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")
