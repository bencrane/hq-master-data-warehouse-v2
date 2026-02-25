"""
Extract ICP Titles — Claude Haiku Normalization

Takes raw Parallel.ai output (inconsistent schemas) and normalizes it into
a consistent structure via Claude Haiku, then persists to
extracted.parallel_icp_job_titles_normalized.
"""

import json
import os
from typing import Any, Optional

import modal
from pydantic import BaseModel, Field, field_validator

from config import app, image

HAIKU_MODEL = "claude-haiku-4-5-20251001"
INPUT_COST_PER_MTOK = 0.80
OUTPUT_COST_PER_MTOK = 4.00
MAX_TOKENS = 8192

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


class ExtractICPTitlesRequest(BaseModel):
    company_domain: str = Field(min_length=1)
    raw_parallel_output: str = Field(min_length=1)
    raw_parallel_icp_id: Optional[str] = None

    @field_validator("company_domain", mode="before")
    @classmethod
    def _strip_domain(cls, value: Any) -> str:
        if value is None:
            raise ValueError("company_domain is required")
        text = str(value).strip()
        if not text:
            raise ValueError("company_domain cannot be empty")
        return text.lower().replace("https://", "").replace("http://", "").strip("/")

    @field_validator("raw_parallel_output", mode="before")
    @classmethod
    def _strip_raw(cls, value: Any) -> str:
        if value is None:
            raise ValueError("raw_parallel_output is required")
        text = str(value).strip()
        if not text:
            raise ValueError("raw_parallel_output cannot be empty")
        return text

    @field_validator("raw_parallel_icp_id", mode="before")
    @classmethod
    def _strip_id(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


def _parse_raw_output(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"raw_parallel_output is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"raw_parallel_output must be a JSON object, got {type(parsed).__name__}")
    return parsed


def _compute_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        (input_tokens / 1_000_000 * INPUT_COST_PER_MTOK)
        + (output_tokens / 1_000_000 * OUTPUT_COST_PER_MTOK),
        6,
    )


def _parse_claude_response(text: str) -> dict:
    """Parse Claude's JSON response, handling possible markdown fencing."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


def _count_by_role(titles: list[dict], role: str) -> int:
    return sum(1 for t in titles if isinstance(t, dict) and t.get("buyer_role") == role)


def _persist_normalized(
    supabase: Any,
    company_domain: str,
    company_name: Optional[str],
    titles: list[dict],
    title_count: int,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    cost_usd: float,
    raw_parallel_icp_id: Optional[str],
) -> str:
    record = {
        "company_domain": company_domain,
        "company_name": company_name,
        "titles": titles,
        "title_count": title_count,
        "champion_count": _count_by_role(titles, "champion"),
        "evaluator_count": _count_by_role(titles, "evaluator"),
        "decision_maker_count": _count_by_role(titles, "decision_maker"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "updated_at": "now()",
    }
    if raw_parallel_icp_id:
        record["raw_parallel_icp_id"] = raw_parallel_icp_id

    result = (
        supabase.schema("extracted")
        .from_("parallel_icp_job_titles_normalized")
        .upsert(record, on_conflict="company_domain")
        .execute()
    )
    return result.data[0]["id"]


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("anthropic-api"),
        modal.Secret.from_name("supabase-credentials"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST", label="extract-icp-titles")
def extract_icp_titles(request: ExtractICPTitlesRequest) -> dict:
    import anthropic
    from supabase import create_client

    parsed_input = _parse_raw_output(request.raw_parallel_output)
    parsed_input["company_domain"] = request.company_domain

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": json.dumps(parsed_input, ensure_ascii=False)},
        ],
    )

    raw_text = message.content[0].text
    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    cost_usd = _compute_cost(input_tokens, output_tokens)

    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": cost_usd,
    }

    try:
        result = _parse_claude_response(raw_text)
    except (json.JSONDecodeError, IndexError) as exc:
        return {
            "success": False,
            "error": f"Claude returned unparseable JSON: {exc}",
            "raw_response": raw_text[:2000],
            "usage": usage,
        }

    titles = result.get("titles", [])
    title_count = result.get("title_count", len(titles))
    company_domain = result.get("company_domain", request.company_domain)
    company_name = result.get("company_name")

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    normalized_id = _persist_normalized(
        supabase=supabase,
        company_domain=company_domain,
        company_name=company_name,
        titles=titles,
        title_count=title_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=cost_usd,
        raw_parallel_icp_id=request.raw_parallel_icp_id,
    )

    return {
        "success": True,
        "normalized_id": normalized_id,
        "company_domain": company_domain,
        "company_name": company_name,
        "titles": titles,
        "title_count": title_count,
        "usage": usage,
    }
