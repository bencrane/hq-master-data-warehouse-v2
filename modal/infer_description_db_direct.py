"""
Modal function: infer-description-db-direct

Infers company description using Parallel AI Task Enrichment API
and writes directly to database.

Deploy with:
    modal deploy infer_description_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-infer-description-db-direct.modal.run
"""

import modal
import json
import time

app = modal.App("hq-master-data-ingest")

# Secrets
db_secret = modal.Secret.from_name("supabase-db-direct")
parallel_secret = modal.Secret.from_name("parallel-secret")

PARALLEL_TASK_API_URL = "https://api.parallel.ai/v1/tasks/runs"


@app.function(
    secrets=[db_secret, parallel_secret],
    timeout=180,  # Longer timeout for async API polling
)
@modal.web_endpoint(method="POST")
def infer_description_db_direct(
    domain: str,
    company_name: str,
    company_linkedin_url: str = None,
    workflow_source: str = "parallel-native/description/infer/db-direct"
):
    """
    Infer company description using Parallel AI Task Enrichment API.

    1. Submit task to Parallel AI
    2. Poll for completion
    3. Write to core.company_descriptions
    """
    import os
    import requests
    import psycopg2

    parallel_api_key = os.environ["PARALLEL_API_KEY"]

    # Build input for Parallel AI
    input_data = {
        "domain": domain,
        "company_name": company_name,
    }
    if company_linkedin_url:
        input_data["company_linkedin_url"] = company_linkedin_url

    # Task specification for description enrichment
    task_spec = {
        "output_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A 2-3 sentence description of what the company does, who they serve, and their primary value proposition."
                },
                "tagline": {
                    "type": "string",
                    "description": "A short one-line tagline or slogan for the company."
                }
            },
            "required": ["description"]
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

        description = output.get("description")
        tagline = output.get("tagline")

        if not description:
            return {
                "success": False,
                "domain": domain,
                "error": "No description returned from Parallel AI"
            }

        # 3. Write to database
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO core.company_descriptions
                    (domain, description, tagline, source, workflow_source, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    description = EXCLUDED.description,
                    tagline = COALESCE(EXCLUDED.tagline, core.company_descriptions.tagline),
                    source = EXCLUDED.source,
                    workflow_source = EXCLUDED.workflow_source,
                    updated_at = NOW()
            """, (domain, description, tagline, "parallel-task-api", workflow_source))

            conn.commit()

            return {
                "success": True,
                "domain": domain,
                "description": description,
                "tagline": tagline
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
