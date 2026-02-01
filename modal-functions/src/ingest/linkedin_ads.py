"""
LinkedIn Ads (Adyntel) Ingest Endpoint

Expects:
{
  "domain": "forethought.ai",
  "linkedin_ads_payload": {
    "ads": [...],
    "page_id": "18555572",
    "total_ads": 277,
    "is_last_page": false,
    "continuation_token": "..."
  },
  "clay_table_url": "optional"
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_linkedin_ads(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("linkedin_ads_payload", {})
        clay_table_url = request.get("clay_table_url")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # Extract data from payload
        ads = payload.get("ads", [])
        page_id = payload.get("page_id")
        total_ads = payload.get("total_ads", 0)

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("linkedin_ads_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
                "clay_table_url": clay_table_url,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Extract each ad
        ads_extracted = 0
        for ad in ads:
            if not isinstance(ad, dict):
                continue

            ad_id = ad.get("ad_id")
            ad_type = ad.get("type")
            creative_type = ad.get("creative_type")

            headline = ad.get("headline", {}) or {}
            headline_title = headline.get("title")
            headline_description = headline.get("description")

            commentary = ad.get("commentary", {}) or {}
            commentary_text = commentary.get("text")

            image_data = ad.get("image", {}) or {}
            image_url = image_data.get("url")
            image_alt_text = image_data.get("alt_text")

            advertiser = ad.get("advertiser", {}) or {}
            advertiser_name = advertiser.get("name")

            view_details_link = ad.get("view_details_link")

            supabase.schema("extracted").from_("company_linkedin_ads").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "ad_id": ad_id,
                "ad_type": ad_type,
                "creative_type": creative_type,
                "headline_title": headline_title,
                "headline_description": headline_description,
                "commentary_text": commentary_text,
                "image_url": image_url,
                "image_alt_text": image_alt_text,
                "advertiser_name": advertiser_name,
                "view_details_link": view_details_link,
            }).execute()

            ads_extracted += 1

        # 3. Upsert core summary
        is_running_ads = total_ads > 0 or len(ads) > 0
        ad_count = total_ads if total_ads > 0 else len(ads)

        supabase.schema("core").from_("company_linkedin_ads").upsert({
            "domain": domain,
            "is_running_ads": is_running_ads,
            "ad_count": ad_count,
            "page_id": page_id,
            "last_checked_at": "now()",
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "ads_extracted": ads_extracted,
            "total_ads": ad_count,
            "is_running_ads": is_running_ads,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
