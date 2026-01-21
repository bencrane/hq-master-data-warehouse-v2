"""
HQ Master Data Ingest - Modal App Entry Point

This is the ONLY file that should be deployed. It imports all modules
and exposes all endpoints for the hq-master-data-ingest app.

Deploy command (from src/ directory):
    cd modal-mcp-server/src && modal deploy app.py

Rules:
    1. All code must be committed to main before deploy
    2. Always deploy from this entry point
    3. Always deploy from main branch
"""

# Import the app from config (this is what Modal looks for)
from config import app, image

# Import all endpoint modules - this registers them with the app
# These imports must happen AFTER app is defined in config
from ingest.company import ingest_clay_company_firmo, ingest_clay_find_companies, ingest_all_comp_customers, upsert_core_company, ingest_manual_comp_customer
from ingest.person import ingest_clay_person_profile, ingest_clay_find_people
from ingest.case_study import ingest_case_study_extraction
from ingest.waterfall import command_center_email_enrichment, get_email_job
from ingest.icp_verdict import ingest_icp_verdict
from ingest.crunchbase_domain import infer_crunchbase_domain
from ingest.signal_new_hire import ingest_clay_signal_new_hire
from ingest.signal_news_fundraising import ingest_clay_signal_news_fundraising
from ingest.signal_job_posting import ingest_clay_signal_job_posting
from ingest.signal_job_change import ingest_clay_signal_job_change
from ingest.signal_promotion import ingest_clay_signal_promotion
from icp.generation import generate_target_client_icp

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

# Re-export for clarity
__all__ = [
    "app",
    "image",
    "ingest_clay_company_firmo",
    "ingest_clay_find_companies",
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
]
