"""
Lookup Client Leads

Returns leads affiliated with a client domain, joined with
enriched data from core tables (job title, location, company country, etc.).
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class LookupClientLeadsRequest(BaseModel):
    client_domain: str
    limit: Optional[int] = 100
    offset: Optional[int] = 0


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_client_leads(request: LookupClientLeadsRequest) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Get leads for this client
        leads_result = (
            supabase.schema("client")
            .from_("leads")
            .select("id, full_name, person_linkedin_url, company_domain, company_name, source, created_at")
            .eq("client_domain", request.client_domain)
            .order("company_name")
            .range(request.offset, request.offset + request.limit - 1)
            .execute()
        )

        if not leads_result.data:
            return {"success": True, "client_domain": request.client_domain, "total": 0, "leads": []}

        # Collect linkedin_urls and company_domains for batch lookups
        linkedin_urls = [l["person_linkedin_url"] for l in leads_result.data if l.get("person_linkedin_url")]
        company_domains = list({l["company_domain"] for l in leads_result.data if l.get("company_domain")})

        # Batch lookup: people_full for job titles, seniority, person location
        people_map = {}
        if linkedin_urls:
            people_result = (
                supabase.schema("core")
                .from_("people_full")
                .select("linkedin_url, matched_cleaned_job_title, matched_seniority, matched_job_function, person_city, person_state, person_country")
                .in_("linkedin_url", linkedin_urls)
                .execute()
            )
            for p in (people_result.data or []):
                people_map[p["linkedin_url"]] = p

        # Batch lookup: company locations for country
        company_country_map = {}
        if company_domains:
            loc_result = (
                supabase.schema("core")
                .from_("company_locations")
                .select("domain, country")
                .in_("domain", company_domains)
                .execute()
            )
            for loc in (loc_result.data or []):
                company_country_map[loc["domain"]] = loc["country"]

        # Batch lookup: company linkedin_urls
        company_linkedin_map = {}
        if company_domains:
            comp_result = (
                supabase.schema("core")
                .from_("companies")
                .select("domain, linkedin_url")
                .in_("domain", company_domains)
                .execute()
            )
            for c in (comp_result.data or []):
                if c.get("linkedin_url"):
                    company_linkedin_map[c["domain"]] = c["linkedin_url"]

        # Assemble response
        leads = []
        for lead in leads_result.data:
            linkedin_url = lead.get("person_linkedin_url")
            domain = lead.get("company_domain")
            person = people_map.get(linkedin_url, {})
            full_name = lead.get("full_name") or ""
            name_parts = full_name.strip().split(" ", 1)

            leads.append({
                "id": lead["id"],
                "first_name": name_parts[0] if name_parts else None,
                "last_name": name_parts[1] if len(name_parts) > 1 else None,
                "full_name": full_name,
                "person_linkedin_url": linkedin_url,
                "job_title": person.get("matched_cleaned_job_title"),
                "seniority": person.get("matched_seniority"),
                "job_function": person.get("matched_job_function"),
                "person_city": person.get("person_city"),
                "person_state": person.get("person_state"),
                "person_country": person.get("person_country"),
                "company_name": lead.get("company_name"),
                "company_domain": domain,
                "company_linkedin_url": company_linkedin_map.get(domain),
                "company_country": company_country_map.get(domain),
                "source": lead.get("source"),
            })

        return {
            "success": True,
            "client_domain": request.client_domain,
            "total": len(leads),
            "leads": leads,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
