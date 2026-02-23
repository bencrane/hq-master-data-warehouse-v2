"""
Generate curated ICP title patterns from raw champion titles using Gemini 3.0 Flash.

For each company, sends their champion job titles to Gemini and gets back
3-8 canonical ICP title patterns with matching keywords.

Stores results in derived.company_icp_title_patterns.

Usage:
    python scripts/generate_icp_title_patterns.py [--limit 100] [--batch-size 10]
"""

import os
import json
import time
import argparse
import psycopg2
import google.generativeai as genai

DB_URL = "postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"

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


def get_companies_needing_patterns(conn, limit):
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
        return cur.fetchall()


def generate_patterns(model, domain, titles):
    titles_text = "\n".join(f"- {t}" for t in titles[:50])  # cap at 50 titles
    prompt = PROMPT_TEMPLATE.format(domain=domain, titles=titles_text)

    response = model.generate_content(prompt)
    text = response.text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    result = json.loads(text)
    input_tokens = response.usage_metadata.prompt_token_count
    output_tokens = response.usage_metadata.candidates_token_count

    return result.get("patterns", []), input_tokens, output_tokens


def save_patterns(conn, domain, patterns):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.0-flash")

    conn = psycopg2.connect(DB_URL)
    companies = get_companies_needing_patterns(conn, args.limit)
    print(f"Processing {len(companies)} companies...")

    total_input = 0
    total_output = 0
    success = 0
    errors = 0

    for i, (domain, titles) in enumerate(companies):
        try:
            patterns, inp, out = generate_patterns(model, domain, titles)
            total_input += inp
            total_output += out

            if patterns:
                save_patterns(conn, domain, patterns)
                success += 1
                print(f"[{i+1}/{len(companies)}] {domain}: {len(patterns)} patterns")
            else:
                print(f"[{i+1}/{len(companies)}] {domain}: no patterns returned")

            if (i + 1) % args.batch_size == 0:
                cost = (total_input * 0.15 / 1_000_000) + (total_output * 0.60 / 1_000_000)
                print(f"  --- batch checkpoint: {success} ok, {errors} err, ${cost:.4f} so far ---")
                time.sleep(0.5)

        except json.JSONDecodeError as e:
            errors += 1
            print(f"[{i+1}/{len(companies)}] {domain}: JSON parse error: {e}")
        except Exception as e:
            errors += 1
            print(f"[{i+1}/{len(companies)}] {domain}: error: {e}")
            time.sleep(1)

    cost = (total_input * 0.15 / 1_000_000) + (total_output * 0.60 / 1_000_000)
    print(f"\nDone. {success} ok, {errors} errors. Cost: ${cost:.4f}")
    print(f"Tokens: {total_input} input, {total_output} output")
    conn.close()


if __name__ == "__main__":
    main()
