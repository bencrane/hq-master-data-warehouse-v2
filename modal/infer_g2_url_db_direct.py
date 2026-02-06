"""
Modal function: infer-g2-url-db-direct

Finds G2 reviews page URL using Parallel AI Search API
and writes directly to database.

Deploy with:
    modal deploy infer_g2_url_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-infer-g2-url-db-direct.modal.run
"""

import modal
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

PARALLEL_SEARCH_API_URL = "https://api.parallel.ai/v1beta/search"


class G2UrlRequest(BaseModel):
    domain: str
    company_name: str
    cleaned_company_name: Optional[str] = None
    workflow_source: str = "parallel-native/g2-url/infer/db-direct"


@app.function(
    image=image,
    secrets=[db_secret, parallel_secret],
    timeout=60,
)
@modal.fastapi_endpoint(method="POST")
def infer_g2_url_db_direct(request: G2UrlRequest):
    """
    Find G2 reviews page URL using Parallel AI Search API.

    1. Call Parallel Search API with interpolated objective
    2. Parse results to find g2.com URL
    3. Write to core.company_g2
    """
    import os
    import requests
    import psycopg2

    domain = request.domain
    company_name = request.company_name
    cleaned_company_name = request.cleaned_company_name
    workflow_source = request.workflow_source

    parallel_api_key = os.environ["PARALLEL_API_KEY"]

    # Use cleaned_company_name if provided, otherwise fall back to company_name
    search_name = cleaned_company_name if cleaned_company_name else company_name

    # Build the search objective
    objective = f"Find the G2 reviews page URL for {search_name} whose domain = {domain}"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": parallel_api_key,
        "parallel-beta": "search-extract-2025-10-10"
    }

    payload = {
        "mode": "one-shot",
        "search_queries": None,
        "max_results": 10,
        "objective": objective
    }

    try:
        # Call Parallel Search API
        response = requests.post(
            PARALLEL_SEARCH_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            return {
                "success": False,
                "domain": domain,
                "error": f"Parallel Search API failed: {response.status_code} - {response.text}"
            }

        search_result = response.json()
        results = search_result.get("results", [])

        # Find the G2 URL from results
        g2_url = None
        for result in results:
            url = result.get("url", "")
            if "g2.com" in url:
                g2_url = url
                break

        if not g2_url:
            return {
                "success": False,
                "domain": domain,
                "error": "No G2 URL found in search results",
                "results_count": len(results)
            }

        # Write to database
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO core.company_g2
                    (domain, g2_url, workflow_source, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    g2_url = EXCLUDED.g2_url,
                    workflow_source = EXCLUDED.workflow_source,
                    updated_at = NOW()
            """, (domain, g2_url, workflow_source))

            conn.commit()

            return {
                "success": True,
                "domain": domain,
                "g2_url": g2_url
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
