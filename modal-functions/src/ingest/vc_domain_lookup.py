"""
VC Domain Lookup Endpoint

Uses Gemini API to find the official domain for a VC firm.
"""

import os
import modal
from pydantic import BaseModel

from config import app, image


class VCDomainLookupRequest(BaseModel):
    vc_name: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("gemini-secret")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_vc_domain(request: VCDomainLookupRequest) -> dict:
    """
    Look up the official domain for a VC firm using Gemini.
    """
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"success": False, "error": "GEMINI_API_KEY not configured"}

    genai.configure(api_key=api_key)

    prompt = f"""#CONTEXT#

You are an AI-powered web scraper specialized in finding the official website domain for venture capital firms, investors, or investment firms using a single input string from a table column. You must only use the provided input value and return a single verified domain.

#OBJECTIVE#

Find and return the official website domain for the entity specified in <vc_name>.

#INPUT#

<vc_name> = "{request.vc_name}"

#INSTRUCTIONS#

1. Interpret the input:
   - Treat <vc_name> as the firm or investor name query string. Do not modify or expand it beyond standard search operators.

2. Searching strategy:
   - Run a web search for: "<vc_name>" official site, homepage, website, domain.
   - Prioritize top results from authoritative sources: the firm's own site, Crunchbase, PitchBook profiles, reputable news, or Wikipedia pages that link to the official site.
   - Avoid social profiles (LinkedIn/Twitter) as final answers unless they are the only official web presence and clearly state the official website is absent.

3. Verification criteria for the correct domain:
   - The site content clearly matches the firm or investor name from <vc_name> (branding, about page, copyright footer).
   - The site describes venture investing activities consistent with an investor/VC/investment firm.
   - Cross-check at least one secondary reputable source (e.g., Crunchbase/Wikipedia/news) that links to the same domain.
   - Prefer the primary corporate domain over subdomains, link shorteners, or third-party pages.

4. Disambiguation rules:
   - If multiple firms share similar names, use contextual cues on the site (geography, portfolio, team) to ensure it is a VC/investment firm.
   - If still ambiguous after checks, choose the most authoritative match with explicit venture/investing language. If ambiguity persists, return "notFound".

5. Domain formatting rules:
   - Output only the root domain in lowercase (e.g., a16z.com, sequoiacap.com).
   - Do not include protocol (http/https), paths, query strings, or trailing slashes.
   - If the official site only exists as a subdomain (rare), return that subdomain (e.g., ventures.example.com) if it is explicitly the primary site.

6. Error handling:
   - If no reliable official website can be identified after reasonable searching and cross-checking, return "notFound".
   - Do not infer or guess domains. Do not fabricate outputs.

#OUTPUT#

Return ONLY the domain (e.g., a16z.com) or "notFound". No other text."""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        domain = response.text.strip().lower()

        # Clean up any accidental formatting
        domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")

        return {
            "success": True,
            "vc_name": request.vc_name,
            "domain": domain if domain != "notfound" else None,
            "found": domain != "notfound",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
