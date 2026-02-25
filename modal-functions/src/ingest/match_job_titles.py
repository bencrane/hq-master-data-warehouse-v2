"""
Match Job Titles — GPT-4.1 Nano Classification

Stateless endpoint that takes a candidate job title and a list of ICP job
titles, then classifies each as SAME JOB or DIFFERENT JOB via GPT-4.1 nano.
"""

import json
import os
from typing import Any

import modal
from pydantic import BaseModel, Field, field_validator

from config import app, image

MODEL = "gpt-4.1-nano"
INPUT_COST_PER_MTOK = 0.10
OUTPUT_COST_PER_MTOK = 0.40
MAX_TOKENS = 4096

SYSTEM_PROMPT = """#CONTEXT#
You will be given a CANDIDATE TITLE and a LIST OF JOB TITLES. Your task is to compare the CANDIDATE TITLE against each job title in the list individually and determine whether they represent, by and large, the same set of responsibilities. Not a promotion, not a demotion, not an adjacent role — the same job. The only difference should be what the company decided to print on the business card.

#OBJECTIVE#
Compare the CANDIDATE TITLE to each title in the provided JOB TITLE LIST and output, for each, the job title, a verdict (SAME JOB or DIFFERENT JOB), and a one-sentence reasoning.

#INSTRUCTIONS#
1. For each job title in the JOB TITLE LIST, compare responsibilities implied by the titles. Treat differences in wording, regional variations, and common synonyms as potentially the same if core responsibilities align.
2. Consider the following when deciding SAME JOB vs DIFFERENT JOB:
- SAME JOB indicators: direct synonyms (e.g., "Software Engineer" vs "Software Developer"), minor stylistic differences (e.g., "Sr." vs "Senior"), functionally identical titles across companies (e.g., "Account Executive" vs "Sales Executive").
- DIFFERENT JOB indicators: changes in core function (e.g., "Product Manager" vs "Project Manager"), step-change in level or scope (promotion/demotion like "Manager" vs "Director"), or adjacent but distinct specialties (e.g., "Data Scientist" vs "Data Analyst").
3. Ignore employer-specific branding or internal level codes unless they clearly indicate a different seniority (e.g., L4 vs L5 alone should not switch the job unless scope clearly differs).
4. Do not use any external data. Base judgments solely on the provided titles.
5. Be consistent and conservative: when in doubt, choose DIFFERENT JOB unless the titles are clear synonyms for the same function and level.

Respond with ONLY a JSON array, no markdown, no explanation. Each element:
{"jobTitle": "<title from list>", "verdict": "SAME JOB" or "DIFFERENT JOB", "reasoning": "<one sentence>"}"""


class MatchJobTitlesRequest(BaseModel):
    candidate_title: str = Field(min_length=1)
    job_titles: list[str] = Field(min_length=1)

    @field_validator("candidate_title", mode="before")
    @classmethod
    def _strip_candidate(cls, value: Any) -> str:
        if value is None:
            raise ValueError("candidate_title is required")
        text = str(value).strip()
        if not text:
            raise ValueError("candidate_title cannot be empty")
        return text

    @field_validator("job_titles", mode="before")
    @classmethod
    def _validate_titles(cls, value: Any) -> list[str]:
        if not isinstance(value, list) or len(value) == 0:
            raise ValueError("job_titles must be a non-empty list of strings")
        cleaned = [str(t).strip() for t in value if str(t).strip()]
        if not cleaned:
            raise ValueError("job_titles must contain at least one non-empty string")
        return cleaned


def _compute_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        (input_tokens / 1_000_000 * INPUT_COST_PER_MTOK)
        + (output_tokens / 1_000_000 * OUTPUT_COST_PER_MTOK),
        6,
    )


def _parse_json_response(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("openai-secret")],
    timeout=60,
)
@modal.fastapi_endpoint(method="POST", label="match-job-titles")
def match_job_titles(request: MatchJobTitlesRequest) -> dict:
    import openai

    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    user_message = (
        f"CANDIDATE TITLE: {request.candidate_title}\n"
        f"JOB TITLE LIST: {json.dumps(request.job_titles)}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw_text = response.choices[0].message.content
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": _compute_cost(input_tokens, output_tokens),
    }

    try:
        results = _parse_json_response(raw_text)
    except (json.JSONDecodeError, IndexError) as exc:
        return {
            "success": False,
            "error": f"Model returned unparseable JSON: {exc}",
            "raw_response": raw_text[:2000],
            "usage": usage,
        }

    has_match = any(r.get("verdict") == "SAME JOB" for r in results)
    match_count = sum(1 for r in results if r.get("verdict") == "SAME JOB")

    return {
        "candidate_title": request.candidate_title,
        "results": results,
        "has_match": has_match,
        "match_count": match_count,
        "total_compared": len(request.job_titles),
        "usage": usage,
    }
