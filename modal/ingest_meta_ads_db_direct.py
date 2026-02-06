"""
Modal function: ingest-meta-ads-db-direct

Ingests Meta (Facebook/Instagram) ads data from Adyntel and writes directly to database.

Deploy with:
    modal deploy ingest_meta_ads_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-ingest-meta-ads-db-direct.modal.run
"""

import modal
import json

app = modal.App("hq-master-data-ingest")

# Database connection
db_secret = modal.Secret.from_name("supabase-db-direct")


@app.function(
    secrets=[db_secret],
    timeout=120,
)
@modal.web_endpoint(method="POST")
def ingest_meta_ads_db_direct(
    domain: str,
    meta_ads_payload: dict,
    workflow_source: str = "adyntel-native/meta-ads/ingest/db-direct"
):
    """
    Ingest Meta ads data and write to database.

    1. Write raw payload to raw.meta_ads_payloads
    2. Extract individual ads to extracted.company_meta_ads
    3. Update summary in core.company_meta_ads
    """
    import os
    import psycopg2

    # Connect to database
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    try:
        # 1. Write to raw table
        cur.execute("""
            INSERT INTO raw.meta_ads_payloads
                (domain, payload)
            VALUES (%s, %s)
            RETURNING id
        """, (domain, json.dumps(meta_ads_payload)))
        raw_payload_id = cur.fetchone()[0]

        # 2. Extract individual ads
        ads = meta_ads_payload.get("ads", [])
        ads_extracted = 0
        platforms_set = set()

        for ad in ads:
            ad_id = ad.get("ad_id") or ad.get("id")
            platform = ad.get("platform")
            if platform:
                platforms_set.add(platform)

            start_date = ad.get("start_date")
            end_date = ad.get("end_date")
            status = ad.get("status")
            page_name = ad.get("page_name")

            # Ad creative fields
            ad_creative = ad.get("ad_creative", {})
            ad_creative_body = ad_creative.get("body") if ad_creative else ad.get("ad_creative_body")
            ad_creative_link_title = ad_creative.get("link_title") if ad_creative else ad.get("ad_creative_link_title")
            ad_creative_link_description = ad_creative.get("link_description") if ad_creative else ad.get("ad_creative_link_description")

            landing_page_url = ad.get("landing_page_url")
            image_url = ad.get("image_url")
            video_url = ad.get("video_url")

            cur.execute("""
                INSERT INTO extracted.company_meta_ads
                    (raw_payload_id, domain, ad_id, platform, start_date, end_date, status,
                     page_name, ad_creative_body, ad_creative_link_title, ad_creative_link_description,
                     landing_page_url, image_url, video_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ad_id) DO UPDATE SET
                    raw_payload_id = EXCLUDED.raw_payload_id,
                    platform = EXCLUDED.platform,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    status = EXCLUDED.status,
                    page_name = EXCLUDED.page_name,
                    ad_creative_body = EXCLUDED.ad_creative_body,
                    ad_creative_link_title = EXCLUDED.ad_creative_link_title,
                    ad_creative_link_description = EXCLUDED.ad_creative_link_description,
                    landing_page_url = EXCLUDED.landing_page_url,
                    image_url = EXCLUDED.image_url,
                    video_url = EXCLUDED.video_url
            """, (str(raw_payload_id), domain, ad_id, platform, start_date, end_date, status,
                  page_name, ad_creative_body, ad_creative_link_title, ad_creative_link_description,
                  landing_page_url, image_url, video_url))
            ads_extracted += 1

        # 3. Update core summary
        total_ads = len(ads)
        is_running_ads = total_ads > 0
        platforms = list(platforms_set) if platforms_set else None

        cur.execute("""
            INSERT INTO core.company_meta_ads
                (domain, is_running_ads, ad_count, platforms, last_checked_at, workflow_source, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), %s, NOW())
            ON CONFLICT (domain) DO UPDATE SET
                is_running_ads = EXCLUDED.is_running_ads,
                ad_count = EXCLUDED.ad_count,
                platforms = EXCLUDED.platforms,
                last_checked_at = NOW(),
                workflow_source = EXCLUDED.workflow_source,
                updated_at = NOW()
        """, (domain, is_running_ads, total_ads, platforms, workflow_source))

        conn.commit()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "ads_extracted": ads_extracted,
            "total_ads": total_ads,
            "is_running_ads": is_running_ads,
            "platforms": platforms
        }

    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "domain": domain,
            "error": str(e)
        }
    finally:
        cur.close()
        conn.close()
