"""
Alumni Lookup Endpoint

Returns people who used to work at a given company, including their current
employer details and past job title.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image

# Batch size for IN queries to avoid URL length limits
BATCH_SIZE = 100


def batch_in_query(supabase, schema: str, table: str, select: str, in_column: str, in_values: list, extra_filters: dict = None):
    """Execute IN query in batches to avoid URL length limits."""
    all_results = []
    for i in range(0, len(in_values), BATCH_SIZE):
        batch = in_values[i:i + BATCH_SIZE]
        query = supabase.schema(schema).from_(table).select(select).in_(in_column, batch)
        if extra_filters:
            for key, value in extra_filters.items():
                query = query.eq(key, value)
        result = query.execute()
        if result.data:
            all_results.extend(result.data)
    return all_results


class AlumniLookupRequest(BaseModel):
    """Request model for alumni lookup."""
    past_company_domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_alumni(request: AlumniLookupRequest) -> dict:
    """
    Lookup alumni (former employees) of a company by domain.
    Returns people who previously worked at the company with their current job info.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # 1. Get alumni from person_past_employer
        alumni_result = (
            supabase.schema("core")
            .from_("person_past_employer")
            .select("linkedin_url, past_company_name, past_company_domain")
            .eq("past_company_domain", request.past_company_domain)
            .execute()
        )

        if not alumni_result.data:
            return {
                "success": True,
                "past_company_domain": request.past_company_domain,
                "alumni_count": 0,
                "alumni": [],
            }

        linkedin_urls = list(set(
            a.get("linkedin_url") for a in alumni_result.data
            if a.get("linkedin_url")
        ))

        if not linkedin_urls:
            return {
                "success": True,
                "past_company_domain": request.past_company_domain,
                "alumni_count": 0,
                "alumni": [],
            }

        # Build lookup dict for past company info
        alumni_info = {
            a["linkedin_url"]: {
                "past_company_name": a.get("past_company_name"),
                "past_company_domain": a.get("past_company_domain"),
            }
            for a in alumni_result.data
            if a.get("linkedin_url")
        }

        # 2. Get current job info from work_history (batched)
        current_job_data = batch_in_query(
            supabase, "core", "person_work_history",
            "linkedin_url, title, company_name, company_domain",
            "linkedin_url", linkedin_urls,
            {"is_current": True}
        )

        current_job_map = {}
        current_company_domains = set()
        for r in current_job_data:
            url = r.get("linkedin_url")
            if url:
                current_job_map[url] = {
                    "current_job_title": r.get("title"),
                    "current_company_name": r.get("company_name"),
                    "current_company_domain": r.get("company_domain"),
                }
                if r.get("company_domain"):
                    current_company_domains.add(r["company_domain"])

        # 3. Get past job title at the specific company (batched)
        past_job_data = batch_in_query(
            supabase, "core", "person_work_history",
            "linkedin_url, title",
            "linkedin_url", linkedin_urls,
            {"company_domain": request.past_company_domain, "is_current": False}
        )

        past_job_map = {}
        for r in past_job_data:
            url = r.get("linkedin_url")
            if url and r.get("title"):
                past_job_map[url] = r["title"]

        # 4. Get cleaned names from salesnav_scrapes_person (batched)
        names_data = batch_in_query(
            supabase, "extracted", "salesnav_scrapes_person",
            "linkedin_url, cleaned_first_name, cleaned_last_name, cleaned_full_name, first_name, last_name",
            "linkedin_url", linkedin_urls
        )

        names_map = {}
        urls_with_names = set()
        for r in names_data:
            url = r.get("linkedin_url")
            if url:
                # Priority: cleaned names, then raw names
                first = r.get("cleaned_first_name") or r.get("first_name")
                last = r.get("cleaned_last_name") or r.get("last_name")
                full = r.get("cleaned_full_name")
                if not full and first and last:
                    full = f"{first} {last}"
                elif not full and first:
                    full = first
                elif not full and last:
                    full = last

                if first or last or full:
                    names_map[url] = {
                        "first_name": first,
                        "last_name": last,
                        "full_name": full,
                    }
                    urls_with_names.add(url)

        # 5. Fallback to core.people for names not found (batched)
        urls_without_names = [u for u in linkedin_urls if u not in urls_with_names]
        if urls_without_names:
            people_data = batch_in_query(
                supabase, "core", "people",
                "linkedin_url, full_name",
                "linkedin_url", urls_without_names
            )
            for r in people_data:
                url = r.get("linkedin_url")
                full_name = r.get("full_name")
                if url and full_name:
                    names_map[url] = {
                        "first_name": None,
                        "last_name": None,
                        "full_name": full_name,
                    }

        # 6. Get LinkedIn URLs for current companies (batched)
        company_linkedin_map = {}
        if current_company_domains:
            linkedin_data = batch_in_query(
                supabase, "core", "companies_full",
                "domain, linkedin_url",
                "domain", list(current_company_domains)
            )
            company_linkedin_map = {
                r["domain"]: r["linkedin_url"]
                for r in linkedin_data
                if r.get("linkedin_url")
            }

        # 7. Merge all data
        alumni = []
        for url in linkedin_urls:
            info = alumni_info.get(url, {})
            names = names_map.get(url, {})
            current = current_job_map.get(url, {})
            past_title = past_job_map.get(url)

            current_domain = current.get("current_company_domain")

            alumni.append({
                "first_name": names.get("first_name"),
                "last_name": names.get("last_name"),
                "full_name": names.get("full_name"),
                "linkedin_url": url,
                "current_company_name": current.get("current_company_name"),
                "current_company_domain": current_domain,
                "current_company_linkedin_url": company_linkedin_map.get(current_domain) if current_domain else None,
                "current_job_title": current.get("current_job_title"),
                "past_company_name": info.get("past_company_name"),
                "past_company_domain": info.get("past_company_domain"),
                "past_job_title": past_title,
            })

        return {
            "success": True,
            "past_company_domain": request.past_company_domain,
            "alumni_count": len(alumni),
            "alumni": alumni,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "past_company_domain": request.past_company_domain,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
