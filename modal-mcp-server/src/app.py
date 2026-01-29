"""
HQ Master Data Ingest - Modal App Entry Point

This is the ONLY file that should be deployed. It imports all modules
and exposes all endpoints for the hq-master-data-ingest app.

Deploy command (from modal-mcp-server/ directory, using uv):
    cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-mcp-server
    uv run modal deploy src/app.py

IMPORTANT: Do NOT run `modal deploy` directly - use `uv run` to ensure
dependencies (pydantic, etc.) are available from the uv-managed venv.

Rules:
    1. All code must be committed to main before deploy
    2. Always deploy from this entry point
    3. Always deploy from main branch
    4. Always use `uv run modal deploy` (not bare `modal deploy`)
"""

# Import the app from config (this is what Modal looks for)
import modal
from config import app, image

# Import all endpoint modules - this registers them with the app
# These imports must happen AFTER app is defined in config
from ingest.company import ingest_clay_company_firmo, ingest_clay_find_companies, ingest_all_comp_customers, upsert_core_company, ingest_manual_comp_customer, ingest_clay_find_co_lctn_prsd
from ingest.person import ingest_clay_person_profile, ingest_clay_find_people, ingest_clay_find_ppl_lctn_prsd, ingest_ppl_title_enrich
from ingest.case_study import ingest_case_study_extraction
from ingest.waterfall import command_center_email_enrichment, get_email_job
from ingest.icp_verdict import ingest_icp_verdict
from ingest.crunchbase_domain import infer_crunchbase_domain
from ingest.signal_new_hire import ingest_clay_signal_new_hire
from ingest.signal_news_fundraising import ingest_clay_signal_news_fundraising
from ingest.signal_job_posting import ingest_clay_signal_job_posting
from ingest.signal_job_change import ingest_clay_signal_job_change
from ingest.signal_promotion import ingest_clay_signal_promotion
from ingest.company_address import ingest_company_address_parsing
from ingest.lookup import lookup_person_location, lookup_salesnav_location, lookup_salesnav_company_location, lookup_job_title, ingest_clay_company_location_lookup, ingest_clay_person_location_lookup
from ingest.vc_portfolio import ingest_vc_portfolio
from ingest.vc_investors import ingest_company_vc_investors
from ingest.backfill import backfill_person_location, backfill_person_matched_location
from ingest.backfill_cleaned_company_name import backfill_cleaned_company_name
from ingest.backfill_company_descriptions import backfill_company_descriptions
from ingest.salesnav_person import ingest_salesnav_person
from ingest.nostra_ecom import ingest_nostra_ecom_company
from ingest.nostra_ecom_people import ingest_nostra_ecom_person
from ingest.leadmagic_company import ingest_leadmagic_company
from ingest.core_company_simple import ingest_core_company_simple
from ingest.apollo_scrape import ingest_apollo_scrape
from ingest.cleaned_company_name import ingest_cleaned_company_name
from ingest.salesnav_company import ingest_salesnav_company
from ingest.apollo_instantdata import extract_apollo_instantdata
from ingest.apollo_people_cleaned import ingest_apollo_people_cleaned
from ingest.apollo_companies_cleaned import ingest_apollo_companies_cleaned
from ingest.company_enrich_similar import find_similar_companies_batch, find_similar_companies_single, get_similar_companies_batch_status
from ingest.company_enrich_similar_queue import process_similar_companies_queue, get_similar_companies_queue_status
from ingest.company_customers_claygent import ingest_company_customers_claygent
from ingest.company_customers_structured import ingest_company_customers_structured
from ingest.company_customers_v2 import ingest_company_customers_v2
from ingest.company_customers_status import get_company_customers_status
from ingest.company_public import ingest_public_company
from ingest.vc_domain_lookup import lookup_vc_domain
from ingest.vc_domain_update import update_vc_domain
from icp.generation import generate_target_client_icp
from cleanup.delete_companies_no_location import delete_companies_no_location

# CRITICAL: Explicitly import extraction module so Modal mounts it.
# The ingest functions import from extraction.company and extraction.person
# inside their function bodies (lazy imports). Modal's static analysis may
# not detect these runtime imports, so we force it to mount the package here.
import extraction.company
import extraction.person
import extraction.case_study
import extraction.icp_verdict
import extraction.crunchbase_domain
import extraction.signal_new_hire
import extraction.signal_news_fundraising
import extraction.signal_job_posting
import extraction.signal_job_change
import extraction.signal_promotion
import extraction.company_address
import extraction.salesnav_person
import extraction.vc_investors
import extraction.company_mapping
import extraction.person_mapping

# Simple test endpoint - always keep this
@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def test_endpoint(data: dict) -> dict:
    """Simple test endpoint that echoes back what you send."""
    return {"success": True, "received": data}


# Re-export for clarity
__all__ = [
    "app",
    "image",
    "test_endpoint",
    "ingest_clay_find_ppl_lctn_prsd",
    "ingest_ppl_title_enrich",
    "ingest_clay_company_firmo",
    "ingest_clay_find_companies",
    "ingest_clay_find_co_lctn_prsd",
    "ingest_all_comp_customers",
    "upsert_core_company",
    "ingest_manual_comp_customer",
    "ingest_clay_person_profile",
    "ingest_clay_find_people",
    "ingest_case_study_extraction",
    "ingest_icp_verdict",
    "generate_target_client_icp",
    "command_center_email_enrichment",
    "get_email_job",
    "infer_crunchbase_domain",
    "ingest_clay_signal_new_hire",
    "ingest_clay_signal_news_fundraising",
    "ingest_clay_signal_job_posting",
    "ingest_clay_signal_job_change",
    "ingest_clay_signal_promotion",
    "ingest_company_address_parsing",
    "lookup_person_location",
    "lookup_salesnav_location",
    "lookup_salesnav_company_location",
    "lookup_job_title",
    "ingest_clay_company_location_lookup",
    "ingest_clay_person_location_lookup",
    "ingest_vc_portfolio",
    "ingest_company_vc_investors",
    "backfill_person_location",
    "backfill_person_matched_location",
    "ingest_salesnav_person",
    "ingest_nostra_ecom_company",
    "ingest_nostra_ecom_person",
    "ingest_leadmagic_company",
    "ingest_core_company_simple",
    "ingest_apollo_scrape",
    "ingest_cleaned_company_name",
    "ingest_salesnav_company",
    "extract_apollo_instantdata",
    "backfill_cleaned_company_name",
    "backfill_company_descriptions",
    "ingest_apollo_people_cleaned",
    "ingest_apollo_companies_cleaned",
    "find_similar_companies_batch",
    "find_similar_companies_single",
    "get_similar_companies_batch_status",
    "process_similar_companies_queue",
    "get_similar_companies_queue_status",
    "ingest_company_customers_claygent",
    "ingest_company_customers_structured",
    "ingest_company_customers_v2",
    "get_company_customers_status",
    "ingest_public_company",
    "lookup_vc_domain",
    "update_vc_domain",
]
