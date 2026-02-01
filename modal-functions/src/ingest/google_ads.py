"""
Google Ads (Adyntel) Ingest Endpoint

Expects:
{
  "domain": "forethought.ai",
  "google_ads_payload": {
    "ads": [...],
    "country_code": "anywhere",
    "total_ad_count": 200,
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
def ingest_google_ads(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("google_ads_payload", {})
        clay_table_url = request.get("clay_table_url")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # Extract data from payload
        ads = payload.get("ads", [])
        total_ad_count = payload.get("total_ad_count", 0)

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("google_ads_payloads")
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
        advertiser_id = None

        for ad in ads:
            if not isinstance(ad, dict):
                continue

            creative_id = ad.get("creative_id")
            format_type = ad.get("format")
            start_date = ad.get("start")
            last_seen = ad.get("last_seen")
            ad_advertiser_id = ad.get("advertiser_id")
            advertiser_name = ad.get("advertiser_name")
            original_url = ad.get("original_url")

            # Capture first advertiser_id for core summary
            if ad_advertiser_id and not advertiser_id:
                advertiser_id = ad_advertiser_id

            # Get first variant info
            variants = ad.get("variants", [])
            variant_content = None
            variant_width = None
            variant_height = None
            if variants and len(variants) > 0:
                first_variant = variants[0]
                variant_content = first_variant.get("content")
                variant_width = first_variant.get("width")
                variant_height = first_variant.get("height")

            supabase.schema("extracted").from_("company_google_ads").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "creative_id": creative_id,
                "format": format_type,
                "start_date": start_date,
                "last_seen": last_seen,
                "advertiser_id": ad_advertiser_id,
                "advertiser_name": advertiser_name,
                "original_url": original_url,
                "variant_content": variant_content,
                "variant_width": variant_width,
                "variant_height": variant_height,
            }).execute()

            ads_extracted += 1

        # 3. Upsert core summary
        is_running_ads = total_ad_count > 0 or len(ads) > 0
        ad_count = total_ad_count if total_ad_count > 0 else len(ads)

        supabase.schema("core").from_("company_google_ads").upsert({
            "domain": domain,
            "is_running_ads": is_running_ads,
            "ad_count": ad_count,
            "advertiser_id": advertiser_id,
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
