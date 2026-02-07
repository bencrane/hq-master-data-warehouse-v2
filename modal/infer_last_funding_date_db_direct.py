"""
Modal function: infer-last-funding-date-db-direct

Infers company last funding date using Parallel AI Task Enrichment API
and writes directly to database.

Deploy with:
    modal deploy infer_last_funding_date_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-infer-last-funding-date-db-direct.modal.run
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


class LastFundingDateRequest(BaseModel):
    domain: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    workflow_source: str = "parallel-native/last-funding-date/infer/db-direct"


@app.function(
    image=image,
    secrets=[db_secret, parallel_secret],
    timeout=180,  # Longer timeout for async API polling
)
@modal.fastapi_endpoint(method="POST")
def infer_last_funding_date_db_direct(request: LastFundingDateRequest):
    """
    Infer company last funding date using Parallel AI Task Enrichment API.

    1. Submit task to Parallel AI
    2. Poll for completion
    3. Write to core.company_funding_rounds
    """
    import os
    import requests
    import psycopg2
    from datetime import datetime

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

    # Task specification for last funding date enrichment
    task_spec = {
        "output_schema": {
            "type": "object",
            "properties": {
                "last_funding_date": {
                    "type": "string",
                    "description": "Date of most recent funding round in YYYY-MM-DD format"
                },
                "funding_type": {
                    "type": "string",
                    "description": "Type of most recent funding (e.g., 'Series B', 'Seed')"
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

        last_funding_date_str = output.get("last_funding_date")
        funding_type = output.get("funding_type")
        confidence = output.get("confidence")

        # Parse the date if provided
        funding_date = None
        if last_funding_date_str:
            try:
                funding_date = datetime.strptime(last_funding_date_str, "%Y-%m-%d")
            except ValueError:
                # Try other common formats
                for fmt in ["%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"]:
                    try:
                        funding_date = datetime.strptime(last_funding_date_str, fmt)
                        break
                    except ValueError:
                        continue

        # 3. Write to database
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO core.company_funding_rounds
                    (domain, funding_date, funding_type, source, workflow_source, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    funding_date = EXCLUDED.funding_date,
                    funding_type = COALESCE(EXCLUDED.funding_type, core.company_funding_rounds.funding_type),
                    source = EXCLUDED.source,
                    workflow_source = EXCLUDED.workflow_source,
                    updated_at = NOW()
            """, (domain, funding_date, funding_type, "parallel-task-api", workflow_source))

            conn.commit()

            return {
                "success": True,
                "domain": domain,
                "last_funding_date": last_funding_date_str,
                "funding_type": funding_type,
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
