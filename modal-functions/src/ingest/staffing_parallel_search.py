"""
Ingest Staffing Parallel AI Search Results

Stores Parallel AI search results for staffing research.

Expects the full response from the search-parallel-ai endpoint:
{
  "domain": "example.com",
  "success": true,
  "company_name": "",
  "parallel_response": {
    "usage": [...],
    "results": [...],
    "search_id": "..."
  }
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def ingest_staffing_parallel_search(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        company_name = request.get("company_name", "")
        objective = request.get("objective", "")
        success = request.get("success", False)
        parallel_response = request.get("parallel_response", {})

        if not domain:
            return {"success": False, "error": "No domain provided"}

        if not success:
            return {"success": False, "error": "Parallel search was not successful", "domain": domain}

        # Extract data from parallel_response
        results = parallel_response.get("results", [])
        search_id = parallel_response.get("search_id", "")

        # Get URLs from results
        urls = [r.get("url", "") for r in results if r.get("url")]

        # Build excerpts summary (first 500 chars of first excerpt from each result)
        excerpts_parts = []
        for r in results[:5]:  # Limit to first 5 results
            excerpts = r.get("excerpts", [])
            if excerpts:
                excerpts_parts.append(excerpts[0][:500])
        excerpts_summary = "\n\n---\n\n".join(excerpts_parts) if excerpts_parts else None

        # 1. Store raw payload
        raw_result = supabase.table("staffing_parallel_search_payloads").insert({
            "domain": domain,
            "company_name": company_name,
            "objective": objective,
            "payload": request
        }, returning="representation").execute()

        raw_id = raw_result.data[0]["id"] if raw_result.data else None

        # 2. Store extracted data
        supabase.table("staffing_parallel_search").insert({
            "domain": domain,
            "company_name": company_name,
            "search_id": search_id,
            "result_count": len(results),
            "urls": urls,
            "excerpts_summary": excerpts_summary[:5000] if excerpts_summary else None,
            "raw_payload_id": raw_id
        }).execute()

        return {
            "success": True,
            "domain": domain,
            "search_id": search_id,
            "result_count": len(results),
            "urls_stored": len(urls)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
