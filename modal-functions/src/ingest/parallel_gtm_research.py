"""
Parallel GTM Research Endpoint

Calls Parallel.ai Deep Research API (Pro processor) to conduct comprehensive
GTM intelligence research on a company - customers, buyer titles, buyer language,
competitive dynamics, and market signals.

Cost: $0.10 per run (Pro processor)

Expects:
{
  "company_name": "Vanta",
  "domain": "vanta.com"
}

Returns comprehensive GTM intelligence with attributed sources.
"""

import json
import os
import time
from typing import Any, Optional

import modal
import requests
from pydantic import BaseModel, Field, field_validator

from config import app, image

PRO_COST_PER_RUN = 0.10
PARALLEL_BASE_URL = "https://api.parallel.ai/v1"
PARALLEL_HTTP_TIMEOUT_SECONDS = 60
DEFAULT_WAIT_SECONDS = 300  # 5 minutes default
MAX_WAIT_SECONDS = 600  # 10 minutes max


class ParallelGTMResearchRequest(BaseModel):
    company_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    wait_seconds: Optional[int] = DEFAULT_WAIT_SECONDS

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

    @field_validator("wait_seconds")
    @classmethod
    def _validate_wait_seconds(cls, value: Optional[int]) -> int:
        if value is None:
            return DEFAULT_WAIT_SECONDS
        return max(60, min(MAX_WAIT_SECONDS, value))


PROMPT_TEMPLATE = """You are a GTM intelligence researcher tasked with conducting GTM intelligence research on {company_name}, {domain}. Your job is to produce the raw material for a go-to-market strategy brief that will make the company's leadership receiving it feel like an outsider understands their market better than their own team does. Go deep. Exhaust every source. The output should contain evidence and insights that {company_name}'s own sales and marketing team likely does not have — hidden customer relationships, buyer language they've never seen, competitive blind spots, market signals buried in places they aren't looking. Research {company_name}, {domain} and return everything below. For every claim, include an attributed source URL.

Customer Evidence — Go Wide
Find every customer of {company_name} you can. Start with their website (case studies, logos, testimonials) but don't stop there. Search press releases, partner blogs, integration directories, third-party aggregator sites, news articles, podcast appearances, conference talks, and any web source that reveals a customer relationship they may not publicly showcase. For each customer: company name, website, LinkedIn URL, and the source URL proving the relationship. For case studies and testimonials: champion's full name, title, company, and pull the most compelling direct quotes — especially quantified outcomes (hours saved, revenue impact, cost reduction, time-to-value, efficiency multipliers). These quotes may end up in the final deliverable, so capture the ones that hit hardest.

Real Buyer Titles — From the Field, Not Personas
Search G2, TrustRadius, Capterra, PeerSpot, Reddit, and Slack/Discord communities for {company_name} reviews and mentions. Return the actual job titles of people reviewing, recommending, or discussing the product. These are the real buyers — not marketing personas. Capture title, source platform, and any context about their role in the purchase decision.

Buyer Language — What Makes Them Move
From reviews, forums, social posts, and community discussions, extract the raw language real buyers use to describe: The pain that made them look for a solution. The trigger event that started the buying process. What they were doing before (manual process, competitor product, nothing). What almost killed the deal (objections, friction, internal pushback). The moment they knew it was working. Capture direct quotes where possible. This language is gold — it reveals messaging angles {company_name}'s own team may have never tested.

Competitive Dynamics — Who They're Really Fighting
Find every competitor mentioned in reviews, comparison pages, analyst reports, Reddit threads, and {company_name}'s own positioning. For each competitor, capture: Where they were mentioned and by whom. Whether the reviewer switched from, evaluated against, or chose {company_name} over them. Any specific reasons given for the win or loss. Look for competitors {company_name} may not even be tracking — adjacent tools, DIY approaches, or emerging players showing up in buyer conversations.

Market Signals They Can't See From Inside
Search for third-party sources that track {company_name}'s footprint from the outside — aggregator sites, technology tracking platforms, certificate transparency logs, integration marketplaces, job boards, and industry reports. Return: Customer base estimates and methodology. Churn or renewal signals. Adoption trends by segment, geography, or company size. Anything that reveals the shape of their market that they wouldn't get from their own CRM.

The goal is density of real, cited, surprising evidence. The more "how did they find that" moments in the output, the better. Return the raw intelligence, analysis, insights and concrete recommendations."""


