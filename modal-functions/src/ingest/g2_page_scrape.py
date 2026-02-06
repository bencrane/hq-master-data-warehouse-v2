"""
Ingest G2 Page Scrape from Clay-Zenrows

Receives the Zenrows scrape of a G2 product page (alternatives/competitors page)
and extracts structured data about the company and its alternatives.

Expects:
{
  "domain": "example.com",
  "g2_url": "https://www.g2.com/products/example/competitors/alternatives",
  "scrape_data": {
    "links": [...],
    "title": "...",
    "bodyText": "...",
    "description": "...",
    "socialLinks": {...}
  }
}

Returns:
{
  "success": true,
  "domain": "example.com",
  "g2_url": "https://www.g2.com/products/example",
  "categories": ["Generative AI Infrastructure"],
  "alternatives_count": 9
}
"""

import os
import re
import modal
from config import app, image


def extract_g2_product_slug(g2_url: str) -> str:
    """Extract the product slug from a G2 URL."""
    if not g2_url:
        return ""
    match = re.search(r'g2\.com/products/([^/]+)', g2_url)
    return match.group(1) if match else ""


def extract_categories(links: list) -> list:
    """Extract G2 categories from the links array."""
    categories = set()
    for link in links:
        href = link.get("href", "")
        text = link.get("text", "")
        if "/categories/" in href and text:
            clean_text = text.strip()
            if clean_text and clean_text not in ["All Categories", "Top Categories", "Back"]:
                categories.add(clean_text)
    return list(categories)


def extract_alternatives(links: list, body_text: str) -> list:
    """Extract alternative products from the links array."""
    alternatives = []
    seen_products = set()

    # Pattern to match G2 product URLs
    product_pattern = re.compile(r'g2\.com/products/([^/]+)/reviews')

    for link in links:
        href = link.get("href", "")
        text = link.get("text", "").strip()

        match = product_pattern.search(href)
        if match and text and text not in seen_products:
            product_slug = match.group(1)

            # Skip if text is empty, a rating, or navigation text
            if not text or text.startswith("4.") or text.startswith("5.") or "Show More" in text:
                continue

            # Skip generic navigation texts
            skip_texts = ["Home", "Back", "", "Show More", "Show Less", "Create a Free Account"]
            if text in skip_texts:
                continue

            seen_products.add(text)

            # Try to extract rating from body text
            rating = None
            review_count = None
            rating_pattern = rf'{re.escape(text)}.*?(\d\.\d)/5\((\d+)\)'
            rating_match = re.search(rating_pattern, body_text)
            if rating_match:
                rating = float(rating_match.group(1))
                review_count = int(rating_match.group(2))

            alternatives.append({
                "name": text,
                "g2_url": f"https://www.g2.com/products/{product_slug}",
                "rating": rating,
                "review_count": review_count
            })

    return alternatives


def normalize_domain(domain: str) -> str:
    """Normalize domain by removing protocol, www, and paths."""
    if not domain:
        return ""
    domain = re.sub(r'^https?://', '', domain)
    domain = domain.split('/')[0]
    domain = re.sub(r'^www\.', '', domain)
    return domain.lower().strip()


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def ingest_g2_page_scrape_zenrows(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = normalize_domain(request.get("domain", ""))
        g2_url = request.get("g2_url", "").strip()
        scrape_data = request.get("scrape_data", {})

        if not domain:
            return {"success": False, "error": "No domain provided"}

        if not g2_url:
            return {"success": False, "error": "No g2_url provided"}

        if not scrape_data:
            return {"success": False, "error": "No scrape_data provided"}

        # Extract data from scrape
        links = scrape_data.get("links", [])
        body_text = scrape_data.get("bodyText", "")
        title = scrape_data.get("title", "")
        description = scrape_data.get("description", "")

        # Derive clean G2 product URL (without /competitors/alternatives)
        g2_product_slug = extract_g2_product_slug(g2_url)
        clean_g2_url = f"https://www.g2.com/products/{g2_product_slug}" if g2_product_slug else g2_url

        # Extract structured data
        categories = extract_categories(links)
        alternatives = extract_alternatives(links, body_text)

        # 1. Store raw payload
        raw_result = supabase.table("clay_zenrows_g2_scrape_payloads").insert({
            "domain": domain,
            "g2_url": g2_url,
            "payload": scrape_data
        }, returning="representation").execute()

        raw_id = raw_result.data[0]["id"] if raw_result.data else None

        # 2. Store extracted data
        supabase.table("g2_page_scrape").upsert({
            "domain": domain,
            "g2_url": clean_g2_url,
            "g2_product_slug": g2_product_slug,
            "page_title": title[:500] if title else None,
            "page_description": description[:1000] if description else None,
            "categories": categories,
            "alternatives": alternatives,
            "raw_payload_id": raw_id
        }, on_conflict="domain").execute()

        # 3. Update core.ancillary_urls with g2_page_url
        supabase.table("ancillary_urls").upsert({
            "domain": domain,
            "g2_page_url": clean_g2_url
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "g2_url": clean_g2_url,
            "g2_product_slug": g2_product_slug,
            "categories": categories,
            "alternatives_count": len(alternatives)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
