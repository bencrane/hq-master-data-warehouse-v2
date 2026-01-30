"""
Meta Description Fetcher

Fetches a website and extracts the meta description tag.
"""

import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class MetaDescriptionRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    timeout=30,
)
@modal.fastapi_endpoint(method="POST")
def fetch_meta_description(request: MetaDescriptionRequest) -> dict:
    """
    Fetch website and extract meta description.
    """
    import requests
    from bs4 import BeautifulSoup

    try:
        # Try https first, fall back to http
        url = f"https://{request.domain}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        except:
            # Try http if https fails
            url = f"http://{request.domain}"
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "domain": request.domain,
            }

        soup = BeautifulSoup(response.text, "html.parser")

        # Try different meta description variations
        meta_description = None

        # Standard meta description
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_description = meta_tag["content"].strip()

        # OpenGraph description as fallback
        if not meta_description:
            og_tag = soup.find("meta", attrs={"property": "og:description"})
            if og_tag and og_tag.get("content"):
                meta_description = og_tag["content"].strip()

        # Twitter description as fallback
        if not meta_description:
            twitter_tag = soup.find("meta", attrs={"name": "twitter:description"})
            if twitter_tag and twitter_tag.get("content"):
                meta_description = twitter_tag["content"].strip()

        # Get title as bonus
        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()

        return {
            "success": True,
            "domain": request.domain,
            "meta_description": meta_description,
            "title": title,
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "timeout", "domain": request.domain}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "connection_error", "domain": request.domain}
    except Exception as e:
        return {"success": False, "error": str(e), "domain": request.domain}
