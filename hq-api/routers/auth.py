from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from db import get_auth_pool
from models import Org, User, UserWithOrg, SessionValidation

router = APIRouter(prefix="/api/auth", tags=["auth"])


def row_to_dict(row):
    """Convert asyncpg Record to dict, converting UUIDs to strings."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'hex'):  # UUID object
            d[k] = str(v)
        elif hasattr(v, 'isoformat'):  # datetime object
            d[k] = v.isoformat()
    return d


@router.get("/session", response_model=SessionValidation)
async def validate_session(authorization: Optional[str] = Header(None)):
    """
    Validate a session token.

    Pass token in Authorization header: "Bearer <token>"
    Returns whether session is valid and user_id if so.
    """
    if not authorization:
        return SessionValidation(valid=False)

    # Extract token from "Bearer <token>"
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    pool = get_auth_pool()

    # Check session table (BetterAuth uses 'session' table)
    row = await pool.fetchrow(
        """
        SELECT "userId", "expiresAt"
        FROM public.session
        WHERE token = $1 AND "expiresAt" > NOW()
        """,
        token
    )

    if not row:
        return SessionValidation(valid=False)

    return SessionValidation(
        valid=True,
        user_id=str(row["userId"]),
        expires_at=row["expiresAt"].isoformat() if row["expiresAt"] else None
    )


@router.get("/me", response_model=UserWithOrg)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Get the current user and their org from session token.

    Pass token in Authorization header: "Bearer <token>"
    Returns user details, org, and role.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization token provided")

    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    pool = get_auth_pool()

    # Get session and user
    session_row = await pool.fetchrow(
        """
        SELECT s."userId", s."expiresAt", u.name, u.email, u."emailVerified", u.image, u."createdAt"
        FROM public.session s
        JOIN public."user" u ON u.id = s."userId"
        WHERE s.token = $1 AND s."expiresAt" > NOW()
        """,
        token
    )

    if not session_row:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user = User(
        id=str(session_row["userId"]),
        email=session_row["email"],
        name=session_row["name"],
        email_verified=session_row["emailVerified"] or False,
        avatar_url=session_row["image"],
        is_active=True,
        created_at=session_row["createdAt"].isoformat() if session_row["createdAt"] else None
    )

    # Get org membership
    org_row = await pool.fetchrow(
        """
        SELECT o.*, ou.role
        FROM core.org_users ou
        JOIN core.orgs o ON o.id = ou.org_id
        WHERE ou.user_id = $1::uuid
        """,
        session_row["userId"]
    )

    org = None
    role = None
    if org_row:
        org_dict = row_to_dict(org_row)
        role = org_dict.pop("role", None)
        org = Org(**org_dict)

    return UserWithOrg(user=user, org=org, role=role)


@router.get("/orgs", response_model=list[Org])
async def list_orgs():
    """List all organizations (admin endpoint)."""
    pool = get_auth_pool()

    rows = await pool.fetch(
        """
        SELECT * FROM core.orgs
        ORDER BY created_at DESC
        """
    )

    return [Org(**row_to_dict(row)) for row in rows]


@router.get("/orgs/{slug}", response_model=Org)
async def get_org_by_slug(slug: str):
    """Get an organization by slug."""
    pool = get_auth_pool()

    row = await pool.fetchrow(
        """
        SELECT * FROM core.orgs
        WHERE slug = $1
        """,
        slug
    )

    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")

    return Org(**row_to_dict(row))
