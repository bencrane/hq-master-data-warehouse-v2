"""
CompanyEnrich Similar Companies Preview Results Ingest

Receives CompanyEnrich similar/preview results from Clay,
stores raw payload, extracts similarity relationship data,
extracts full company profiles to dedicated extracted tables,
and conditionally writes to core tables for new domains.
"""

import os
import modal
from datetime import datetime
from typing import Optional

from config import app, image


SOURCE = "companyenrich-similar-preview"

def parse_datetime(dt_str: Optional[str]) -> Optional[str]:
    """Parse datetime string to ISO format."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).isoformat()
    except Exception:
        return None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def ingest_companyenrich_similar_preview_results(data: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    input_domain = data.get("input_domain", "").lower().strip()
    if not input_domain:
        return {"success": False, "error": "input_domain is required"}

    payload = data.get("payload", {})
    if isinstance(payload, str):
        import json
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": "payload must be valid JSON"}

    items = payload.get("items", [])
    scores = (payload.get("metadata") or {}).get("scores", {})

    try:
        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("company_enrich_similar_raw")
            .insert({
                "input_domain": input_domain,
                "similarity_weight": 0.0,
                "raw_response": payload,
                "status_code": 200,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        extracted_count = 0
        core_count = 0
        profile_count = 0
        core_new_companies = 0

        for item in items:
            company_id = item.get("id")
            company_domain = item.get("domain")
            score = scores.get(str(company_id)) if company_id else None

            # --- (a) Extract to existing similarity relationship table ---
            try:
                supabase.schema("extracted").from_("company_enrich_similar").insert({
                    "raw_id": raw_id,
                    "input_domain": input_domain,
                    "company_id": company_id,
                    "company_name": item.get("name"),
                    "company_domain": company_domain,
                    "company_website": item.get("website"),
                    "company_industry": item.get("industry"),
                    "company_description": item.get("description"),
                    "company_keywords": item.get("keywords"),
                    "company_logo_url": item.get("logo_url"),
                    "similarity_score": score,
                }).execute()
                extracted_count += 1
            except Exception:
                pass

            # --- (b) Upsert to existing core similarity table ---
            if company_domain:
                try:
                    supabase.schema("core").from_("company_similar_companies_preview").upsert({
                        "input_domain": input_domain,
                        "company_name": item.get("name"),
                        "company_domain": company_domain,
                        "company_industry": item.get("industry"),
                        "company_description": item.get("description"),
                        "similarity_score": score,
                        "source": "companyenrich-preview",
                    }, on_conflict="input_domain,company_domain").execute()
                    core_count += 1
                except Exception:
                    pass

            # Skip full profile extraction if no domain
            if not company_domain:
                continue

            # Extract nested objects from item
            location = item.get("location") or {}
            socials = item.get("socials") or {}
            financial = item.get("financial") or {}
            city_obj = location.get("city") or {}
            state_obj = location.get("state") or {}
            country_obj = location.get("country") or {}

            # --- (c) Extract to companyenrich_similar_company_profile ---
            try:
                supabase.schema("extracted").from_("companyenrich_similar_company_profile").upsert({
                    "domain": company_domain,
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "website": item.get("website"),
                    "industry": item.get("industry"),
                    "industries": item.get("industries"),
                    "description": item.get("description"),
                    "seo_description": item.get("seo_description"),
                    "employees": item.get("employees"),
                    "revenue": item.get("revenue"),
                    "founded_year": item.get("founded_year"),
                    "page_rank": item.get("page_rank"),
                    "categories": item.get("categories"),
                    "naics_codes": item.get("naics_codes"),
                    "keywords": item.get("keywords"),
                    "logo_url": item.get("logo_url"),
                    "companyenrich_id": str(company_id) if company_id else None,
                    "companyenrich_updated_at": parse_datetime(item.get("updated_at")),
                }, on_conflict="domain").execute()
                profile_count += 1
            except Exception:
                pass

            # --- (d) Extract to companyenrich_similar_company_location ---
            if location:
                try:
                    supabase.schema("extracted").from_("companyenrich_similar_company_location").upsert({
                        "domain": company_domain,
                        "city": city_obj.get("name"),
                        "state": state_obj.get("name"),
                        "state_code": state_obj.get("code"),
                        "country": country_obj.get("name"),
                        "country_code": country_obj.get("code"),
                        "address": location.get("address"),
                        "postal_code": location.get("postal_code"),
                        "phone": location.get("phone"),
                        "latitude": city_obj.get("latitude"),
                        "longitude": city_obj.get("longitude"),
                    }, on_conflict="domain").execute()
                except Exception:
                    pass

            # --- (e) Extract to companyenrich_similar_company_socials ---
            if socials:
                try:
                    supabase.schema("extracted").from_("companyenrich_similar_company_socials").upsert({
                        "domain": company_domain,
                        "linkedin_url": socials.get("linkedin_url"),
                        "linkedin_id": socials.get("linkedin_id"),
                        "twitter_url": socials.get("twitter_url"),
                        "facebook_url": socials.get("facebook_url"),
                        "instagram_url": socials.get("instagram_url"),
                        "youtube_url": socials.get("youtube_url"),
                        "github_url": socials.get("github_url"),
                        "crunchbase_url": socials.get("crunchbase_url"),
                        "angellist_url": socials.get("angellist_url"),
                        "g2_url": socials.get("g2_url"),
                    }, on_conflict="domain").execute()
                except Exception:
                    pass

            # --- (f) Extract to companyenrich_similar_company_technologies ---
            technologies = item.get("technologies") or []
            for tech in technologies:
                if tech:
                    try:
                        supabase.schema("extracted").from_("companyenrich_similar_company_technologies").upsert(
                            {"domain": company_domain, "technology": tech},
                            on_conflict="domain,technology"
                        ).execute()
                    except Exception:
                        pass

            # --- (g) Extract to companyenrich_similar_company_financial ---
            if financial:
                try:
                    supabase.schema("extracted").from_("companyenrich_similar_company_financial").upsert({
                        "domain": company_domain,
                        "funding_stage": financial.get("funding_stage"),
                        "total_funding": financial.get("total_funding"),
                        "stock_symbol": financial.get("stock_symbol"),
                        "stock_exchange": financial.get("stock_exchange"),
                        "latest_funding_date": parse_datetime(financial.get("funding_date")),
                    }, on_conflict="domain").execute()
                except Exception:
                    pass

            # --- (h) Extract to companyenrich_similar_company_funding_rounds ---
            funding_rounds = financial.get("funding") or []
            for round_data in funding_rounds:
                funding_date = parse_datetime(round_data.get("date"))
                funding_type = round_data.get("type")
                if funding_type or funding_date:
                    try:
                        supabase.schema("extracted").from_("companyenrich_similar_company_funding_rounds").upsert({
                            "domain": company_domain,
                            "funding_type": funding_type,
                            "amount": round_data.get("amount"),
                            "funding_date": funding_date,
                            "investors": round_data.get("from"),
                            "url": round_data.get("url"),
                        }, on_conflict="domain,funding_type,funding_date").execute()
                    except Exception:
                        pass

            # --- (i) Check-then-insert to core tables (only if domain is new) ---
            try:
                existing = (
                    supabase.schema("core")
                    .from_("companies")
                    .select("id")
                    .eq("domain", company_domain)
                    .execute()
                )
                if existing.data:
                    # Domain already in core — skip all core writes
                    continue
            except Exception:
                # If check fails, skip core writes to be safe
                continue

            # Domain is new — insert to core.companies
            try:
                supabase.schema("core").from_("companies").insert({
                    "domain": company_domain,
                    "name": item.get("name"),
                    "linkedin_url": socials.get("linkedin_url"),
                }).execute()
                core_new_companies += 1
            except Exception:
                # If core.companies insert fails (race condition), skip dimension writes
                continue

            # Core dimension writes (all wrapped individually so one failure doesn't block others)

            # core.company_descriptions
            desc = item.get("description")
            seo_desc = item.get("seo_description")
            if desc or seo_desc:
                try:
                    supabase.schema("core").from_("company_descriptions").upsert({
                        "domain": company_domain,
                        "description": desc,
                        "tagline": seo_desc,
                        "source": SOURCE,
                    }, on_conflict="domain").execute()
                except Exception:
                    pass

            # core.company_locations
            city_name = city_obj.get("name")
            state_name = state_obj.get("name")
            country_name = country_obj.get("name")
            if city_name or state_name or country_name:
                try:
                    supabase.schema("core").from_("company_locations").upsert({
                        "domain": company_domain,
                        "city": city_name,
                        "state": state_name,
                        "country": country_name,
                        "raw_location": location.get("address"),
                        "raw_country": country_name,
                        "has_city": city_name is not None,
                        "has_state": state_name is not None,
                        "source": SOURCE,
                    }, on_conflict="domain").execute()
                except Exception:
                    pass

            # core.company_employee_range (via reference lookup)
            raw_employees = item.get("employees")
            if raw_employees:
                try:
                    lookup = (
                        supabase.schema("reference")
                        .from_("employee_range_lookup")
                        .select("size_cleaned")
                        .eq("size_raw", raw_employees)
                        .execute()
                    )
                    if lookup.data:
                        supabase.schema("core").from_("company_employee_range").upsert({
                            "domain": company_domain,
                            "employee_range": lookup.data[0]["size_cleaned"],
                            "source": SOURCE,
                        }, on_conflict="domain").execute()
                except Exception:
                    pass

            # core.company_revenue (via reference lookup)
            raw_revenue = item.get("revenue")
            if raw_revenue:
                try:
                    rev_lookup = (
                        supabase.schema("reference")
                        .from_("revenue_range_lookup")
                        .select("matched_revenue_range")
                        .eq("raw_value", raw_revenue)
                        .execute()
                    )
                    matched_revenue = rev_lookup.data[0]["matched_revenue_range"] if rev_lookup.data else None
                    supabase.schema("core").from_("company_revenue").upsert({
                        "domain": company_domain,
                        "source": SOURCE,
                        "raw_revenue_range": raw_revenue,
                        "matched_revenue_range": matched_revenue,
                    }, on_conflict="domain,source").execute()
                except Exception:
                    pass

            # core.company_industries (via reference lookup)
            industry = item.get("industry")
            if industry:
                try:
                    industry_lookup = (
                        supabase.schema("reference")
                        .from_("industry_lookup")
                        .select("industry_cleaned")
                        .eq("industry_raw", industry)
                        .execute()
                    )
                    matched_industry = industry_lookup.data[0]["industry_cleaned"] if industry_lookup.data else industry
                    supabase.schema("core").from_("company_industries").insert({
                        "domain": company_domain,
                        "matched_industry": matched_industry,
                        "source": SOURCE,
                    }).execute()
                except Exception:
                    pass

            # core.company_business_model (derived from categories — b2b/b2c)
            categories = item.get("categories") or []
            categories_lower = [c.lower() for c in categories if c]
            if categories_lower:
                b2b = any("b2b" in c for c in categories_lower)
                b2c = any("b2c" in c for c in categories_lower)
                if b2b or b2c:
                    biz_model = "B2B" if b2b and not b2c else "B2C" if b2c and not b2b else "B2B & B2C"
                    try:
                        supabase.schema("core").from_("company_business_model").upsert({
                            "domain": company_domain,
                            "business_model": biz_model,
                            "source": SOURCE,
                        }, on_conflict="domain").execute()
                    except Exception:
                        pass

            # core.company_types
            raw_type = item.get("type")
            if raw_type:
                matched_type = None
                try:
                    type_lookup = (
                        supabase.schema("reference")
                        .from_("company_type_lookup")
                        .select("matched_company_type")
                        .eq("raw_value", raw_type.lower())
                        .execute()
                    )
                    if type_lookup.data:
                        matched_type = type_lookup.data[0]["matched_company_type"]
                    supabase.schema("core").from_("company_types").upsert({
                        "domain": company_domain,
                        "source": SOURCE,
                        "raw_type": raw_type,
                        "matched_type": matched_type,
                    }, on_conflict="domain,source").execute()
                except Exception:
                    pass

            # core.company_social_urls
            if socials:
                try:
                    supabase.schema("core").from_("company_social_urls").upsert({
                        "domain": company_domain,
                        "linkedin_url": socials.get("linkedin_url"),
                        "twitter_url": socials.get("twitter_url"),
                        "facebook_url": socials.get("facebook_url"),
                        "github_url": socials.get("github_url"),
                        "youtube_url": socials.get("youtube_url"),
                        "instagram_url": socials.get("instagram_url"),
                        "crunchbase_url": socials.get("crunchbase_url"),
                        "g2_url": socials.get("g2_url"),
                        "angellist_url": socials.get("angellist_url"),
                        "source": SOURCE,
                    }, on_conflict="domain").execute()
                except Exception:
                    pass

            # core.company_categories (one row per category)
            for cat in categories:
                if cat:
                    try:
                        supabase.schema("core").from_("company_categories").upsert({
                            "domain": company_domain,
                            "category": cat,
                            "source": SOURCE,
                        }, on_conflict="domain,category").execute()
                    except Exception:
                        pass

            # core.company_keywords (one row per keyword)
            keywords = item.get("keywords") or []
            for kw in keywords:
                if kw:
                    try:
                        supabase.schema("core").from_("company_keywords").upsert({
                            "domain": company_domain,
                            "keyword": kw,
                            "source": SOURCE,
                        }, on_conflict="domain,keyword").execute()
                    except Exception:
                        pass

            # core.company_funding
            total_funding = financial.get("total_funding")
            if total_funding:
                try:
                    supabase.schema("core").from_("company_funding").upsert({
                        "domain": company_domain,
                        "total_funding": total_funding,
                        "source": SOURCE,
                    }, on_conflict="domain").execute()
                except Exception:
                    pass

        return {
            "success": True,
            "input_domain": input_domain,
            "raw_id": raw_id,
            "items_received": len(items),
            "extracted_count": extracted_count,
            "core_count": core_count,
            "profile_count": profile_count,
            "core_new_companies": core_new_companies,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
