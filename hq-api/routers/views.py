from fastapi import APIRouter, HTTPException
from db import core
from models import TargetClientView, TargetClientViewCreate, TargetClientViewResponse
import re

router = APIRouter(prefix="/api/target-views", tags=["target-views"])


def domain_to_slug(domain: str) -> str:
    """Convert domain to URL-safe slug: acme.com -> acme-com"""
    return re.sub(r'[^a-z0-9]+', '-', domain.lower()).strip('-')


@router.post("", response_model=TargetClientViewResponse)
async def create_or_update_view(view: TargetClientViewCreate):
    """
    Create or update a target client view.

    If a view for this domain already exists, it will be updated.
    Returns the view with its shareable URL.
    """
    slug = domain_to_slug(view.domain)

    # Check if view exists for this domain
    existing = (
        core()
        .from_("target_client_views")
        .select("id")
        .eq("domain", view.domain.lower())
        .execute()
    )

    if existing.data:
        # Update existing
        result = (
            core()
            .from_("target_client_views")
            .update({
                "name": view.name,
                "filters": view.filters,
                "endpoint": view.endpoint,
                "updated_at": "now()",
            })
            .eq("domain", view.domain.lower())
            .select("*")
            .execute()
        )
    else:
        # Create new
        result = (
            core()
            .from_("target_client_views")
            .insert({
                "domain": view.domain.lower(),
                "name": view.name,
                "slug": slug,
                "filters": view.filters,
                "endpoint": view.endpoint,
            })
            .select("*")
            .execute()
        )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create/update view")

    row = result.data[0]
    return TargetClientViewResponse(
        data=TargetClientView(
            id=str(row["id"]),
            domain=row["domain"],
            name=row["name"],
            slug=row["slug"],
            filters=row["filters"],
            endpoint=row["endpoint"],
            created_at=str(row["created_at"]) if row.get("created_at") else None,
            updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
        ),
        url=f"https://app.revenueinfra.com/v/{row['slug']}"
    )


@router.get("/{slug}", response_model=TargetClientView)
async def get_view_by_slug(slug: str):
    """
    Get a target client view by its slug.

    Frontend uses this to load the saved filters when client visits their URL.
    """
    result = (
        core()
        .from_("target_client_views")
        .select("*")
        .eq("slug", slug)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="View not found")

    row = result.data[0]
    return TargetClientView(
        id=str(row["id"]),
        domain=row["domain"],
        name=row["name"],
        slug=row["slug"],
        filters=row["filters"],
        endpoint=row["endpoint"],
        created_at=str(row["created_at"]) if row.get("created_at") else None,
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )


@router.delete("/{slug}")
async def delete_view(slug: str):
    """Delete a target client view by its slug."""
    result = (
        core()
        .from_("target_client_views")
        .delete()
        .eq("slug", slug)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="View not found")

    return {"message": "View deleted", "slug": slug}
