"""
Modal function: ingest-linkedin-ads-db-direct

Ingests LinkedIn ads data from Adyntel and writes directly to database.

Deploy with:
    modal deploy ingest_linkedin_ads_db_direct.py

Endpoint URL:
    https://bencrane--hq-master-data-ingest-ingest-linkedin-ads-db-direct.modal.run
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
def ingest_linkedin_ads_db_direct(
    domain: str,
    linkedin_ads_payload: dict,
    workflow_source: str = "adyntel-native/linkedin-ads/ingest/db-direct"
):
    """
    Ingest LinkedIn ads data and write to database.

    1. Write raw payload to raw.linkedin_ads_payloads
    2. Extract individual ads to extracted.company_linkedin_ads
    3. Update summary in core.company_linkedin_ads
    """
    import os
    import psycopg2

    # Connect to database
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    try:
        # 1. Write to raw table
        cur.execute("""
            INSERT INTO raw.linkedin_ads_payloads
                (domain, payload)
            VALUES (%s, %s)
            RETURNING id
        """, (domain, json.dumps(linkedin_ads_payload)))
        raw_payload_id = cur.fetchone()[0]

        # 2. Extract individual ads
        ads = linkedin_ads_payload.get("ads", [])
        ads_extracted = 0

        for ad in ads:
            ad_id = ad.get("ad_id")
            ad_type = ad.get("type")
            creative_type = ad.get("creative_type")

            headline = ad.get("headline", {})
            headline_title = headline.get("title") if headline else None
            headline_description = headline.get("description") if headline else None

            commentary = ad.get("commentary", {})
            commentary_text = commentary.get("text") if commentary else None

            image = ad.get("image", {})
            image_url = image.get("url") if image else None
            image_alt_text = image.get("alt_text") if image else None

            advertiser = ad.get("advertiser", {})
            advertiser_name = advertiser.get("name") if advertiser else None

            view_details_link = ad.get("view_details_link")

            cur.execute("""
                INSERT INTO extracted.company_linkedin_ads
                    (raw_payload_id, domain, ad_id, ad_type, creative_type,
                     headline_title, headline_description, commentary_text,
                     image_url, image_alt_text, advertiser_name, view_details_link)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ad_id) DO UPDATE SET
                    raw_payload_id = EXCLUDED.raw_payload_id,
                    ad_type = EXCLUDED.ad_type,
                    creative_type = EXCLUDED.creative_type,
                    headline_title = EXCLUDED.headline_title,
                    headline_description = EXCLUDED.headline_description,
                    commentary_text = EXCLUDED.commentary_text,
                    image_url = EXCLUDED.image_url,
                    image_alt_text = EXCLUDED.image_alt_text,
                    advertiser_name = EXCLUDED.advertiser_name,
                    view_details_link = EXCLUDED.view_details_link
            """, (str(raw_payload_id), domain, ad_id, ad_type, creative_type,
                  headline_title, headline_description, commentary_text,
                  image_url, image_alt_text, advertiser_name, view_details_link))
            ads_extracted += 1

        # 3. Update core summary
        total_ads = len(ads)
        is_running_ads = total_ads > 0

        cur.execute("""
            INSERT INTO core.company_linkedin_ads
                (domain, is_running_ads, ad_count, last_checked_at, workflow_source, updated_at)
            VALUES (%s, %s, %s, NOW(), %s, NOW())
            ON CONFLICT (domain) DO UPDATE SET
                is_running_ads = EXCLUDED.is_running_ads,
                ad_count = EXCLUDED.ad_count,
                last_checked_at = NOW(),
                workflow_source = EXCLUDED.workflow_source,
                updated_at = NOW()
        """, (domain, is_running_ads, total_ads, workflow_source))

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
