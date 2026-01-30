"""
Case Study Buyer Extraction

Simple endpoint that extracts buyer info from a case study URL using Gemini 2.0 Flash.
Returns result directly to Clay - no database storage.
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class CaseStudyBuyerRequest(BaseModel):
    origin_company_name: str  # The company that published the case study
    origin_company_domain: str  # The publisher's domain
    customer_company_name: str  # The company featured in the case study
    case_study_url: str


EXTRACTION_PROMPT = """#CONTEXT#
You are an AI-powered web scraper. You will be given a URL to a company case study page: {case_study_url}

The page may be labeled as a case study, success story, testimonial, or partner story. Your task is to extract structured information from that single page only.

**IMPORTANT - Do NOT confuse these two companies:**
- Origin/Publisher Company: {origin_company_name} ({origin_company_domain}) - This is the company that PUBLISHED this case study. Do NOT return this company's information.
- Customer/Featured Company: {customer_company_name} - This is the company FEATURED in the case study as a success story. Extract information about THIS company.

#OBJECTIVE#
Extract the customer company being featured, its domain (if found), and ALL people quoted/giving testimonials along with their job titles.

#INSTRUCTIONS#
1. Navigate only to the exact URL provided. Do not browse to other pages or links.

2. Identify the customer company:
   - This is the company featured as the success story (should match: {customer_company_name})
   - Do NOT return {origin_company_name} - that is the publisher, not the customer

3. Find the customer company's domain:
   - ONLY extract if hyperlinked on the page or explicitly written
   - Look for links to the customer's website, or email addresses (e.g., jane@acme.com → acme.com)
   - Do NOT guess or infer from company name
   - Do NOT return {origin_company_domain} - that is the publisher's domain
   - Format: bare domain only (e.g., "acme.com" not "https://www.acme.com")

4. Find ALL people quoted/giving testimonials:
   - Look for quotation blocks, pull quotes, text in quotation marks
   - Look for labels like "Testimonial," "Customer quote," "What they said"
   - Look for speaker attributions near quotes (name, job title, company)
   - Extract EVERY person quoted, not just one

5. For each person, extract:
   - fullName: Their complete name
   - jobTitle: Their job title (if mentioned, else empty string)

6. Data integrity:
   - Do NOT infer or fabricate any values
   - Only use content visible on the given page
   - If a field is not found, use empty string ""
   - Preserve original capitalization

#RESPONSE FORMAT#
Return ONLY valid JSON:
{{
    "customer_company_name": "Customer Corp",
    "customer_company_domain": "customercorp.com",
    "people": [
        {{
            "fullName": "Jane Smith",
            "jobTitle": "VP of Operations"
        }},
        {{
            "fullName": "John Doe",
            "jobTitle": "Director of Engineering"
        }}
    ]
}}

If no people are quoted, return empty array for people.
If domain not found, return empty string for customer_company_domain.
"""


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("gemini-secret")],
    timeout=60,
)
@modal.fastapi_endpoint(method="POST")
def extract_case_study_buyer(request: CaseStudyBuyerRequest) -> dict:
    """
    Extract buyer info from case study URL using Gemini 2.0 Flash.
    Returns extracted fields directly - no database storage.
    """
    import google.generativeai as genai

    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)

    try:
        # Build prompt
        prompt = EXTRACTION_PROMPT.format(
            case_study_url=request.case_study_url,
            customer_company_name=request.customer_company_name,
            origin_company_name=request.origin_company_name,
            origin_company_domain=request.origin_company_domain,
        )

        # Call Gemini 2.5 Flash Lite - can fetch URL content directly
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        # Parse response
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse Gemini response as JSON",
                "raw_response": response.text,
            }

        # Get token usage for cost calculation
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0

        # Gemini 2.0 Flash pricing: $0.10/1M input, $0.40/1M output
        cost = (input_tokens * 0.10 / 1_000_000) + (output_tokens * 0.40 / 1_000_000)

        # Return extracted fields directly
        return {
            "success": True,
            "customer_company_name": result.get("customer_company_name", ""),
            "customer_company_domain": result.get("customer_company_domain", ""),
            "people": result.get("people", []),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
