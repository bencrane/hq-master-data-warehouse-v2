"""
Compare Job Titles Endpoint

Compares a candidate job title against a list of job titles to determine
if they represent the same role or different roles.
Uses Gemini 2.5 Flash.
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import List, Optional
from config import app, image


class CompareJobTitlesRequest(BaseModel):
    candidate_title: str
    job_title_list: List[str]


PROMPT_TEMPLATE = """#CONTEXT#

You are an expert analyst specializing in job title normalization and equivalence assessment. You will compare a single candidate job title to each job title in a provided list and determine whether they represent, by and large, the same role (not a promotion, demotion, or adjacent function). Treat differences in wording as potentially cosmetic unless they imply materially different scope, level, function, or domain.



#OBJECTIVE#

Compare the candidate title against each title in the job title list and, for each list title, output whether it is the SAME JOB or a DIFFERENT JOB, along with one concise sentence of reasoning.

#INSTRUCTIONS#

1. Inputs:

- candidateTitle: {candidate_title}

- jobTitleList: {job_title_list}

2. For each job title in jobTitleList, compare it against candidateTitle focusing on:

- Core function (e.g., marketing, sales, software engineering, data science, security).

- Seniority/level indicators (e.g., intern, junior, senior, lead, principal, head, director, vp, c-level).

- Scope indicators (e.g., regional/global, individual contributor vs manager/leadership, strategic vs hands-on).

- Domain specialization qualifiers (e.g., frontend vs backend, data platform vs ml, it security vs application security).

- Modifiers that are usually cosmetic (e.g., "I", "II", "III" within same band; "software engineer" vs "software developer").

3. SAME JOB criteria (all must hold):

- Core function aligns and day-to-day responsibilities substantially overlap.

- No material change in seniority/scope (e.g., Manager/Lead/Head imply leadership vs IC; Director/VP/CxO are leadership tiers and not the same as IC titles; Senior vs Staff/Principal typically differ).

- No material change in specialization that alters responsibilities (e.g., Backend Engineer vs Data Engineer is different; Product Marketing Manager vs Marketing Manager can be different unless clearly generalist).

4. DIFFERENT JOB criteria (any can trigger):

- Change in function, seniority, scope, or specialization that would alter core responsibilities.

5. Critical guardrails:

- A shared functional domain is NOT enough to warrant SAME JOB. The titles must imply the same specific role — same core daily activities, same type of ownership, same level of individual vs. team responsibility.

- If one title is a broad category or functional label (e.g., "Technical Sales", "Information Security", "Marketing") and the other is a specific position (e.g., "Account Executive", "Security Engineer", "Content Marketing Manager"), that is DIFFERENT JOB. A category is not a role.

- Two titles can live in the same department and still be DIFFERENT JOB if their day-to-day work, deliverables, or accountability structures differ materially.

- Matching seniority tier alone is NOT enough. Titles like "VP", "Head of", "Director", "Manager", "Lead", "Chief" are seniority/scope indicators — they are NOT functional descriptors. Two titles can both be VP-level, Director-level, Head-level, or Manager-level and still be DIFFERENT JOB if functional domain differs. "VP of Sales" and "VP of Engineering" are both VP — they are DIFFERENT JOB. "Director of Marketing" and "Director of Security" are both Directors — they are DIFFERENT JOB. "Head of IT" and "Head of Customer Success" are both Heads — they are DIFFERENT JOB. The seniority label is just a rank indicator. It must be paired with an overlapping function to qualify as SAME JOB. Never match on rank alone.

Example candidateTitle: "Vice President of Security and Compliance"
Example jobTitleList item: "VP Global Resilience and ERM"
Expected output item:
- jobTitle: VP Global Resilience and ERM
- verdict: DIFFERENT JOB
- reasoning: Both are VP-level, but "Security and Compliance" and "Global Resilience and ERM" are distinct functional domains with different day-to-day responsibilities and accountability structures. Shared seniority tier does not make them the same job.

6. Ambiguity handling:

- Default to industry-standard interpretations (e.g., Program Manager vs Project Manager often differ; DevOps Engineer vs SRE may overlap but are not always the same).

- When uncertain, prefer DIFFERENT JOB unless equivalence is broadly recognized.

7. Output formatting per job title (exactly these fields, camelCase keys):

- jobTitle: the job title from the list (verbatim)

- verdict: "SAME JOB" or "DIFFERENT JOB"

- reasoning: one concise sentence justifying the verdict

- If verdict is "SAME JOB", also include jobTitleSameAs: repeat the list job title that is deemed the same as the candidate title

8. Constraints:

- Keep reasoning concise and specific to function, level, scope, and specialization differences or alignments.

#EXAMPLES#

Example candidateTitle: "Senior Software Engineer"
Example jobTitleList item: "Software Engineer"
Expected output item:
- jobTitle: Software Engineer
- verdict: DIFFERENT JOB
- reasoning: "Senior" indicates higher ownership and scope than baseline "Software Engineer", implying a different level.

Example candidateTitle: "Head of Security"
Example jobTitleList item: "Security Lead"
Expected output item:
- jobTitle: Security Lead
- verdict: SAME JOB
- reasoning: Both denote leadership over the security function with comparable scope depending on naming conventions.
- jobTitleSameAs: Security Lead

In your output, you must output "anyMatches" where, if every VERDICT = DIFFERENT JOB, then anyMatches = false.
If VERDICT = SAME JOB at least once, then anyMatches = true.

- A title that combines an IC role with a team lead modifier (e.g., "Account Executive and Team Lead", "Software Engineer and Team Lead") is NOT the same as a dedicated management title (e.g., "Account Management Manager", "Engineering Manager"). The former is an individual contributor who also leads a small team; the latter is a full-time people manager whose primary responsibility is managing others. These are DIFFERENT JOB.

Example candidateTitle: "Account Management Manager"
Example jobTitleList item: "Account Executive and Team Lead"
Expected output item:
- jobTitle: Account Executive and Team Lead
- verdict: DIFFERENT JOB
- reasoning: "Account Executive and Team Lead" is an IC with added team oversight, whereas "Account Management Manager" is a dedicated people management role — different primary responsibility.

#OUTPUT FORMAT#

Return a JSON object with:
{{
  "candidateTitle": "{candidate_title}",
  "anyMatches": true/false,
  "comparisons": [
    {{
      "jobTitle": "...",
      "verdict": "SAME JOB" or "DIFFERENT JOB",
      "reasoning": "...",
      "jobTitleSameAs": "..." // only if verdict is SAME JOB
    }}
  ],
  "inputTokens": ...,
  "outputTokens": ...
}}

Return only valid JSON."""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini-secret"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def compare_job_titles(request: CompareJobTitlesRequest) -> dict:
    """
    Compare a candidate job title against a list of job titles.
    Uses Gemini 2.5 Flash.
    """
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = PROMPT_TEMPLATE.format(
        candidate_title=request.candidate_title,
        job_title_list=json.dumps(request.job_title_list),
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )

        result = json.loads(response.text)

        # Handle if Gemini returns a list
        if isinstance(result, list):
            result = result[0] if result else {}

        # Get token counts
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        # Gemini 2.5 Flash pricing
        cost_usd = (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)

        return {
            "success": True,
            "candidateTitle": request.candidate_title,
            "anyMatches": result.get("anyMatches", False),
            "comparisons": result.get("comparisons", []),
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "costUsd": round(cost_usd, 6),
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse Gemini response: {e}",
            "candidateTitle": request.candidate_title,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "candidateTitle": request.candidate_title,
        }
