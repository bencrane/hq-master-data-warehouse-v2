"""
Meta Ads (Adyntel) Ingest Endpoint

Expects:
{
  "domain": "example.com",
  "meta_ads_payload": {
    "page_id": "1952488691430943",
    "results": [...],
    "platform": ["facebook", "instagram"],
    "number_of_ads": 0,
    "continuation_token": "...",
    ...
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
def ingest_meta_ads(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("meta_ads_payload", {})
        clay_table_url = request.get("clay_table_url")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # Extract data from payload
        results = payload.get("results", [])
        page_id = payload.get("page_id")
        platforms = payload.get("platform", [])
        number_of_ads = payload.get("number_of_ads", 0)

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("meta_ads_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
                "clay_table_url": clay_table_url,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Extract each ad from results
        ads_extracted = 0
        for ad in results:
            if not isinstance(ad, dict):
                continue

            ad_id = ad.get("id") or ad.get("ad_id")
            platform = ad.get("platform")
            start_date = ad.get("start_date") or ad.get("ad_delivery_start_time")
            end_date = ad.get("end_date") or ad.get("ad_delivery_stop_time")
            status = ad.get("status") or ad.get("ad_status")
            page_name = ad.get("page_name")

            # Creative content
            ad_creative = ad.get("ad_creative", {}) or {}
            ad_creative_body = ad_creative.get("body") or ad.get("body") or ad.get("ad_creative_body")
            ad_creative_link_title = ad_creative.get("link_title") or ad.get("link_title")
            ad_creative_link_description = ad_creative.get("link_description") or ad.get("link_description")

            # Media
            landing_page_url = ad.get("landing_page_url") or ad.get("link_url")
            image_url = ad.get("image_url") or ad_creative.get("image_url")
            video_url = ad.get("video_url") or ad_creative.get("video_url")

            supabase.schema("extracted").from_("company_meta_ads").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "ad_id": ad_id,
                "platform": platform,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "page_name": page_name,
                "ad_creative_body": ad_creative_body,
                "ad_creative_link_title": ad_creative_link_title,
                "ad_creative_link_description": ad_creative_link_description,
                "landing_page_url": landing_page_url,
                "image_url": image_url,
                "video_url": video_url,
            }).execute()

            ads_extracted += 1

        # 3. Upsert core summary
        is_running_ads = number_of_ads > 0 or len(results) > 0
        ad_count = number_of_ads if number_of_ads > 0 else len(results)

        supabase.schema("core").from_("company_meta_ads").upsert({
            "domain": domain,
            "is_running_ads": is_running_ads,
            "ad_count": ad_count,
            "page_id": page_id,
            "platforms": platforms,
            "last_checked_at": "now()",
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "ads_extracted": ads_extracted,
            "total_ads": ad_count,
            "is_running_ads": is_running_ads,
            "platforms": platforms,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
