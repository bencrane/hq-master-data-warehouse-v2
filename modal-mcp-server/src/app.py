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
from ingest.company import ingest_clay_company_firmo, ingest_clay_find_companies
from ingest.person import ingest_clay_person_profile, ingest_clay_find_people
from icp.generation import generate_target_client_icp

# CRITICAL: Explicitly import extraction module so Modal mounts it.
# The ingest functions import from extraction.company and extraction.person
# inside their function bodies (lazy imports). Modal's static analysis may
# not detect these runtime imports, so we force it to mount the package here.
import extraction.company
import extraction.person

# Re-export for clarity
__all__ = [
    "app",
    "image",
    "ingest_clay_company_firmo",
    "ingest_clay_find_companies",
    "ingest_clay_person_profile",
    "ingest_clay_find_people",
    "generate_target_client_icp",
]
