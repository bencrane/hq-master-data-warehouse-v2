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
from ingest.company import ingest_company_payload, ingest_company_discovery
from ingest.person import ingest_person_payload, ingest_person_discovery
from icp.generation import generate_target_client_icp

# Re-export for clarity
__all__ = [
    "app",
    "image",
    "ingest_company_payload",
    "ingest_company_discovery",
    "ingest_person_payload",
    "ingest_person_discovery",
    "generate_target_client_icp",
]
