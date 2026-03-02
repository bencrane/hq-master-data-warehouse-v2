"""
Gemini ICP Criterion Endpoints

Two endpoints using Gemini 3 Flash:

1. generate_icp_criterion - Creates a company-specific criterion (the core problem)
   Input: company_name, domain, customers, icp_titles
   Output: Single sentence describing the problem

2. evaluate_icp_fit - Evaluates if a target company has the problem
   Input: criterion, company_name, domain, description
   Output: YES/NO + 2 sentence explanation
"""

import os
import json
import modal
from pydantic import BaseModel, Field
from typing import Optional, List

from config import app, image


# =============================================================================
# Endpoint 1: Generate ICP Criterion
# =============================================================================

class GenerateICPCriterionRequest(BaseModel):
    company_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    customers: List[str] = Field(min_items=1)
    icp_titles: List[str] = Field(min_items=1)


GENERATE_CRITERION_PROMPT = """You are a B2B market analyst. Your job is to identify the single core problem that a company's product solves for its customers.

You will be given:
- A company name and domain
- A list of their known customers
- The job titles of people who typically buy their product

From this, infer the one underlying problem or operational reality that connects these customers and buyers. Do not list multiple criteria. Do not describe the product. Do not mention the company by name. Just state the problem that makes a company need this product.

Output a single sentence. Nothing else.

EXAMPLES:

Input:
Vanta, vanta.com
Customers: Ramp, Snowflake, GitHub, Clay, Modern Health, Duolingo
ICP Titles: Head of Security, CISO, Director of Compliance, VP Engineering

Output:
Needs to prove security compliance to close enterprise deals or meet regulatory requirements.

Input:
Rippling, rippling.com
Customers: Superhuman, Dutchie, Quora, Flatfile, Popl
ICP Titles: Head of People, VP HR, CFO, Director of IT, Head of Operations

Output:
Manages a growing headcount and needs unified control over payroll, benefits, devices, and HR operations.

Input:
Gong, gong.io
Customers: LinkedIn, Shopify, Sprinklr, Paychex, Zillow
ICP Titles: VP Sales, CRO, Head of Revenue Operations, Director of Sales Enablement

Output:
Runs a sales org with enough call volume that leadership needs visibility into what reps are actually saying to buyers.

---

{company_name}, {domain}
Customers: {customers}
ICP Titles: {icp_titles}"""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def generate_icp_criterion(request: GenerateICPCriterionRequest) -> dict:
    """
    Generate a single-sentence ICP criterion from company, customers, and titles.
    """
    import google.generativeai as genai
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)

    try:
        # Build prompt
        customers_str = ", ".join(request.customers)
        titles_str = ", ".join(request.icp_titles)

        prompt = GENERATE_CRITERION_PROMPT.format(
            company_name=request.company_name,
            domain=request.domain,
            customers=customers_str,
            icp_titles=titles_str,
        )

        # Call Gemini 3 Flash Preview
        model = genai.GenerativeModel("gemini-3-flash-preview")

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
            ),
        )

        # Extract token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        cost_usd = (input_tokens * 0.50 / 1_000_000) + (output_tokens * 3.00 / 1_000_000)

        # Get the criterion (should be a single sentence)
        criterion = response.text.strip()

        # Store to database
        supabase.schema("core").from_("icp_criteria").upsert({
            "domain": request.domain.lower(),
            "company_name": request.company_name,
            "customers": request.customers,
            "icp_titles": request.icp_titles,
            "criterion": criterion,
            "source": "gemini-generate-icp-criterion",
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": request.domain,
            "company_name": request.company_name,
            "criterion": criterion,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.domain,
        }


# =============================================================================
# Endpoint 2: Evaluate ICP Fit
# =============================================================================

class EvaluateICPFitRequest(BaseModel):
    criterion: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    description: str = Field(min_length=1)


EVALUATE_FIT_PROMPT = """You are a B2B market fit analyst. You will be given a criterion that describes the core problem a specific product solves.

You will then be given a company's name, domain, and description.

Your job is to determine whether this company would realistically have this problem. Do not overthink it. Be opinionated.

Output YES or NO, followed by two sentences explaining why.

Nothing else.

EXAMPLES:

Criterion: Needs to prove security compliance to close enterprise deals or meet regulatory requirements.

Company: Lattice, lattice.com
Description: HR and people management platform for mid-size companies. Performance reviews, engagement surveys, compensation management.

NO. Lattice sells to HR teams, not regulated industries or enterprise buyers requiring compliance certifications. Their sales motion doesn't depend on proving security posture.

---

Criterion: Needs to prove security compliance to close enterprise deals or meet regulatory requirements.

Company: Plaid, plaid.com
Description: Financial data connectivity platform. APIs that let applications connect to users' bank accounts for payments, transactions, and identity verification.

YES. Plaid handles sensitive financial data and connects directly to bank accounts. Every enterprise customer and financial institution they sell to will require SOC 2, ISO 27001, or similar certifications before signing.

---

Criterion: Needs to prove security compliance to close enterprise deals or meet regulatory requirements.

Company: BarkBox, barkbox.com
Description: Monthly subscription box for dog toys, treats, and chews. Direct-to-consumer pet products brand.

NO. BarkBox is a D2C subscription brand selling to individual consumers. There is no enterprise sales cycle or regulatory requirement that would drive a compliance purchase.

---

Criterion: {criterion}

Company: {company_name}, {domain}
Description: {description}"""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def evaluate_icp_fit(request: EvaluateICPFitRequest) -> dict:
    """
    Evaluate whether a target company fits an ICP criterion.
    Returns YES/NO with explanation.
    """
    import google.generativeai as genai
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)

    try:
        # Build prompt
        prompt = EVALUATE_FIT_PROMPT.format(
            criterion=request.criterion,
            company_name=request.company_name,
            domain=request.domain,
            description=request.description,
        )

        # Call Gemini 3 Flash Preview
        model = genai.GenerativeModel("gemini-3-flash-preview")

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
            ),
        )

        # Extract token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        cost_usd = (input_tokens * 0.50 / 1_000_000) + (output_tokens * 3.00 / 1_000_000)

        # Parse response
        result_text = response.text.strip()

        # Extract verdict (YES or NO)
        verdict = "unknown"
        if result_text.upper().startswith("YES"):
            verdict = "yes"
        elif result_text.upper().startswith("NO"):
            verdict = "no"

        # Extract reasoning (everything after YES/NO)
        reasoning = result_text
        if verdict != "unknown":
            # Remove the YES/NO prefix and any following punctuation/whitespace
            for prefix in ["YES.", "YES,", "YES ", "NO.", "NO,", "NO "]:
                if result_text.upper().startswith(prefix):
                    reasoning = result_text[len(prefix):].strip()
                    break

        # Store to database
        supabase.schema("core").from_("icp_fit_evaluations").upsert({
            "target_domain": request.domain.lower(),
            "target_company_name": request.company_name,
            "target_description": request.description,
            "criterion": request.criterion,
            "verdict": verdict,
            "reasoning": reasoning,
            "source": "gemini-evaluate-icp-fit",
        }, on_conflict="target_domain,criterion").execute()

        return {
            "success": True,
            "domain": request.domain,
            "company_name": request.company_name,
            "criterion": request.criterion,
            "verdict": verdict,
            "reasoning": reasoning,
            "raw_response": result_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.domain,
        }
