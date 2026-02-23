"""
Generate curated ICP title patterns from raw champion titles using Gemini 3 Flash.

Two endpoints:
1. POST trigger (fast): kicks off background worker, returns immediately
2. Background worker: processes all companies, writes to DB

Trigger: POST /run/companies/icp/generate-title-patterns
  {"limit": 500}

Stores results in derived.company_icp_title_patterns.
Idempotent — skips companies that already have patterns.
"""

import os
import json
import time
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image

PROMPT_TEMPLATE = """You are analyzing case study champion job titles for a B2B software company to identify their ICP (Ideal Customer Profile) buyer personas.

Company domain: {domain}

Here are the job titles of champions/contacts from their case studies:
{titles}

Based on these titles, identify the 3-8 distinct ICP buyer persona title patterns this company sells to.

Rules:
- Collapse similar titles into one pattern (e.g. "Director of Marketing", "VP Marketing", "Head of Marketing" → one pattern)
- Ignore generic titles like "CEO", "Founder", "Co-Founder", "President", "Managing Director" — these are noise from case studies, not the actual buyer persona
- Focus on the FUNCTIONAL role, not the seniority (e.g. "Demand Generation" not "VP of Demand Generation")
- Each pattern should have 2-5 matching keywords that would appear in a LinkedIn title for that persona
- Keywords should be lowercase, specific enough to avoid false positives (e.g. "demand generation" not just "marketing")
- Strip company names from any titles before analyzing

Return ONLY valid JSON in this exact format:
{{
  "patterns": [
    {{
      "title_pattern": "Human-readable pattern name",
      "keywords": ["keyword1", "keyword2", "keyword3"]
    }}
  ]
}}

Return only the JSON, nothing else."""

DB_URL = "postgresql://postgres:Txi4V4wjoWCIr0Og@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"


class GenerateICPPatternsRequest(BaseModel):
    limit: Optional[int] = 500


@app.function(
    image=image,
    timeout=3600,
    secrets=[modal.Secret.from_name("gemini-secret")],
)
def _process_icp_patterns_batch(limit: int) -> dict:
    import google.generativeai as genai
    import psycopg2

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3-flash-preview")
    conn = psycopg2.connect(DB_URL)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT csc.origin_company_domain,
                   ARRAY_AGG(DISTINCT csc.job_title ORDER BY csc.job_title) AS titles
            FROM core.case_study_champions csc
            WHERE csc.job_title IS NOT NULL
              AND csc.job_title != ''
              AND csc.job_title != 'null'
              AND csc.origin_company_domain NOT IN (
                  SELECT DISTINCT domain FROM derived.company_icp_title_patterns
              )
            GROUP BY csc.origin_company_domain
            HAVING COUNT(DISTINCT csc.job_title) >= 3
            ORDER BY COUNT(*) DESC
            LIMIT %s
        """, (limit,))
        companies = cur.fetchall()

    total_input = 0
    total_output = 0
    success = 0
    errors = 0

    for i, (domain, titles) in enumerate(companies):
        try:
            titles_text = "\n".join(f"- {t}" for t in titles[:50])
            prompt = PROMPT_TEMPLATE.format(domain=domain, titles=titles_text)

            response = model.generate_content(prompt)
            text = response.text.strip()

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            parsed = json.loads(text)
            patterns = parsed.get("patterns", [])

            total_input += response.usage_metadata.prompt_token_count
            total_output += response.usage_metadata.candidates_token_count

            if patterns:
                with conn.cursor() as cur:
                    for p in patterns:
                        title_pattern = p.get("title_pattern", "")
                        keywords = p.get("keywords", [])
                        if not title_pattern or not keywords:
                            continue
                        cur.execute("""
                            INSERT INTO derived.company_icp_title_patterns
                                (domain, title_pattern, pattern_keywords, source)
                            VALUES (%s, %s, %s, 'gemini-3-flash')
                            ON CONFLICT (domain, title_pattern) DO NOTHING
                        """, (domain, title_pattern, keywords))
                conn.commit()
                success += 1

            if (i + 1) % 50 == 0:
                cost = (total_input * 0.15 / 1_000_000) + (total_output * 0.60 / 1_000_000)
                print(f"Progress: {i+1}/{len(companies)} | {success} ok, {errors} err | ${cost:.4f}")
                time.sleep(0.3)

        except Exception as e:
            errors += 1
            print(f"Error on {domain}: {e}")
            time.sleep(0.5)

    conn.close()
    cost = (total_input * 0.15 / 1_000_000) + (total_output * 0.60 / 1_000_000)
    return {
        "processed": len(companies),
        "ok": success,
        "errors": errors,
        "cost_usd": round(cost, 4),
    }


@app.function(image=image, timeout=30)
@modal.fastapi_endpoint(method="POST")
def generate_icp_title_patterns(request: GenerateICPPatternsRequest) -> dict:
    call = _process_icp_patterns_batch.spawn(request.limit)
    return {
        "success": True,
        "message": f"Background job started for up to {request.limit} companies",
        "call_id": call.object_id,
    }
