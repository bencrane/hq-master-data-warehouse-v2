"""
Read DB Check Endpoint

Checks if a domain exists in a specific schema and table.
"""

import os
import modal
from config import app, image

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def read_db_check_existence(request: dict) -> dict:
    from supabase import create_client, Client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    client: Client = create_client(supabase_url, supabase_key)

    domain = request.get("domain", "").lower().strip()
    schema_name = request.get("schema_name", "").lower().strip()
    table_name = request.get("table_name", "").lower().strip()
    column_name = request.get("column_name", "domain").lower().strip()

    try:
        # Input sanitization
        if not domain or not schema_name or not table_name:
             return {
                 "success": False, 
                 "exists": False, 
                 "error": "Missing parameters",
                 "domain": domain,
                 "schema_name": schema_name,
                 "table_name": table_name
             }
        
        # Strict alphanumeric check for schema/table/column (allow underscores)
        # This prevents injection even though Supabase client is already safe
        if not (schema_name.replace("_","").isalnum() and table_name.replace("_","").isalnum() and column_name.replace("_","").isalnum()):
             return {
                 "success": False, 
                 "exists": False, 
                 "error": "Invalid schema or table name",
                 "domain": domain,
                 "schema_name": schema_name,
                 "table_name": table_name
             }

        # Attempt to query the table
        # We select just the domain column to minimize data transfer
        response = (
            client.schema(schema_name)
            .from_(table_name)
            .select(column_name)
            .eq(column_name, domain)
            .limit(1)
            .execute()
        )
        
        exists = len(response.data) > 0
        
        return {
            "success": True,
            "exists": exists,
            "domain": domain,
            "schema_name": schema_name,
            "table_name": table_name
        }

    except Exception as e:
        # Check for specific error messages indicating table not found
        error_str = str(e)
        if "relation" in error_str and "does not exist" in error_str:
            return {
                "success": False,
                "exists": False,
                "error": f"Table {schema_name}.{table_name} does not exist",
                "domain": domain,
                "schema_name": schema_name,
                "table_name": table_name
            }

        return {
            "success": False, 
            "exists": False, 
            "error": str(e),
            "domain": domain,
            "schema_name": schema_name,
            "table_name": table_name
        }
