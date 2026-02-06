"""
Modal function: extract-g2-insights-db-direct

Extracts G2 review insights using Gemini and writes directly to database.

Deploy with:
    modal deploy extract_g2_insights_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-extract-g2-insights-db-direct.modal.run
"""

import modal
import json
from pydantic import BaseModel

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
gemini_secret = modal.Secret.from_name("gemini-secret")


class G2InsightsRequest(BaseModel):
    domain: str
    g2_url: str
    workflow_source: str = "gemini-native/g2-insights/extract/db-direct"


@app.function(
    image=image,
    secrets=[db_secret, gemini_secret],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def extract_g2_insights_db_direct(request: G2InsightsRequest):
    """
    Extract G2 review insights using Gemini.

    1. Call Gemini API with G2 URL and extraction prompt
    2. Parse response
    3. Write to core.company_g2_insights
    """
    import os
    import requests as req
    import psycopg2

    domain = request.domain
    g2_url = request.g2_url
    workflow_source = request.workflow_source

    gemini_api_key = os.environ["GEMINI_API_KEY"]

    # Build the prompt
    prompt = f"""Extract from this G2 reviews page:
1. Overall rating (e.g., 4.5/5)
2. Total number of reviews
3. Top 3-5 common complaints or pain points from reviews
4. Top 3-5 common praise points from reviews
5. Any specific negative quotes that highlight frustrations

URL: {g2_url}

Respond in this exact JSON format:
{{
    "overall_rating": "4.5/5",
    "total_reviews": "1234",
    "top_complaints": ["complaint 1", "complaint 2", "complaint 3"],
    "top_praise": ["praise 1", "praise 2", "praise 3"],
    "negative_quotes": ["quote 1", "quote 2"]
}}"""

    # Gemini API endpoint
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    try:
        # Call Gemini API
        response = req.post(
            gemini_url,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "domain": domain,
                "error": f"Gemini API failed: {response.status_code} - {response.text}"
            }

        gemini_result = response.json()

        # Extract the text content from Gemini response
        try:
            content = gemini_result["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return {
                "success": False,
                "domain": domain,
                "error": f"Failed to parse Gemini response: {str(e)}",
                "raw_response": gemini_result
            }

        overall_rating = parsed.get("overall_rating")
        total_reviews = parsed.get("total_reviews")
        top_complaints = parsed.get("top_complaints", [])
        top_praise = parsed.get("top_praise", [])
        negative_quotes = parsed.get("negative_quotes", [])

        # Write to database
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO core.company_g2_insights
                    (domain, g2_url, overall_rating, total_reviews, top_complaints,
                     top_praise, negative_quotes, raw_response, workflow_source, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    g2_url = EXCLUDED.g2_url,
                    overall_rating = EXCLUDED.overall_rating,
                    total_reviews = EXCLUDED.total_reviews,
                    top_complaints = EXCLUDED.top_complaints,
                    top_praise = EXCLUDED.top_praise,
                    negative_quotes = EXCLUDED.negative_quotes,
                    raw_response = EXCLUDED.raw_response,
                    workflow_source = EXCLUDED.workflow_source,
                    updated_at = NOW()
            """, (
                domain,
                g2_url,
                overall_rating,
                total_reviews,
                json.dumps(top_complaints),
                json.dumps(top_praise),
                json.dumps(negative_quotes),
                json.dumps(parsed),
                workflow_source
            ))

            conn.commit()

            return {
                "success": True,
                "domain": domain,
                "g2_url": g2_url,
                "overall_rating": overall_rating,
                "total_reviews": total_reviews,
                "top_complaints": top_complaints,
                "top_praise": top_praise,
                "negative_quotes": negative_quotes
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
