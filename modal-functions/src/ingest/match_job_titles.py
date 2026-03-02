"""
Match Job Titles — GPT-4.1 Nano Classification

Takes a candidate job title and a list of ICP job titles, classifies each as
SAME JOB or DIFFERENT JOB via GPT-4.1 nano. Returns verdicts + token usage + cost.

Expects:
{
  "candidate_title": "VP of Engineering",
  "job_titles": ["VP Engineering", "Director of Engineering", "CTO", "Head of Engineering"]
}

Returns:
{
  "success": true,
  "candidate_title": "VP of Engineering",
  "results": [
    {"jobTitle": "VP Engineering", "verdict": "SAME JOB", "reasoning": "..."},
    {"jobTitle": "Director of Engineering", "verdict": "DIFFERENT JOB", "reasoning": "..."}
  ],
  "has_match": true,
  "match_count": 1,
  "total_compared": 4,
  "usage": {
    "input_tokens": 892,
    "output_tokens": 234,
    "total_tokens": 1126,
    "cost_usd": 0.000183
  }
}
"""

import os
import json
import modal
from config import app, image


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


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("openai-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def match_job_titles(request: dict) -> dict:
    import openai

    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    try:
        candidate_title = request.get("candidate_title", "").strip()
        job_titles = request.get("job_titles", [])

        if not candidate_title:
            return {"success": False, "error": "candidate_title is required"}
        if not job_titles or not isinstance(job_titles, list):
            return {"success": False, "error": "job_titles must be a non-empty list"}

        # Clean up job titles
        job_titles = [str(t).strip() for t in job_titles if str(t).strip()]
        if not job_titles:
            return {"success": False, "error": "job_titles must contain at least one non-empty string"}

        user_message = f"CANDIDATE TITLE: {candidate_title}\nJOB TITLE LIST: {json.dumps(job_titles)}"

        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            max_tokens=4096,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )

        response_text = response.choices[0].message.content.strip()
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # Cost: GPT-4.1 nano = $0.10/MTok input, $0.40/MTok output
        cost_usd = round(
            (input_tokens / 1_000_000 * 0.10) + (output_tokens / 1_000_000 * 0.40),
            6,
        )

        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        try:
            results = json.loads(response_text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Model returned unparseable JSON",
                "raw_response": response_text[:2000],
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "cost_usd": cost_usd,
                },
            }

        # Compute has_match and match_count in code
        has_match = any(r.get("verdict") == "SAME JOB" for r in results)
        match_count = sum(1 for r in results if r.get("verdict") == "SAME JOB")

        return {
            "success": True,
            "candidate_title": candidate_title,
            "results": results,
            "has_match": has_match,
            "match_count": match_count,
            "total_compared": len(job_titles),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": cost_usd,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "candidate_title": request.get("candidate_title", "unknown"),
        }