def _request_or_raise(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    """Make HTTP request and raise on error."""
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
    """Submit task to Parallel AI Deep Research."""
    return _request_or_raise(
        "POST",
        f"{PARALLEL_BASE_URL}/tasks/runs",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"input": input_data, "processor": "pro"},
        timeout=PARALLEL_HTTP_TIMEOUT_SECONDS,
    )


def _retrieve_parallel_task_result(run_id: str, api_key: str, wait_seconds: int) -> dict[str, Any]:
    """Poll for task completion."""
    result_url = f"{PARALLEL_BASE_URL}/tasks/runs/{run_id}/result"
    headers = {"x-api-key": api_key}

    response = requests.get(
        result_url,
        headers=headers,
        params={"wait": wait_seconds},
        timeout=wait_seconds + 30,
    )

    if response.status_code == 408:
        # Timeout - task still running
        return {"status": "running", "run_id": run_id}

    if not response.ok:
        raise RuntimeError(f"Parallel API {response.status_code}: {response.text[:1000]}")

    return response.json()


def _parse_possible_json_string(content: str) -> Any:
    """Parse JSON from string, handling markdown code blocks."""
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
    """Extract content from Parallel AI response."""
    output = result_payload.get("output")
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, str):
            return _parse_possible_json_string(content)
        return content
    if isinstance(output, str):
        return _parse_possible_json_string(output)
    return output


@app.function(
    image=image,
    timeout=900,  # 15 minutes - Deep Research can take time
    secrets=[
        modal.Secret.from_name("parallel-ai"),
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def parallel_gtm_research(request: ParallelGTMResearchRequest) -> dict:
    """
    Conduct comprehensive GTM intelligence research using Parallel AI Deep Research.

    Returns customer evidence, buyer titles, buyer language, competitive dynamics,
    and market signals - all with attributed source URLs.
    """
    from supabase import create_client

    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        return {"success": False, "error": "PARALLEL_API_KEY not configured"}

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.domain
        company_name = request.company_name
        wait_seconds = request.wait_seconds

        # Build prompt
        prompt = PROMPT_TEMPLATE.format(
            company_name=company_name,
            domain=domain,
        )

        # Submit task to Parallel AI
        submit_result = _create_parallel_task_run(prompt, api_key)
        run_id = submit_result.get("run_id")

        if not run_id:
            return {"success": False, "error": "No run_id returned from Parallel AI"}

        # Store initial raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("parallel_gtm_research")
            .insert({
                "company_name": company_name,
                "domain": domain,
                "run_id": run_id,
                "raw_payload": {"status": "submitted", "run_id": run_id},
                "success": False,
                "cost_usd": PRO_COST_PER_RUN,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"] if raw_insert.data else None

        # Poll for result
        result = _retrieve_parallel_task_result(run_id, api_key, wait_seconds)

        if result.get("status") == "running":
            return {
                "success": True,
                "done": False,
                "status": "running",
                "run_id": run_id,
                "raw_payload_id": str(raw_payload_id) if raw_payload_id else None,
                "domain": domain,
                "company_name": company_name,
                "message": "Task still running. Poll again with run_id.",
            }

        # Extract output
        output = _extract_output_content(result)

        # Update raw payload with result
        if raw_payload_id:
            supabase.schema("raw").from_("parallel_gtm_research").update({
                "raw_payload": {
                    "status": "completed",
                    "run_id": run_id,
                    "result": result,
                    "output": output,
                },
                "success": True,
            }).eq("id", raw_payload_id).execute()

        # Upsert to extracted table
        supabase.schema("extracted").from_("parallel_gtm_research").upsert({
            "raw_payload_id": raw_payload_id,
            "company_name": company_name,
            "domain": domain,
            "run_id": run_id,
            "output": output if isinstance(output, dict) else {"raw_text": str(output)},
            "cost_usd": PRO_COST_PER_RUN,
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "done": True,
            "domain": domain,
            "company_name": company_name,
            "run_id": run_id,
            "raw_payload_id": str(raw_payload_id) if raw_payload_id else None,
            "output": output,
            "cost_usd": PRO_COST_PER_RUN,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.domain,
            "company_name": request.company_name,
        }
