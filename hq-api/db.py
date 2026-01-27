import os
import asyncpg
from supabase import create_client, Client
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Connection pool for direct PostgreSQL access
_pool: asyncpg.Pool = None

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

async def init_pool():
    """Initialize asyncpg connection pool."""
    global _pool
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set")
    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,  # 30 second timeout
    )
    return _pool

async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

def get_pool() -> asyncpg.Pool:
    """Get the connection pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool

# Export
__all__ = ['supabase', 'core', 'raw', 'extracted', 'init_pool', 'close_pool', 'get_pool']

# Helper to get core schema client (for simple table queries via Supabase)
def core():
    """Get client for core schema."""
    return supabase

def raw():
    """Get client for raw schema."""
    return supabase.schema("raw")

def extracted():
    """Get client for extracted schema."""
    return supabase.schema("extracted")
