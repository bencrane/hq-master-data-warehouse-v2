"""
Assess ICP Fit Endpoint

Modal endpoint that uses Gemini 3 Flash with web browsing to assess
whether a job title is someone a company would sell to.
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class AssessICPFitRequest(BaseModel):
    company_name: str
    company_domain: str
    company_description: str
    job_title: str


class AssessICPFitResponse(BaseModel):
    verdict: str
    reason: str
    jobTitle: str
    companyName: str


PROMPT_TEMPLATE = """#CONTEXT#
You are a B2B sales targeting analyst. You will receive a company's name, domain, description, and a single person's job title.

Before assessing, browse the company's website at {company_domain} to understand what they sell, who their customers are, and which roles within those customers use/buy/champion the product. Use this alongside the provided company description.

#OBJECTIVE#
Determine whether this person is someone the company would sell to. Return a strict JSON object with: verdict, reason, jobTitle, companyName.

#INSTRUCTIONS#
1. From the company website and description, identify:
   - What the company sells (product/service)
   - Who uses it (end users), who evaluates/champions it (influencers), who approves/buys it (decision-makers)

2. From the job title, determine the person's core function and seniority.

3. Decision rule:
   - Would this person evaluate, champion, approve, or directly use this product?
   - If yes → verdict "yes"
   - If no → verdict "no"

4. Heuristics:
   - Err toward "yes" for roles functionally adjacent to likely buyers
   - Err toward "no" for unrelated functions (sales, HR, legal, finance) unless the product specifically targets those functions
   - Ambiguous or empty titles with no functional signal → "no"
   - Strip jargon, verticals, qualifiers — focus on core function

5. Output rules:
   - Strict JSON, camelCase keys: verdict, reason, jobTitle, companyName
   - No additional fields or commentary
   - reason: one sentence connecting the person's function to what the company sells and who uses it

6. Edge cases:
   - If company website is unreachable and description is non-informative → verdict "no", reason citing insufficient context
   - If job title is missing/blank/ambiguous → verdict "no", reason citing insufficient role signal

#INPUT#
Company Name: {company_name}
Company Domain: {company_domain}
Company Description: {company_description}

Job Title: {job_title}

#OUTPUT#
Return only valid JSON:"""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini-secret"),
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def assess_icp_fit(request: AssessICPFitRequest) -> dict:
    """
    Assess whether a job title is someone the company would sell to.
    Uses Gemini 3 Flash with web browsing/grounding.
    """
    import google.generativeai as genai
    from supabase import create_client

    # Initialize Gemini
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    genai.configure(api_key=api_key)

    # Use Gemini 3 Flash
    model = genai.GenerativeModel("gemini-3-flash-preview")

    # Build prompt
    prompt = PROMPT_TEMPLATE.format(
        company_name=request.company_name,
        company_domain=request.company_domain,
        company_description=request.company_description,
        job_title=request.job_title,
    )

    try:
        # Call Gemini with JSON response
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )

        # Parse response
        result = json.loads(response.text)

        # Handle if Gemini returns a list instead of dict
        if isinstance(result, list):
            result = result[0] if result else {}

        # Get token counts
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        # Gemini 3 Flash pricing: $0.15/1M input, $0.60/1M output
        cost_usd = (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)

        # Normalize verdict to lowercase
        verdict = result.get("verdict", "no").lower()
        reason = result.get("reason", "")
        job_title = result.get("jobTitle", request.job_title)
        company_name = result.get("companyName", request.company_name)

        # Store in Supabase
        supabase_url = os.environ["SUPABASE_URL"]
        supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
        supabase = create_client(supabase_url, supabase_key)

        supabase.schema("core").table("icp_verdicts").upsert(
            {
                "company_name": request.company_name,
                "company_domain": request.company_domain,
                "company_description": request.company_description,
                "job_title": request.job_title,
                "verdict": verdict,
                "reason": reason,
            },
            on_conflict="company_domain,job_title",
        ).execute()

        return {
            "verdict": verdict,
            "reason": reason,
            "jobTitle": job_title,
            "companyName": company_name,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "costUsd": round(cost_usd, 6),
        }

    except json.JSONDecodeError as e:
        return {
            "verdict": "no",
            "reason": f"Failed to parse Gemini response: {e}",
            "jobTitle": request.job_title,
            "companyName": request.company_name,
        }
    except Exception as e:
        return {
            "verdict": "no",
            "reason": f"Error: {str(e)}",
            "jobTitle": request.job_title,
            "companyName": request.company_name,
        }
