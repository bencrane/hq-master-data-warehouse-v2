import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# Export supabase client for RPC calls
__all__ = ['supabase', 'core', 'raw', 'extracted']

# Helper to get core schema client
def core():
    """Get client for core schema."""
    return supabase

def raw():
    """Get client for raw schema."""
    return supabase.schema("raw")

def extracted():
    """Get client for extracted schema."""
    return supabase.schema("extracted")
