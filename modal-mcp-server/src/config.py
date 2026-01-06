"""
Shared Modal App Configuration

This module defines the Modal app and image that all endpoint modules use.
"""

import modal

# Define the app - single source of truth
app = modal.App("hq-master-data-ingest")

# Build the image with all dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "supabase",
    "pydantic",
    "fastapi",
    "openai",
)
