"""
Parallel AI Task Enrichment Endpoints

Uses Parallel AI Task API to enrich company data:
- HQ Location
- Industry
- Competitors

Writes results directly to core.company_parallel_* tables.
"""

import os
import time
import modal
from config import app, image


def call_parallel_task_api(input_data: dict, task_spec: dict, timeout_seconds: int = 120) -> dict:
    """
    Submit task to Parallel AI and poll for completion.
    Returns the output content or error dict.
    """
    import httpx

    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        return {"success": False, "error": "PARALLEL_API_KEY not configured"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            # Submit task
            submit_response = client.post(
                "https://api.parallel.ai/v1/tasks/runs",
                headers=headers,
                json={
                    "input": input_data,
                    "processor": "core",
                    "task_spec": task_spec
                }
            )

            if submit_response.status_code not in (200, 202):
                return {
                    "success": False,
                    "error": f"Submit failed: {submit_response.status_code}",
                    "detail": submit_response.text
                }

            task_result = submit_response.json()
            run_id = task_result.get("run_id")

            if not run_id:
                return {"success": False, "error": "No run_id returned"}

            # Poll for completion
            result_url = f"https://api.parallel.ai/v1/tasks/runs/{run_id}"
            poll_interval = 3
            max_attempts = timeout_seconds // poll_interval

            for _ in range(max_attempts):
                time.sleep(poll_interval)

                poll_response = client.get(result_url, headers=headers)

                if poll_response.status_code != 200:
                    continue

                poll_result = poll_response.json()
                status = poll_result.get("run", {}).get("status") or poll_result.get("status")

                if status == "completed":
                    return {
                        "success": True,
                        "content": poll_result.get("output", {}).get("content", {})
                    }
                elif status == "failed":
                    return {"success": False, "error": "Task failed"}

            return {"success": False, "error": "Task timed out"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_db_connection():
    """Get Supabase connection."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


# =============================================================================
# HQ Location Endpoint
# =============================================================================

@app.function(
    image=image,
    timeout=180,
    secrets=[
        modal.Secret.from_name("parallel-ai-secret"),
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def infer_parallel_hq_location(request: dict) -> dict:
    """
    Infer company HQ location using Parallel AI Task API.
    Writes to core.company_parallel_locations.

    Expects: {"domain": "...", "company_name": "...", "company_linkedin_url": "..."}
    """
    domain = request.get("domain", "").strip()
    company_name = request.get("company_name", "").strip()
    company_linkedin_url = request.get("company_linkedin_url", "")
    workflow_source = request.get("workflow_source", "parallel-task/hq-location/infer/db-direct")

    if not domain or not company_name:
        return {"success": False, "error": "domain and company_name required"}

    input_data = {
        "domain": domain,
        "company_name": company_name,
    }
    if company_linkedin_url:
        input_data["company_linkedin_url"] = company_linkedin_url

    task_spec = {
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "hq_city": {
                        "type": "string",
                        "description": "City where company HQ is located"
                    },
                    "hq_state": {
                        "type": "string",
                        "description": "State/province where company HQ is located"
                    },
                    "hq_country": {
                        "type": "string",
                        "description": "Country where company HQ is located"
                    }
                },
                "required": ["hq_country"]
            }
        },
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "company_name": {"type": "string"},
                    "company_linkedin_url": {"type": "string"}
                }
            }
        }
    }

    result = call_parallel_task_api(input_data, task_spec)

    if not result.get("success"):
        return result

    content = result.get("content", {})
    hq_city = content.get("hq_city")
    hq_state = content.get("hq_state")
    hq_country = content.get("hq_country")

    # Write to database
    try:
        supabase = get_db_connection()
        supabase.schema("core").table("company_parallel_locations").upsert({
            "domain": domain,
            "hq_city": hq_city,
            "hq_state": hq_state,
            "hq_country": hq_country,
            "source": "parallel-task-api",
            "workflow_source": workflow_source,
        }, on_conflict="domain").execute()
    except Exception as e:
        return {"success": False, "error": f"Database write failed: {e}"}

    return {
        "success": True,
        "domain": domain,
        "hq_city": hq_city,
        "hq_state": hq_state,
        "hq_country": hq_country
    }


# =============================================================================
# Industry Endpoint
# =============================================================================

@app.function(
    image=image,
    timeout=180,
    secrets=[
        modal.Secret.from_name("parallel-ai-secret"),
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def infer_parallel_industry(request: dict) -> dict:
    """
    Infer company industry using Parallel AI Task API.
    Writes to core.company_parallel_industries.

    Expects: {"domain": "...", "company_name": "...", "company_linkedin_url": "..."}
    """
    domain = request.get("domain", "").strip()
    company_name = request.get("company_name", "").strip()
    company_linkedin_url = request.get("company_linkedin_url", "")
    workflow_source = request.get("workflow_source", "parallel-task/industry/infer/db-direct")

    if not domain or not company_name:
        return {"success": False, "error": "domain and company_name required"}

    input_data = {
        "domain": domain,
        "company_name": company_name,
    }
    if company_linkedin_url:
        input_data["company_linkedin_url"] = company_linkedin_url

    task_spec = {
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "Primary industry the company operates in"
                    },
                    "sub_industry": {
                        "type": "string",
                        "description": "More specific sub-industry or vertical"
                    }
                },
                "required": ["industry"]
            }
        },
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "company_name": {"type": "string"},
                    "company_linkedin_url": {"type": "string"}
                }
            }
        }
    }

    result = call_parallel_task_api(input_data, task_spec)

    if not result.get("success"):
        return result

    content = result.get("content", {})
    industry = content.get("industry")
    sub_industry = content.get("sub_industry")

    # Write to database
    try:
        supabase = get_db_connection()
        supabase.schema("core").table("company_parallel_industries").upsert({
            "domain": domain,
            "industry": industry,
            "sub_industry": sub_industry,
            "source": "parallel-task-api",
            "workflow_source": workflow_source,
        }, on_conflict="domain").execute()
    except Exception as e:
        return {"success": False, "error": f"Database write failed: {e}"}

    return {
        "success": True,
        "domain": domain,
        "industry": industry,
        "sub_industry": sub_industry
    }


# =============================================================================
# Competitors Endpoint
# =============================================================================

@app.function(
    image=image,
    timeout=180,
    secrets=[
        modal.Secret.from_name("parallel-ai-secret"),
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def infer_parallel_competitors(request: dict) -> dict:
    """
    Infer company competitors using Parallel AI Task API.
    Writes to core.company_parallel_competitors.

    Expects: {"domain": "...", "company_name": "...", "company_linkedin_url": "..."}
    """
    import json

    domain = request.get("domain", "").strip()
    company_name = request.get("company_name", "").strip()
    company_linkedin_url = request.get("company_linkedin_url", "")
    workflow_source = request.get("workflow_source", "parallel-task/competitors/infer/db-direct")

    if not domain or not company_name:
        return {"success": False, "error": "domain and company_name required"}

    input_data = {
        "domain": domain,
        "company_name": company_name,
    }
    if company_linkedin_url:
        input_data["company_linkedin_url"] = company_linkedin_url

    task_spec = {
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "competitors": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "domain": {"type": "string"},
                                "reason": {"type": "string"}
                            }
                        },
                        "description": "List of competitor companies"
                    }
                },
                "required": ["competitors"]
            }
        },
        "input_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "company_name": {"type": "string"},
                    "company_linkedin_url": {"type": "string"}
                }
            }
        }
    }

    result = call_parallel_task_api(input_data, task_spec)

    if not result.get("success"):
        return result

    content = result.get("content", {})
    competitors = content.get("competitors", [])

    # Write to database
    try:
        supabase = get_db_connection()
        supabase.schema("core").table("company_parallel_competitors").upsert({
            "domain": domain,
            "competitors": json.dumps(competitors),
            "source": "parallel-task-api",
            "workflow_source": workflow_source,
        }, on_conflict="domain").execute()
    except Exception as e:
        return {"success": False, "error": f"Database write failed: {e}"}

    return {
        "success": True,
        "domain": domain,
        "competitors": competitors
    }
