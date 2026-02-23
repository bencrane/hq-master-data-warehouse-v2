"""
Scrape G2 Reviews Page with Gemini

Takes a G2 reviews URL, fetches the page, and uses Gemini to extract
structured insights (ratings, complaints, praise points, quotes).
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class G2ReviewsScrapeRequest(BaseModel):
    """Request model for G2 reviews scrape."""
    g2_url: str
    domain: Optional[str] = None


GEMINI_PROMPT = """You are extracting structured review insights from a G2 product reviews page.

Extract the following from the page content below:

1. **overallRating**: The overall star rating as a numeric value (e.g., 4.5). If format is "4.5/5", capture 4.5.

2. **totalReviewsCount**: Total number of reviews as an integer (e.g., 237). Use the primary aggregate count near the rating widget.

3. **commonComplaints**: Top 3-5 recurring negative themes across reviews. Summarize each in 1 short sentence. Only use what's visible in the content.

4. **commonPraisePoints**: Top 3-5 recurring positive themes across reviews. Summarize each in 1 short sentence. Only use what's visible in the content.

5. **negativeQuotes**: 2-5 short, representative direct quotes highlighting frustrations. Use exact wording - do not paraphrase.

Rules:
- If multiple ratings appear, use the main product rating near the title/overview
- Normalize counts with separators (e.g., "1,234" → 1234)
- Themes should recur across multiple reviews
- Quotes must be verbatim from the page
- Only use information from this page content, not external knowledge

Return valid JSON only, no markdown code blocks:
{
  "overallRating": 4.5,
  "totalReviewsCount": 237,
  "commonComplaints": [
    "Theme 1 summary",
    "Theme 2 summary"
  ],
  "commonPraisePoints": [
    "Theme 1 summary",
    "Theme 2 summary"
  ],
  "negativeQuotes": [
    "Exact quote from review",
    "Another exact quote"
  ],
  "error": null
}

If the page content is empty, inaccessible, or has no review content, return:
{
  "overallRating": null,
  "totalReviewsCount": null,
  "commonComplaints": [],
  "commonPraisePoints": [],
  "negativeQuotes": [],
  "error": "Brief explanation of the issue"
}

PAGE CONTENT:
"""


@app.function(
    image=image,
    timeout=120,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def scrape_g2_reviews(request: G2ReviewsScrapeRequest) -> dict:
    """
    Scrape a G2 reviews page and extract structured insights using Gemini.
    """
    import requests
    import json
    import google.generativeai as genai
    from bs4 import BeautifulSoup

    g2_url = request.g2_url.strip()
    domain = request.domain

    if not g2_url:
        return {"success": False, "error": "No g2_url provided"}

    # Ensure URL points to reviews page
    if "/reviews" not in g2_url:
        # Try to construct reviews URL
        if "/products/" in g2_url:
            base = g2_url.split("/products/")[1].split("/")[0]
            g2_url = f"https://www.g2.com/products/{base}/reviews"

    try:
        # Fetch the page
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(g2_url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse HTML and extract text
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Get text content
        page_text = soup.get_text(separator="\n", strip=True)

        # Truncate if too long (Gemini context limit)
        max_chars = 100000
        if len(page_text) > max_chars:
            page_text = page_text[:max_chars]

        if len(page_text) < 500:
            return {
                "success": False,
                "g2_url": g2_url,
                "error": "Page content too short - may be blocked or empty",
                "overallRating": None,
                "totalReviewsCount": None,
                "commonComplaints": [],
                "commonPraisePoints": [],
                "negativeQuotes": []
            }

        # Call Gemini
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash")

        full_prompt = GEMINI_PROMPT + page_text
        gemini_response = model.generate_content(full_prompt)

        # Parse response
        response_text = gemini_response.text.strip()

        # Clean up response if wrapped in markdown
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        result = json.loads(response_text)

        # Add metadata
        result["success"] = True
        result["g2_url"] = g2_url
        result["domain"] = domain

        # Token usage
        if hasattr(gemini_response, "usage_metadata"):
            result["input_tokens"] = gemini_response.usage_metadata.prompt_token_count
            result["output_tokens"] = gemini_response.usage_metadata.candidates_token_count

        return result

    except requests.RequestException as e:
        return {
            "success": False,
            "g2_url": g2_url,
            "domain": domain,
            "error": f"Failed to fetch page: {str(e)}",
            "overallRating": None,
            "totalReviewsCount": None,
            "commonComplaints": [],
            "commonPraisePoints": [],
            "negativeQuotes": []
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "g2_url": g2_url,
            "domain": domain,
            "error": f"Failed to parse Gemini response as JSON: {str(e)}",
            "raw_response": response_text[:1000] if 'response_text' in locals() else None
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "g2_url": g2_url,
            "domain": domain,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
