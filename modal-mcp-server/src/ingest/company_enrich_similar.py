"""
Company Enrich Similar Companies Endpoint

Calls companyenrich.com API to find similar companies (preview - free endpoint).
Stores results in raw and extracted tables.

Architecture:
- POST /find_similar_companies_batch - Creates batch, spawns async processing, returns immediately
- GET /get_similar_companies_batch_status - Check batch progress
- POST /find_similar_companies_single - Process single domain (sync)
"""

import os
import time
import modal
import requests
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from config import app, image


class SimilarCompaniesRequest(BaseModel):
    domains: List[str]
    similarity_weight: Optional[float] = 0.0
    country_code: Optional[str] = None
    batch_name: Optional[str] = None


class SingleDomainRequest(BaseModel):
    domain: str
    similarity_weight: Optional[float] = 0.0
    country_code: Optional[str] = None
    batch_id: Optional[str] = None


class BatchStatusRequest(BaseModel):
    batch_id: str


# Background worker function - processes domains asynchronously
@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("companyenrich-api-key"),
    ],
    timeout=14400,  # 4 hours max
)
def process_similar_companies_batch(
    batch_id: str,
    domains: List[str],
    similarity_weight: float,
    country_code: Optional[str],
):
    """
    Background worker that processes all domains for a batch.
    Called via .spawn() from the batch endpoint.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    companyenrich_key = os.environ["COMPANYENRICH_API_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    processed = 0
    errors = []

    for domain in domains:
        try:
            _process_single_domain_with_retry(
                supabase=supabase,
                companyenrich_key=companyenrich_key,
                domain=domain,
                similarity_weight=similarity_weight,
                country_code=country_code,
                batch_id=batch_id,
            )
            processed += 1
        except Exception as e:
            # Log error, continue to next domain (don't crash batch)
            print(f"Error processing {domain}: {e}")
            errors.append({"domain": domain, "error": str(e)})

        # Update progress every domain (processed + errors = total attempted)
        supabase.schema("raw").from_("company_enrich_similar_batches").update({
            "processed_domains": processed + len(errors)
        }).eq("id", batch_id).execute()

        # Rate limit: 2 requests per second to avoid hammering the API
        time.sleep(0.5)

    # Mark batch complete (or completed_with_errors if there were failures)
    final_status = "completed" if not errors else "completed_with_errors"
    error_summary = None
    if errors:
        error_summary = f"{len(errors)} domains failed: {errors[:10]}"  # First 10 errors
        if len(errors) > 10:
            error_summary += f"... and {len(errors) - 10} more"

    supabase.schema("raw").from_("company_enrich_similar_batches").update({
        "status": final_status,
        "completed_at": datetime.utcnow().isoformat(),
        "error_message": error_summary,
    }).eq("id", batch_id).execute()


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def find_similar_companies_batch(request: SimilarCompaniesRequest) -> dict:
    """
    Create a batch and spawn async processing.
    Returns immediately with batch_id - frontend should poll for status.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Create batch record with 'pending' status
        batch_insert = (
            supabase.schema("raw")
            .from_("company_enrich_similar_batches")
            .insert({
                "batch_name": request.batch_name,
                "input_domains": request.domains,
                "similarity_weight": request.similarity_weight,
                "country_code": request.country_code,
                "status": "pending",
                "total_domains": len(request.domains),
                "processed_domains": 0,
            })
            .execute()
        )
        batch_id = batch_insert.data[0]["id"]

        # Update to processing
        supabase.schema("raw").from_("company_enrich_similar_batches").update({
            "status": "processing"
        }).eq("id", batch_id).execute()

        # Spawn background processing
        process_similar_companies_batch.spawn(
            batch_id=batch_id,
            domains=request.domains,
            similarity_weight=request.similarity_weight,
            country_code=request.country_code,
        )

        # Return immediately
        return {
            "success": True,
            "batch_id": batch_id,
            "total_domains": len(request.domains),
            "status": "processing",
            "message": "Batch submitted. Poll /get_similar_companies_batch_status for progress.",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def get_similar_companies_batch_status(request: BatchStatusRequest) -> dict:
    """
    Check the status of a batch.
    Returns progress and results when completed.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Get batch record
        batch = (
            supabase.schema("raw")
            .from_("company_enrich_similar_batches")
            .select("*")
            .eq("id", request.batch_id)
            .single()
            .execute()
        )

        if not batch.data:
            return {"success": False, "error": "Batch not found"}

        b = batch.data
        response = {
            "success": True,
            "batch_id": b["id"],
            "batch_name": b["batch_name"],
            "status": b["status"],
            "total_domains": b["total_domains"],
            "processed_domains": b["processed_domains"],
            "created_at": b["created_at"],
            "completed_at": b["completed_at"],
        }

        # If completed, include summary of results
        if b["status"] == "completed":
            # Get count of extracted companies per input domain
            results = (
                supabase.schema("extracted")
                .from_("company_enrich_similar")
                .select("input_domain")
                .eq("batch_id", request.batch_id)
                .execute()
            )

            # Count per domain
            domain_counts = {}
            for r in results.data:
                d = r["input_domain"]
                domain_counts[d] = domain_counts.get(d, 0) + 1

            response["results_summary"] = {
                "total_similar_companies": len(results.data),
                "domains_with_results": len(domain_counts),
                "per_domain_counts": domain_counts,
            }

        return response

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("companyenrich-api-key"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def find_similar_companies_single(request: SingleDomainRequest) -> dict:
    """
    Find similar companies for a single domain (synchronous).
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    companyenrich_key = os.environ["COMPANYENRICH_API_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = _process_single_domain(
            supabase=supabase,
            companyenrich_key=companyenrich_key,
            domain=request.domain,
            similarity_weight=request.similarity_weight,
            country_code=request.country_code,
            batch_id=request.batch_id,
        )

        return {
            "success": True,
            **result,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _process_single_domain_with_retry(
    supabase,
    companyenrich_key: str,
    domain: str,
    similarity_weight: float,
    country_code: str,
    batch_id: str = None,
    max_retries: int = 3,
) -> dict:
    """
    Process a single domain with retry logic for transient errors.
    Uses exponential backoff between retries.
    """
    for attempt in range(max_retries):
        try:
            return _process_single_domain(
                supabase=supabase,
                companyenrich_key=companyenrich_key,
                domain=domain,
                similarity_weight=similarity_weight,
                country_code=country_code,
                batch_id=batch_id,
            )
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Attempt {attempt + 1} failed for {domain}: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise  # Re-raise on final attempt


def _process_single_domain(
    supabase,
    companyenrich_key: str,
    domain: str,
    similarity_weight: float,
    country_code: str,
    batch_id: str = None,
) -> dict:
    """
    Process a single domain: call API, store raw, extract results.
    """
    # Build API request
    api_url = "https://api.companyenrich.com/companies/similar/preview"
    headers = {
        "Authorization": f"Bearer {companyenrich_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "domains": [domain],
        "similarityWeight": similarity_weight,
    }

    # Add country filter if provided
    if country_code:
        payload["countries"] = [country_code]

    # Call API
    response = requests.post(api_url, json=payload, headers=headers)

    # Store raw response
    raw_insert = (
        supabase.schema("raw")
        .from_("company_enrich_similar_raw")
        .insert({
            "batch_id": batch_id,
            "input_domain": domain,
            "similarity_weight": similarity_weight,
            "country_code": country_code,
            "raw_response": response.json() if response.status_code == 200 else None,
            "status_code": response.status_code,
            "error_message": response.text if response.status_code != 200 else None,
        })
        .execute()
    )
    raw_id = raw_insert.data[0]["id"]

    # Extract similar companies if successful
    extracted_count = 0
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        scores = data.get("metadata", {}).get("scores", {})

        for item in items:
            company_id = item.get("id")
            score = scores.get(str(company_id)) if company_id else None

            supabase.schema("extracted").from_("company_enrich_similar").insert({
                "raw_id": raw_id,
                "batch_id": batch_id,
                "input_domain": domain,
                "company_id": company_id,
                "company_name": item.get("name"),
                "company_domain": item.get("domain"),
                "company_website": item.get("website"),
                "company_industry": item.get("industry"),
                "company_description": item.get("description"),
                "company_keywords": item.get("keywords"),
                "company_logo_url": item.get("logo_url"),
                "similarity_score": score,
            }).execute()
            extracted_count += 1

    return {
        "domain": domain,
        "raw_id": raw_id,
        "status_code": response.status_code,
        "similar_companies_count": extracted_count,
    }
