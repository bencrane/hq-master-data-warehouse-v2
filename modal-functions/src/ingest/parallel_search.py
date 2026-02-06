"""
Parallel AI Search API Wrapper

Simple passthrough to Parallel AI's Search API.

Expects:
{
  "objective": "Find information about...",
  "search_queries": ["query1", "query2"],  # optional
  "mode": "one-shot",  # one-shot, agentic, fast
  "max_results": 10,  # 1-20
  "domain": "example.com",  # optional, for context
  "company_name": "Example Inc"  # optional, for context
}

Returns: Parallel AI's response
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    timeout=120,
    secrets=[
        modal.Secret.from_name("parallel-ai-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def search_parallel_ai(request: dict) -> dict:
    import httpx

    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        return {"success": False, "error": "PARALLEL_API_KEY not configured"}

    try:
        # Extract parameters
        objective = request.get("objective", "")
        search_queries = request.get("search_queries", [])
        mode = request.get("mode", "one-shot")
        max_results = request.get("max_results", 10)
        domain = request.get("domain", "")
        company_name = request.get("company_name", "")
        source_policy = request.get("source_policy")
        fetch_policy = request.get("fetch_policy")

        # Build objective with domain/company context if provided
        if domain or company_name:
            context = ""
            if company_name:
                context += f"Company: {company_name}. "
            if domain:
                context += f"Domain: {domain}. "
            if objective:
                objective = f"{context}{objective}"
            else:
                objective = context.strip()

        if not objective and not search_queries:
            return {"success": False, "error": "Either objective or search_queries is required"}

        # Build Parallel AI request
        parallel_request = {
            "mode": mode,
            "max_results": max_results,
        }

        if objective:
            parallel_request["objective"] = objective
        if search_queries:
            parallel_request["search_queries"] = search_queries
        if source_policy:
            parallel_request["source_policy"] = source_policy
        if fetch_policy:
            parallel_request["fetch_policy"] = fetch_policy

        # Call Parallel AI
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                "https://api.parallel.ai/v1beta/search",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "parallel-beta": "search-extract-2025-10-10"
                },
                json=parallel_request
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Parallel AI error: {response.status_code}",
                    "detail": response.text
                }

            result = response.json()

        return {
            "success": True,
            "domain": domain,
            "company_name": company_name,
            "parallel_response": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
