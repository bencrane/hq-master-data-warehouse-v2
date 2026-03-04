"""
Meta Ads (Clay Native Adyntel) Ingest Endpoint

For Clay's native Adyntel enrichment which has a different payload structure.

Expects:
{
  "domain": "example.com",
  "meta_ads_payload": {
    "page_id": "107585658730958",
    "results": [
      {
        "ad_archive_id": "1043443784505779",
        "start_date": 1762156800,
        "end_date": 1772524800,
        "is_active": true,
        "page_name": "Grüns",
        "publisher_platform": ["FACEBOOK", "INSTAGRAM"],
        "snapshot": {
          "body": {"text": "..."},
          "link_url": "...",
          ...
        }
      }
    ]
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
def ingest_meta_ads_clay(request: dict) -> dict:
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

            # Clay/Adyntel specific field mappings
            ad_id = ad.get("ad_archive_id") or ad.get("collation_id")

            # publisher_platform is an array like ["FACEBOOK", "INSTAGRAM"]
            publisher_platforms = ad.get("publisher_platform", [])
            platform = ",".join(publisher_platforms) if publisher_platforms else None

            # Timestamps are unix epoch
            start_date = ad.get("start_date")
            end_date = ad.get("end_date")

            # is_active is boolean
            is_active = ad.get("is_active")
            status = "active" if is_active else "inactive"

            page_name = ad.get("page_name")

            # Snapshot contains the creative content
            snapshot = ad.get("snapshot", {}) or {}

            # Body text
            body_obj = snapshot.get("body", {}) or {}
            ad_creative_body = body_obj.get("text") if isinstance(body_obj, dict) else None

            # Title and description
            ad_creative_link_title = snapshot.get("title")
            ad_creative_link_description = snapshot.get("link_description")

            # Landing page
            landing_page_url = snapshot.get("link_url")

            # Images - try to get from snapshot
            images = snapshot.get("images", [])
            image_url = images[0] if images else None

            # If no images array, try cards
            if not image_url:
                cards = snapshot.get("cards", [])
                if cards and isinstance(cards[0], dict):
                    image_url = cards[0].get("resized_image_url") or cards[0].get("original_image_url")

            # Videos
            videos = snapshot.get("videos", [])
            video_url = videos[0] if videos else None

            supabase.schema("extracted").from_("company_meta_ads").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "ad_id": ad_id,
                "platform": platform,
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
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
        is_running_ads = len(results) > 0
        ad_count = len(results)

        supabase.schema("core").from_("company_meta_ads").upsert({
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
