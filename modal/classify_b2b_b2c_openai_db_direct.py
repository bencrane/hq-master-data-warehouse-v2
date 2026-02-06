"""
Modal function: classify-b2b-b2c-openai-db-direct

Classifies a company as B2B/B2C using OpenAI and writes directly to database.

Deploy with:
    modal deploy classify_b2b_b2c_openai_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-classify-b2b-b2c-openai-db-direct.modal.run
"""

import modal
import json

app = modal.App("hq-master-data-ingest")

# Database connection
db_secret = modal.Secret.from_name("supabase-db-direct")
openai_secret = modal.Secret.from_name("openai-secret")


@app.function(
    secrets=[db_secret, openai_secret],
    timeout=120,
)
@modal.web_endpoint(method="POST")
def classify_b2b_b2c_openai_db_direct(
    domain: str,
    company_name: str,
    description: str,
    model: str = "gpt-4o",
    workflow_source: str = "openai-native/b2b-b2c/classify/db-direct"
):
    """
    Classify a company as B2B/B2C using OpenAI and write to database.

    1. Call OpenAI with company info
    2. Parse response
    3. Write to raw.company_classification_db_direct
    4. Write to extracted.company_classification_db_direct
    5. Write to core.company_business_model
    """
    import os
    import psycopg2
    from openai import OpenAI

    # Initialize OpenAI client
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # Build prompt
    prompt = f"""Given this company information:
- Company Name: {company_name}
- Domain: {domain}
- Description: {description}

Determine if the company primarily sells to businesses/organizations (B2B) and separately if it sells to individual consumers (B2C). Answer each independently with YES or NO, each followed by a one-sentence rationale grounded only in the description.

Respond in this exact JSON format:
{{
    "is_b2b": true/false,
    "b2b_reason": "One sentence rationale",
    "is_b2c": true/false,
    "b2c_reason": "One sentence rationale"
}}"""

    try:
        # Call OpenAI
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a business analyst. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else None

        # Parse response
        result = json.loads(content)
        is_b2b = result.get("is_b2b")
        b2b_reason = result.get("b2b_reason")
        is_b2c = result.get("is_b2c")
        b2c_reason = result.get("b2c_reason")

        # Connect to database
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()

        try:
            # 1. Write to raw table
            cur.execute("""
                INSERT INTO raw.company_classification_db_direct
                    (domain, company_name, description, model, prompt, response, tokens_used)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (domain, company_name, description, model, prompt, json.dumps({"raw": content}), tokens_used))
            raw_id = cur.fetchone()[0]

            # 2. Write to extracted table
            cur.execute("""
                INSERT INTO extracted.company_classification_db_direct
                    (raw_id, domain, is_b2b, b2b_reason, is_b2c, b2c_reason, model, workflow_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (domain) DO UPDATE SET
                    is_b2b = EXCLUDED.is_b2b,
                    b2b_reason = EXCLUDED.b2b_reason,
                    is_b2c = EXCLUDED.is_b2c,
                    b2c_reason = EXCLUDED.b2c_reason,
                    model = EXCLUDED.model,
                    raw_id = EXCLUDED.raw_id
            """, (str(raw_id), domain, is_b2b, b2b_reason, is_b2c, b2c_reason, model, workflow_source))

            # 3. Write to core table
            cur.execute("""
                INSERT INTO core.company_business_model
                    (domain, is_b2b, is_b2c, workflow_source, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    is_b2b = EXCLUDED.is_b2b,
                    is_b2c = EXCLUDED.is_b2c,
                    workflow_source = EXCLUDED.workflow_source,
                    updated_at = NOW()
            """, (domain, is_b2b, is_b2c, workflow_source))

            conn.commit()

            return {
                "success": True,
                "domain": domain,
                "is_b2b": is_b2b,
                "b2b_reason": b2b_reason,
                "is_b2c": is_b2c,
                "b2c_reason": b2c_reason,
                "tokens_used": tokens_used,
                "raw_id": str(raw_id)
            }

        except Exception as db_error:
            conn.rollback()
            raise db_error
        finally:
            cur.close()
            conn.close()

    except Exception as e:
        return {
            "success": False,
            "domain": domain,
            "error": str(e)
        }
