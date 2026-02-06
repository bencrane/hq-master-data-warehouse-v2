"""
Modal function: ingest-google-ads-db-direct

Ingests Google ads data from Adyntel and writes directly to database.

Deploy with:
    modal deploy ingest_google_ads_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-ingest-google-ads-db-direct.modal.run
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
def ingest_google_ads_db_direct(
    domain: str,
    google_ads_payload: dict,
    workflow_source: str = "adyntel-native/google-ads/ingest/db-direct"
):
    """
    Ingest Google ads data and write to database.

    1. Write raw payload to raw.google_ads_payloads
    2. Extract individual ads to extracted.company_google_ads
    3. Update summary in core.company_google_ads
    """
    import os
    import psycopg2
    from datetime import datetime

    # Connect to database
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    try:
        # 1. Write to raw table
        cur.execute("""
            INSERT INTO raw.google_ads_payloads
                (domain, payload)
            VALUES (%s, %s)
            RETURNING id
        """, (domain, json.dumps(google_ads_payload)))
        raw_payload_id = cur.fetchone()[0]

        # 2. Extract individual ads
        ads = google_ads_payload.get("ads", [])
        ads_extracted = 0
        advertiser_id = None

        for ad in ads:
            creative_id = ad.get("creative_id") or ad.get("id")
            format_type = ad.get("format")

            # Parse dates
            start_date = ad.get("start_date")
            last_seen = ad.get("last_seen")

            # Advertiser info
            ad_advertiser_id = ad.get("advertiser_id")
            advertiser_name = ad.get("advertiser_name")
            if ad_advertiser_id:
                advertiser_id = ad_advertiser_id  # Keep track for core table

            original_url = ad.get("original_url")

            # Variant info
            variant = ad.get("variant", {})
            variant_content = variant.get("content") if variant else ad.get("variant_content")
            variant_width = variant.get("width") if variant else ad.get("variant_width")
            variant_height = variant.get("height") if variant else ad.get("variant_height")

            cur.execute("""
                INSERT INTO extracted.company_google_ads
                    (raw_payload_id, domain, creative_id, format, start_date, last_seen,
                     advertiser_id, advertiser_name, original_url,
                     variant_content, variant_width, variant_height)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (creative_id) DO UPDATE SET
                    raw_payload_id = EXCLUDED.raw_payload_id,
                    format = EXCLUDED.format,
                    start_date = EXCLUDED.start_date,
                    last_seen = EXCLUDED.last_seen,
                    advertiser_id = EXCLUDED.advertiser_id,
                    advertiser_name = EXCLUDED.advertiser_name,
                    original_url = EXCLUDED.original_url,
                    variant_content = EXCLUDED.variant_content,
                    variant_width = EXCLUDED.variant_width,
                    variant_height = EXCLUDED.variant_height
            """, (str(raw_payload_id), domain, creative_id, format_type, start_date, last_seen,
                  ad_advertiser_id, advertiser_name, original_url,
                  variant_content, variant_width, variant_height))
            ads_extracted += 1

        # 3. Update core summary
        total_ads = len(ads)
        is_running_ads = total_ads > 0

        cur.execute("""
            INSERT INTO core.company_google_ads
                (domain, is_running_ads, ad_count, advertiser_id, last_checked_at, workflow_source, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), %s, NOW())
            ON CONFLICT (domain) DO UPDATE SET
                is_running_ads = EXCLUDED.is_running_ads,
                ad_count = EXCLUDED.ad_count,
                advertiser_id = COALESCE(EXCLUDED.advertiser_id, core.company_google_ads.advertiser_id),
                last_checked_at = NOW(),
                workflow_source = EXCLUDED.workflow_source,
                updated_at = NOW()
        """, (domain, is_running_ads, total_ads, advertiser_id, workflow_source))

        conn.commit()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "ads_extracted": ads_extracted,
            "total_ads": total_ads,
            "is_running_ads": is_running_ads
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
