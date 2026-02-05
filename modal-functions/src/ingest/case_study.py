"""
Case Study Ingestion Endpoints

- ingest_case_study_extraction: Extract details from case study URL using Gemini 3 Flash
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image

from extraction.case_study import extract_case_study_details, extract_case_study_champions


class CaseStudyExtractionRequest(BaseModel):
    origin_company_name: str
    origin_company_domain: str
    case_study_url: str
    company_customer_name: str
    workflow_slug: str


# Gemini extraction prompt
# NOTE: Inputs are at the bottom for token caching efficiency
EXTRACTION_PROMPT = """You are extracting structured data from a case study webpage. The "origin company" is the company that PUBLISHED the case study on their website. The "customer company" is the company FEATURED in the case study as a success story.

Your job is to extract: the article title, the customer company's domain (if findable), and any "champions" (people quoted or featured).

**Extractions:**

1. **article_title**: The title/headline of the case study article.

2. **customer_company_domain**: The website domain of the customer company.
   - ONLY extract if the domain is hyperlinked or explicitly listed on the page
   - If you cannot find it on the page, return null
   - Do NOT guess or infer the domain
   - Format: just the domain, e.g., "citi.com" not "https://www.citi.com"

3. **champions**: People quoted or featured in the case study.
   - For each person, extract:
     - full_name: Their complete name
     - job_title: Their job title (if mentioned, else null)
     - company_name: The company they work for as stated in the article (if mentioned, else null)
   - If no champions found, return an empty array

4. **confidence**: Your confidence in the extraction accuracy: "high", "medium", or "low".

5. **reasoning**: 1-2 sentences explaining your extraction process or any issues encountered.

**Response Format:**
Return ONLY valid JSON:
{{
    "article_title": "The title of the case study",
    "customer_company_domain": "example.com" or null,
    "champions": [
        {{
            "full_name": "John Smith",
            "job_title": "VP of Engineering",
            "company_name": "Acme Corp"
        }}
    ],
    "confidence": "high",
    "reasoning": "Found 2 champions quoted with job titles. Domain was hyperlinked in footer."
}}

---

**Inputs:**

Case Study URL: {case_study_url}

Origin Company (publisher): {origin_company_name} ({origin_company_domain})

Company Customer (featured): {company_customer_name}
Note: The company customer name above may have slight variations in capitalization or formatting compared to how it appears in the article. Match by recognizing it refers to the same company.
"""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def ingest_case_study_extraction(request: CaseStudyExtractionRequest) -> dict:
    """
    Extract case study details using Gemini 3 Flash.
    Stores raw Gemini response, then extracts to case_study_details and case_study_champions.
    """
    from supabase import create_client
    import google.generativeai as genai

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)

    try:
        # Look up workflow in registry
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", request.workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found"}

        # Build prompt
        prompt = EXTRACTION_PROMPT.format(
            case_study_url=request.case_study_url,
            origin_company_name=request.origin_company_name,
            origin_company_domain=request.origin_company_domain,
            company_customer_name=request.company_customer_name,
        )

        # Call Gemini 3 Flash
        model = genai.GenerativeModel("gemini-3-flash-preview")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,  # Low temperature for consistent extraction
            ),
        )

        # Parse Gemini response
        try:
            gemini_response = json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse Gemini response as JSON",
                "raw_response": response.text,
            }

        # Extract token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        total_tokens = input_tokens + output_tokens
        # Gemini 3 Flash Preview pricing: $0.50/1M input, $3.00/1M output
        cost_usd = (input_tokens * 0.50 / 1_000_000) + (output_tokens * 3.00 / 1_000_000)

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("case_study_extraction_payloads")
            .insert({
                "case_study_url": request.case_study_url,
                "origin_company_domain": request.origin_company_domain,
                "origin_company_name": request.origin_company_name,
                "company_customer_name": request.company_customer_name,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": gemini_response,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract case study details
        case_study_id = extract_case_study_details(
            supabase,
            raw_id,
            request.case_study_url,
            request.origin_company_domain,
            request.origin_company_name,
            request.company_customer_name,
            gemini_response,
        )

        # Update core.company_customers with extracted domain
        customer_domain = gemini_response.get("customer_company_domain")
        if customer_domain:
            try:
                supabase.schema("core").from_("company_customers").update(
                    {"customer_domain": customer_domain, "customer_domain_source": "gemini-3-flash-preview"}
                ).eq("case_study_url", request.case_study_url).execute()
            except Exception:
                pass  # Non-fatal — domain update is best-effort

        # Extract champions
        champion_count = 0
        if case_study_id:
            champion_count = extract_case_study_champions(
                supabase,
                case_study_id,
                gemini_response,
            )

        return {
            "success": True,
            "raw_id": raw_id,
            "case_study_id": case_study_id,
            "origin_company_name": request.origin_company_name,
            "origin_company_domain": request.origin_company_domain,
            "company_customer_name": request.company_customer_name,
            "champion_count": champion_count,
            "champions": gemini_response.get("champions", []),
            "customer_domain_found": gemini_response.get("customer_company_domain") is not None,
            "customer_domain": gemini_response.get("customer_company_domain"),
            "article_title": gemini_response.get("article_title"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_usd, 6),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

