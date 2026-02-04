"""
SEC Filing Analysis Endpoints

Sends SEC filing URLs to Gemini for analysis.
Prompts are pulled from prompts/sec_filings.py for easy iteration.

Endpoints:
- analyze_sec_10k: Analyze a 10-K annual report
- analyze_sec_10q: Analyze a 10-Q quarterly report
"""

import os
import modal
import httpx
from config import app, image


def fetch_filing_content(url: str) -> str:
    """Fetch the HTML content of an SEC filing."""
    headers = {"User-Agent": "HQ Master Data ben@revenueinfra.com"}
    response = httpx.get(url, headers=headers, timeout=120.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def call_gemini(prompt: str, content: str) -> str:
    """Send content to Gemini for analysis."""
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    full_prompt = f"{prompt}\n\n---\n\nFILING CONTENT:\n\n{content[:100000]}"  # Truncate if huge

    response = model.generate_content(full_prompt)
    return response.text


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("gemini-secret")],
    timeout=300,
)
@modal.fastapi_endpoint(method="POST")
def analyze_sec_10k(request: dict) -> dict:
    """
    Analyze a 10-K filing URL with Gemini.

    Expects:
    {
        "document_url": "https://www.sec.gov/Archives/...",
        "domain": "klaviyo.com",  # optional, for context
        "company_name": "Klaviyo, Inc."  # optional
    }
    """
    from prompts.sec_filings import PROMPT_10K

    try:
        document_url = request.get("document_url")
        domain = request.get("domain", "")
        company_name = request.get("company_name", "")

        if not document_url:
            return {"success": False, "error": "No document_url provided"}

        # Fetch the filing
        content = fetch_filing_content(document_url)

        # Add context to prompt if available
        prompt = PROMPT_10K
        if company_name:
            prompt = f"Company: {company_name}\n\n{prompt}"

        # Analyze with Gemini
        analysis = call_gemini(prompt, content)

        return {
            "success": True,
            "filing_type": "10-K",
            "document_url": document_url,
            "domain": domain,
            "company_name": company_name,
            "analysis": analysis,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "document_url": request.get("document_url", "unknown"),
        }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("gemini-secret")],
    timeout=300,
)
@modal.fastapi_endpoint(method="POST")
def analyze_sec_10q(request: dict) -> dict:
    """
    Analyze a 10-Q filing URL with Gemini.

    Expects:
    {
        "document_url": "https://www.sec.gov/Archives/...",
        "domain": "klaviyo.com",  # optional
        "company_name": "Klaviyo, Inc."  # optional
    }
    """
    from prompts.sec_filings import PROMPT_10Q

    try:
        document_url = request.get("document_url")
        domain = request.get("domain", "")
        company_name = request.get("company_name", "")

        if not document_url:
            return {"success": False, "error": "No document_url provided"}

        # Fetch the filing
        content = fetch_filing_content(document_url)

        # Add context to prompt if available
        prompt = PROMPT_10Q
        if company_name:
            prompt = f"Company: {company_name}\n\n{prompt}"

        # Analyze with Gemini
        analysis = call_gemini(prompt, content)

        return {
            "success": True,
            "filing_type": "10-Q",
            "document_url": document_url,
            "domain": domain,
            "company_name": company_name,
            "analysis": analysis,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "document_url": request.get("document_url", "unknown"),
        }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("gemini-secret")],
    timeout=300,
)
@modal.fastapi_endpoint(method="POST")
def analyze_sec_8k_executive(request: dict) -> dict:
    """
    Analyze an 8-K executive changes filing URL with Gemini.

    Expects:
    {
        "document_url": "https://www.sec.gov/Archives/...",
        "domain": "klaviyo.com",  # optional
        "company_name": "Klaviyo, Inc."  # optional
    }
    """
    from prompts.sec_filings import PROMPT_8K_EXECUTIVE

    try:
        document_url = request.get("document_url")
        domain = request.get("domain", "")
        company_name = request.get("company_name", "")

        if not document_url:
            return {"success": False, "error": "No document_url provided"}

        content = fetch_filing_content(document_url)

        prompt = PROMPT_8K_EXECUTIVE
        if company_name:
            prompt = f"Company: {company_name}\n\n{prompt}"

        analysis = call_gemini(prompt, content)

        return {
            "success": True,
            "filing_type": "8-K-executive",
            "document_url": document_url,
            "domain": domain,
            "company_name": company_name,
            "analysis": analysis,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "document_url": request.get("document_url", "unknown"),
        }
