"""
Modal function: infer-revenue-db-direct

Infers company annual revenue using Parallel AI Task Enrichment API
and writes directly to database.

Deploy with:
    modal deploy infer_revenue_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-infer-revenue-db-direct.modal.run
"""

import modal
import json
import time
from pydantic import BaseModel
from typing import Optional

app = modal.App("hq-master-data-ingest")

# Image with required dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "psycopg2-binary",
    "requests",
    "fastapi",
    "pydantic",
)

# Secrets
db_secret = modal.Secret.from_name("supabase-db-direct")
parallel_secret = modal.Secret.from_name("parallel-secret")

PARALLEL_TASK_API_URL = "https://api.parallel.ai/v1/tasks/runs"


class RevenueRequest(BaseModel):
    domain: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    workflow_source: str = "parallel-native/revenue/infer/db-direct"


@app.function(
    image=image,
    secrets=[db_secret, parallel_secret],
    timeout=180,  # Longer timeout for async API polling
)
@modal.fastapi_endpoint(method="POST")
def infer_revenue_db_direct(request: RevenueRequest):
    """
    Infer company annual revenue using Parallel AI Task Enrichment API.

    1. Submit task to Parallel AI
    2. Poll for completion
    3. Write to core.company_revenue
    """
    import os
    import requests
    import psycopg2

    domain = request.domain
    company_name = request.company_name
    company_linkedin_url = request.company_linkedin_url
    workflow_source = request.workflow_source

    parallel_api_key = os.environ["PARALLEL_API_KEY"]

    # Build input for Parallel AI
    input_data = {
        "domain": domain,
        "company_name": company_name,
    }
    if company_linkedin_url:
        input_data["company_linkedin_url"] = company_linkedin_url

    # Task specification for revenue enrichment
    task_spec = {
        "output_schema": {
            "type": "object",
            "properties": {
                "annual_revenue_usd": {
                    "type": "integer",
                    "description": "Estimated annual revenue in USD (e.g., 50000000 for $50M)"
                },
                "revenue_range": {
                    "type": "string",
                    "description": "Revenue range if exact not available (e.g., '$10M - $50M')"
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the estimate"
                }
            },
            "required": ["confidence"]
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Company website domain"},
                "company_name": {"type": "string", "description": "Company name"},
                "company_linkedin_url": {"type": "string", "description": "Company LinkedIn URL"}
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {parallel_api_key}",
        "Content-Type": "application/json"
    }

    try:
        # 1. Submit task
        submit_response = requests.post(
            PARALLEL_TASK_API_URL,
            headers=headers,
            json={
                "input": input_data,
                "processor": "core",
                "task_spec": task_spec
            },
            timeout=30
        )

        if submit_response.status_code != 200:
            return {
                "success": False,
                "domain": domain,
                "error": f"Parallel API submit failed: {submit_response.status_code} - {submit_response.text}"
            }

        task_result = submit_response.json()
        run_id = task_result.get("run_id")

        if not run_id:
            return {
                "success": False,
                "domain": domain,
                "error": "No run_id returned from Parallel API"
            }

        # 2. Poll for completion
        result_url = f"{PARALLEL_TASK_API_URL}/{run_id}"
        max_attempts = 30
        poll_interval = 2  # seconds

        output = None
        for attempt in range(max_attempts):
            time.sleep(poll_interval)

            poll_response = requests.get(result_url, headers=headers, timeout=30)

            if poll_response.status_code != 200:
                continue

            poll_result = poll_response.json()
            status = poll_result.get("run", {}).get("status") or poll_result.get("status")

            if status == "completed":
                output = poll_result.get("output", {}).get("content", {})
                break
            elif status == "failed":
                return {
                    "success": False,
                    "domain": domain,
                    "error": "Parallel AI task failed"
                }

        if not output:
            return {
                "success": False,
                "domain": domain,
                "error": "Parallel AI task timed out"
            }

        annual_revenue_usd = output.get("annual_revenue_usd")
        revenue_range = output.get("revenue_range")
        confidence = output.get("confidence")

        # 3. Write to database
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO core.company_revenue
                    (domain, raw_revenue_amount, raw_revenue_range, source, workflow_source, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    raw_revenue_amount = EXCLUDED.raw_revenue_amount,
                    raw_revenue_range = COALESCE(EXCLUDED.raw_revenue_range, core.company_revenue.raw_revenue_range),
                    source = EXCLUDED.source,
                    workflow_source = EXCLUDED.workflow_source,
                    updated_at = NOW()
            """, (domain, annual_revenue_usd, revenue_range, "parallel-task-api", workflow_source))

            conn.commit()

            return {
                "success": True,
                "domain": domain,
                "annual_revenue_usd": annual_revenue_usd,
                "revenue_range": revenue_range,
                "confidence": confidence
            }

        except Exception as db_error:
            conn.rollback()
            return {
                "success": False,
                "domain": domain,
                "error": f"Database error: {str(db_error)}"
            }
        finally:
            cur.close()
            conn.close()

    except Exception as e:
        return {
            "success": False,
            "domain": domain,
            "error": str(e)
        }
