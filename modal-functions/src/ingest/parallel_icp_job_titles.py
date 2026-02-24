"""
Parallel ICP Job Titles Endpoint

Calls Parallel.ai Deep Research API, then writes both raw and extracted records.
"""

import json
import os
from typing import Any, Optional

import modal
import requests
from pydantic import BaseModel, Field, field_validator

from config import app, image

PRO_COST_PER_RUN = 0.10
PARALLEL_BASE_URL = "https://api.parallel.ai/v1"
PARALLEL_RESULT_TIMEOUT_SECONDS = 3300
PARALLEL_HTTP_TIMEOUT_SECONDS = 60


class ParallelICPJobTitlesRequest(BaseModel):
    company_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    company_description: Optional[str] = None

    @field_validator("company_name", "domain", mode="before")
    @classmethod
    def _strip_required_fields(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Field is required")
        text = str(value).strip()
        if not text:
            raise ValueError("Field cannot be empty")
        return text

    @field_validator("domain")
    @classmethod
    def _normalize_domain(cls, value: str) -> str:
        return value.lower().replace("https://", "").replace("http://", "").strip("/")

    @field_validator("company_description", mode="before")
    @classmethod
    def _normalize_company_description(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


PROMPT_TEMPLATE = """CONTEXT
You are a B2B buyer persona researcher. You will be given a company name, domain, and optionally a company description. Your job is to research this company thoroughly and produce an exhaustive list of job titles that represent realistic buyers, champions, evaluators, and decision-makers for this company's product(s).

INPUTS
companyName: {company_name}
domain: {domain}
companyDescription: {company_description}

RESEARCH INSTRUCTIONS
1. Research the company
   - Visit the company website to understand what they sell, who they sell to, and how they position their product.
   - Review case studies, testimonials, and customer logos to identify real buyers and users.
   - Check G2, TrustRadius, Capterra, and similar review platforms. Look specifically at reviewer job titles.
   - Review the company's LinkedIn presence and any published ICP or buyer persona content.
   - Search: "[companyName] case study" "[companyName] customer story"
   - Capture any named roles or titles.

2. Identify the buying committee
   Determine realistic roles for:
   - Champions: Day-to-day users or people experiencing the problem directly.
   - Evaluators: Technical or operational stakeholders who run POCs or compare alternatives.
   - Decision makers: Budget owners and signers. Only include if appropriate.

3. Generate title variations
   - Include realistic seniority variants only where appropriate.
   - Include function-specific variants where relevant.

CRITICAL GUARDRAILS
- Every title must be grounded in evidence from company website, reviews, case studies, or known buyer patterns.
- Do not guess or hallucinate titles.
- Exclude roles that would reasonably not care about or buy this product.
- Do not include generic functional labels.
- Quantity target: 30-60 titles; never pad.

OUTPUT FORMAT
companyName: {company_name}
domain: {domain}
inferredProduct: One sentence describing what the company sells and to whom, based on your research.
buyerPersona: 2-3 sentences describing the buying committee — who champions it, who evaluates it, who signs off.
titles: For each title include title, buyerRole (champion | evaluator | decision_maker), and reasoning.
"""


def _parse_possible_json_string(content: str) -> Any:
    text = content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if not candidate:
                continue
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    return {"raw_text": content}


def _extract_output_content(result_payload: dict[str, Any]) -> Any:
    output = result_payload.get("output")
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, str):
            return _parse_possible_json_string(content)
        return content
    if isinstance(output, str):
        return _parse_possible_json_string(output)
    return output


def _request_or_raise(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    response = requests.request(method, url, **kwargs)
    if not response.ok:
        body_text = response.text
        try:
            body_text = json.dumps(response.json())
        except Exception:
            pass
        raise RuntimeError(f"Parallel API {response.status_code}: {body_text[:1000]}")

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Parallel API returned non-JSON response") from exc


def _create_parallel_task_run(input_data: str, api_key: str) -> dict[str, Any]:
    return _request_or_raise(
        "POST",
        f"{PARALLEL_BASE_URL}/tasks/runs",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"input": input_data, "processor": "pro"},
        timeout=PARALLEL_HTTP_TIMEOUT_SECONDS,
    )


def _retrieve_parallel_task_result(run_id: str, api_key: str) -> dict[str, Any]:
    return _request_or_raise(
        "GET",
        f"{PARALLEL_BASE_URL}/tasks/runs/{run_id}/result",
        headers={"x-api-key": api_key},
        params={"timeout": PARALLEL_RESULT_TIMEOUT_SECONDS},
        timeout=PARALLEL_RESULT_TIMEOUT_SECONDS + 60,
    )


def _extract_titles_by_role(titles: list[dict[str, Any]], role: str) -> list[dict[str, str]]:
    return [
        {"title": str(t.get("title", "")).strip(), "reasoning": str(t.get("reasoning", "")).strip()}
        for t in titles
        if isinstance(t, dict)
        and str(t.get("buyerRole", "")).strip() == role
        and str(t.get("title", "")).strip()
    ]


def _extract_all_title_strings(titles: list[dict[str, Any]]) -> list[str]:
    return [
        str(t.get("title", "")).strip()
        for t in titles
        if isinstance(t, dict) and str(t.get("title", "")).strip()
    ]


def _insert_failed_raw(supabase: Any, request: ParallelICPJobTitlesRequest, error_message: str, run_id: Optional[str]) -> None:
    supabase.schema("raw").from_("parallel_icp_job_titles").insert(
        {
            "company_name": request.company_name,
            "domain": request.domain,
            "company_description": request.company_description,
            "run_id": run_id,
            "raw_payload": {"success": False, "error": error_message, "runId": run_id},
            "success": False,
            "error_message": error_message,
        }
    ).execute()


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("parallel.ai"),
        modal.Secret.from_name("supabase-credentials"),
    ],
    timeout=3600,
)
@modal.fastapi_endpoint(method="POST", label="icp-titles")
def parallel_icp_job_titles(request: ParallelICPJobTitlesRequest) -> dict:
    from supabase import create_client

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        raise ValueError("PARALLEL_API_KEY not found in environment")

    input_data = PROMPT_TEMPLATE.format(
        company_name=request.company_name,
        domain=request.domain,
        company_description=request.company_description or "Not provided.",
    )

    run_id: Optional[str] = None
    try:
        task_run = _create_parallel_task_run(input_data=input_data, api_key=api_key)
        run_id = task_run.get("run_id")
        if not run_id:
            raise RuntimeError("Parallel task run missing run_id")

        run_result = _retrieve_parallel_task_result(run_id=run_id, api_key=api_key)
        output = _extract_output_content(run_result)

        titles_raw = output.get("titles", []) if isinstance(output, dict) else []
        titles = titles_raw if isinstance(titles_raw, list) else []
        champion_titles = _extract_titles_by_role(titles, "champion")
        evaluator_titles = _extract_titles_by_role(titles, "evaluator")
        decision_maker_titles = _extract_titles_by_role(titles, "decision_maker")
        all_titles = _extract_all_title_strings(titles)

        raw_payload = {
            "success": True,
            "runId": run_id,
            "companyName": request.company_name,
            "domain": request.domain,
            "taskRun": task_run,
            "taskResult": run_result,
            "output": output,
        }

        raw_insert = (
            supabase.schema("raw")
            .from_("parallel_icp_job_titles")
            .insert(
                {
                    "company_name": request.company_name,
                    "domain": request.domain,
                    "company_description": request.company_description,
                    "run_id": run_id,
                    "raw_payload": raw_payload,
                    "success": True,
                    "cost_usd": PRO_COST_PER_RUN,
                }
            )
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        supabase.schema("extracted").from_("parallel_icp_job_titles").upsert(
            {
                "raw_payload_id": raw_payload_id,
                "company_name": request.company_name,
                "domain": request.domain,
                "run_id": run_id,
                "inferred_product": output.get("inferredProduct") if isinstance(output, dict) else None,
                "buyer_persona": output.get("buyerPersona") if isinstance(output, dict) else None,
                "champion_titles": champion_titles,
                "evaluator_titles": evaluator_titles,
                "decision_maker_titles": decision_maker_titles,
                "all_titles": all_titles,
                "total_title_count": len(titles),
                "champion_count": len(champion_titles),
                "evaluator_count": len(evaluator_titles),
                "decision_maker_count": len(decision_maker_titles),
                "cost_usd": PRO_COST_PER_RUN,
            },
            on_conflict="domain",
        ).execute()

        return {
            "success": True,
            "runId": run_id,
            "companyName": request.company_name,
            "domain": request.domain,
            "output": output,
            "costUsd": PRO_COST_PER_RUN,
            "titleCount": len(titles),
            "championCount": len(champion_titles),
            "evaluatorCount": len(evaluator_titles),
            "decisionMakerCount": len(decision_maker_titles),
            "stored": {"rawPayloadId": raw_payload_id, "extractedUpserted": True},
        }
    except Exception as exc:
        error_message = str(exc)
        try:
            _insert_failed_raw(supabase, request, error_message, run_id)
        except Exception:
            pass

        return {
            "success": False,
            "error": error_message,
            "companyName": request.company_name,
            "domain": request.domain,
            "runId": run_id,
        }
