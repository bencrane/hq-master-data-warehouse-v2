"""
Backfill Endpoints - batch update extracted tables from reference lookups

- backfill_person_location: Update person_discovery with location data from location_lookup

v2: Removed RPC, uses standard Supabase client methods only
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class BackfillPersonLocationRequest(BaseModel):
    dry_run: bool = True
    limit: Optional[int] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,  # 10 minutes for large batches
)
@modal.fastapi_endpoint(method="POST")
def backfill_person_location(request: BackfillPersonLocationRequest) -> dict:
    """
    Backfill city/state/country in extracted.person_discovery from reference.location_lookup.
    
    Only updates records where city IS NULL (won't overwrite existing data).
    Matches on exact location_name.
    
    Args:
        dry_run: If True, returns preview of what would be updated without writing. Default True.
        limit: Max records to update. None = all matching records.
    
    Returns:
        - dry_run=True: count of matchable records + sample
        - dry_run=False: count of updated records
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Get all lookup entries (paginate to get all, not just default 1000)
        lookup_map = {}
        offset = 0
        batch_size = 1000
        while True:
            lookup_result = (
                supabase.schema("reference")
                .from_("location_lookup")
                .select("location_name, city, state, country, has_city, has_state, has_country")
                .range(offset, offset + batch_size - 1)
                .execute()
            )
            if not lookup_result.data:
                break
            for r in lookup_result.data:
                lookup_map[r["location_name"]] = r
            if len(lookup_result.data) < batch_size:
                break
            offset += batch_size
        
        if request.dry_run:
            # Get records missing city (with count)
            missing_city = (
                supabase.schema("extracted")
                .from_("person_discovery")
                .select("id, location_name", count="exact")
                .is_("city", "null")
                .not_.is_("location_name", "null")
                .limit(5000)  # Sample first 5000
                .execute()
            )
            
            # Count matches in sample
            match_count = 0
            sample_records = []
            for record in missing_city.data:
                if record["location_name"] in lookup_map:
                    match_count += 1
                    if len(sample_records) < 10:
                        lookup = lookup_map[record["location_name"]]
                        sample_records.append({
                            "location_name": record["location_name"],
                            "city": lookup["city"],
                            "state": lookup["state"],
                            "country": lookup["country"],
                        })
            
            return {
                "dry_run": True,
                "records_missing_city": missing_city.count,
                "lookup_entries": len(lookup_map),
                "matches_in_sample": match_count,
                "sample_size": len(missing_city.data),
                "sample_matches": sample_records,
                "message": "Set dry_run=False to execute update"
            }
        
        else:
            # Execute the update
            # lookup_map already loaded above
            
            # Find matches and update
            updated_count = 0
            errors = []
            processed_count = 0
            batch_size = 1000
            offset = 0
            
            while True:
                # Get batch of records missing city
                missing_city = (
                    supabase.schema("extracted")
                    .from_("person_discovery")
                    .select("id, location_name")
                    .is_("city", "null")
                    .not_.is_("location_name", "null")
                    .range(offset, offset + batch_size - 1)
                    .execute()
                )
                
                if not missing_city.data:
                    break  # No more records
                
                for record in missing_city.data:
                    if request.limit and updated_count >= request.limit:
                        break
                        
                    location_name = record["location_name"]
                    if location_name in lookup_map:
                        lookup = lookup_map[location_name]
                        try:
                            supabase.schema("extracted").from_("person_discovery").update({
                                "city": lookup["city"],
                                "state": lookup["state"],
                                "country": lookup["country"],
                                "has_city": lookup["has_city"],
                                "has_state": lookup["has_state"],
                                "has_country": lookup["has_country"],
                            }).eq("id", record["id"]).execute()
                            updated_count += 1
                        except Exception as e:
                            errors.append({"id": record["id"], "error": str(e)})
                    
                    processed_count += 1
                
                # Stop if we've hit our limit
                if request.limit and updated_count >= request.limit:
                    break
                    
                offset += batch_size
                
                # Safety: don't process more than 100k records without a limit
                if not request.limit and offset > 100000:
                    break
            
            return {
                "dry_run": False,
                "updated_count": updated_count,
                "processed_count": processed_count,
                "limit": request.limit,
                "errors": errors[:10] if errors else [],
                "error_count": len(errors),
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
