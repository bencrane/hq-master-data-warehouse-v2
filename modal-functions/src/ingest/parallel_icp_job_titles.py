"""
Parallel ICP Job Titles Endpoint

Calls Parallel.ai Deep Research API to generate ICP job titles for a company.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app


# Custom image with parallel-web SDK
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "parallel-web",
        "pydantic",
        "fastapi",
    )
)


class ParallelICPJobTitlesRequest(BaseModel):
    company_name: str
    domain: str
    company_description: str


PROMPT_TEMPLATE = """# CONTEXT

You are a B2B buyer persona researcher.

You will be given a company name, domain, and optionally a company description. Your job is to research this company thoroughly and produce an exhaustive list of job titles that represent realistic buyers, champions, evaluators, and decision-makers for this company's product(s).

---

# INPUTS

- **companyName:** {company_name}
- **domain:** {domain}
- **companyDescription:**
{company_description}

---

# RESEARCH INSTRUCTIONS

## 1. Research the company

- Visit the company website to understand what they sell, who they sell to, and how they position their product.
- Review case studies, testimonials, and customer logos to identify real buyers and users.
- Check G2, TrustRadius, Capterra, and similar review platforms. Look specifically at reviewer job titles.
- Review the company's LinkedIn presence and any published ICP or buyer persona content.
- Search:
  - "[companyName] case study"
  - "[companyName] customer story"

Capture any named roles or titles.

---

## 2. Identify the buying committee

Determine realistic roles for:

- **Champions**
  Day-to-day users or people experiencing the problem directly. They discover, evaluate, and advocate internally.

- **Evaluators**
  Technical or operational stakeholders who run POCs or compare alternatives.

- **Decision makers**
  Budget owners and signers. Only if appropriate for this product category and price point.

---

## 3. Generate title variations

For each persona:

- Include realistic seniority variants (Manager, Senior Manager, Director, Head, VP, Lead) **only where appropriate**.
- Include function-specific variants where relevant (e.g., Security, Compliance, GRC, Risk).

---

# CRITICAL GUARDRAILS

- Every title must be grounded in evidence from the company website, reviews, case studies, or known buyer patterns for this category.
- Do **not** guess or hallucinate titles.
- Exclude roles that would reasonably not care about or buy this product.
- Do not include generic functional labels (e.g., "Information Security").
- Quantity target: 30–60 titles. More is fine if grounded. Fewer is fine if narrow. Never pad.

---

# OUTPUT FORMAT

```json
{{
  "companyName": "...",
  "domain": "...",
  "inferredProduct": "One sentence describing what the company sells and to whom, based on your research.",
  "buyerPersona": "2–3 sentences describing the buying committee — who champions it, who evaluates it, who signs off.",
  "titles": [
    {{
      "title": "...",
      "buyerRole": "champion | evaluator | decision_maker",
      "reasoning": "One sentence grounding this title in research evidence."
    }}
  ]
}}"""


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("parallel-secret")],
    timeout=1800,  # 30 minutes max for deep research (Ultra can take up to 25 min)
)
@modal.fastapi_endpoint(method="POST", label="icp-titles")
def parallel_icp_job_titles(request: ParallelICPJobTitlesRequest) -> dict:
    """
    Generate ICP job titles using Parallel.ai Deep Research.
    """
    from parallel import Parallel

    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        raise ValueError("PARALLEL_API_KEY not found in environment")

    client = Parallel(api_key=api_key)

    # Build the prompt
    input_data = PROMPT_TEMPLATE.format(
        company_name=request.company_name,
        domain=request.domain,
        company_description=request.company_description,
    )

    try:
        # Create the task run
        task_run = client.task_run.create(
            input=input_data,
            processor="ultra"
        )

        # Wait for completion (can take up to 15 mins)
        run_result = client.task_run.result(task_run.run_id, api_timeout=1800)

        return {
            "success": True,
            "runId": task_run.run_id,
            "companyName": request.company_name,
            "domain": request.domain,
            "output": run_result.output,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "companyName": request.company_name,
            "domain": request.domain,
        }
