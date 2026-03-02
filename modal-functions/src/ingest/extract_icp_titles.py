"""
Extract ICP Titles — Claude Haiku Normalization

Takes raw Parallel.ai output (inconsistent schemas) and normalizes it into
a consistent structure via Claude Haiku.

Expects:
{
  "company_domain": "withcoverage.com",
  "raw_parallel_output": "{\"domain\": \"withcoverage.com\", ...}"  // JSON string
}

Returns:
{
  "success": true,
  "company_domain": "withcoverage.com",
  "company_name": "WithCoverage",
  "titles": [
    {"title": "Chief Financial Officer (CFO)", "buyer_role": "decision_maker", "reasoning": "..."},
    ...
  ],
  "title_count": 42,
  "usage": {"input_tokens": 1234, "output_tokens": 567, "cost_usd": 0.00123}
}
"""

import os
import json
import modal
from config import app, image


SYSTEM_PROMPT = """You are a JSON normalizer. You will receive a raw JSON object containing ICP (Ideal Customer Profile) buyer persona data for a company. The schema varies across inputs — sometimes titles are in a flat "titles" array, sometimes in "buyer_personas", sometimes split across "champion_personas", "evaluator_personas", and "decision_maker_personas" arrays.

Your job: extract every job title and normalize into the exact output schema below. Do not add, remove, or infer any titles. Only extract what is present in the input.

OUTPUT SCHEMA (respond with ONLY this JSON, no markdown, no explanation):
{
  "company_domain": "<domain from input>",
  "company_name": "<company_name from input, or null if not present>",
  "titles": [
    {
      "title": "<exact job title string>",
      "buyer_role": "champion" | "evaluator" | "decision_maker",
      "reasoning": "<reasoning string, or null if not present>"
    }
  ],
  "title_count": <integer count of titles extracted>
}

RULES:
- buyer_role must be one of: "champion", "evaluator", "decision_maker"
- Normalize "buyerRole" (camelCase) to "buyer_role" (snake_case)
- If titles are split across champion_personas/evaluator_personas/decision_maker_personas, merge them and assign buyer_role from which array they came from
- If a persona object has extra fields (key_pain_points, primary_responsibilities, key_criteria, etc.), ignore them — only extract title, buyer_role, reasoning
- If reasoning is not present but a different descriptive field exists, use null for reasoning
- Preserve the exact title string — do not normalize, lowercase, or modify it"""


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("anthropic-api"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def extract_icp_titles(request: dict) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    try:
        company_domain = request.get("company_domain", "").strip()
        raw_parallel_output = request.get("raw_parallel_output", "").strip()

        if not company_domain:
            return {"success": False, "error": "company_domain is required"}
        if not raw_parallel_output:
            return {"success": False, "error": "raw_parallel_output is required"}

        # Parse the raw output to validate it's JSON
        try:
            parsed_input = json.loads(raw_parallel_output)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"raw_parallel_output is not valid JSON: {e}"}

        # Ensure company_domain is in the input for Claude
        parsed_input["company_domain"] = company_domain

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": json.dumps(parsed_input, ensure_ascii=False)},
            ],
        )

        response_text = message.content[0].text.strip()
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        # Cost: Haiku 4.5 = $0.80/MTok input, $4.00/MTok output
        cost_usd = round(
            (input_tokens / 1_000_000 * 0.80) + (output_tokens / 1_000_000 * 4.00),
            6,
        )

        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Claude returned unparseable JSON",
                "raw_response": response_text[:2000],
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "cost_usd": cost_usd,
                },
            }

        titles = result.get("titles", [])
        title_count = result.get("title_count", len(titles))

        return {
            "success": True,
            "company_domain": result.get("company_domain", company_domain),
            "company_name": result.get("company_name"),
            "titles": titles,
            "title_count": title_count,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": cost_usd,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "company_domain": request.get("company_domain", "unknown"),
        }
