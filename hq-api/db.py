import os
import asyncpg
from supabase import create_client, Client
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_DATABASE_URL = os.getenv("AUTH_DATABASE_URL")

# Connection pools for direct PostgreSQL access
_pool: asyncpg.Pool = None
_auth_pool: asyncpg.Pool = None

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

async def init_pool():
    """Initialize asyncpg connection pools."""
    global _pool, _auth_pool
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set")
    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    # Initialize auth pool if AUTH_DATABASE_URL is set
    if AUTH_DATABASE_URL:
        _auth_pool = await asyncpg.create_pool(
            AUTH_DATABASE_URL,
            min_size=1,
            max_size=5,
            command_timeout=30,
        )
    return _pool

async def close_pool():
    """Close the connection pools."""
    global _pool, _auth_pool
    if _pool:
        await _pool.close()
        _pool = None
    if _auth_pool:
        await _auth_pool.close()
        _auth_pool = None

def get_pool() -> asyncpg.Pool:
    """Get the main data connection pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool

def get_auth_pool() -> asyncpg.Pool:
    """Get the auth database connection pool."""
    if _auth_pool is None:
        raise RuntimeError("Auth database pool not initialized. Set AUTH_DATABASE_URL.")
    return _auth_pool

# Export
__all__ = ['supabase', 'core', 'raw', 'extracted', 'reference', 'init_pool', 'close_pool', 'get_pool', 'get_auth_pool']

# Helper to get core schema client (for simple table queries via Supabase)
def core():
    """Get client for core schema."""
    return supabase.schema("core")

def raw():
    """Get client for raw schema."""
    return supabase.schema("raw")

def extracted():
    """Get client for extracted schema."""
    return supabase.schema("extracted")

def reference():
    """Get client for reference schema."""
    return supabase.schema("reference")
