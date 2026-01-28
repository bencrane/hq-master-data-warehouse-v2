from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional, List
from db import get_auth_pool
from models import Org, User, UserWithOrg, SessionValidation, MagicLinkRequest, MagicLinkResponse, VerifyMagicLinkResponse
import secrets
import os
from datetime import datetime, timedelta
import httpx

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


@router.get("/orgs", response_model=List[Org])
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


@router.post("/send-magic-link", response_model=MagicLinkResponse)
async def send_magic_link(request: MagicLinkRequest):
    """
    Send a magic link to the user's email.

    Checks if the email domain is approved before sending.
    """
    email = request.email.lower().strip()
    domain = email.split("@")[-1] if "@" in email else None

    if not domain:
        raise HTTPException(status_code=400, detail="Invalid email format")

    pool = get_auth_pool()

    # Check if domain is approved
    approved = await pool.fetchrow(
        "SELECT * FROM core.approved_domains WHERE domain = $1",
        domain
    )

    if not approved:
        raise HTTPException(status_code=403, detail="Email domain not approved for access")

    # Generate token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    # Store token
    await pool.execute(
        """
        INSERT INTO core.magic_link_tokens (email, token, expires_at)
        VALUES ($1, $2, $3)
        """,
        email, token, expires_at
    )

    # Send email via Resend
    resend_api_key = os.getenv("RESEND_API_KEY")
    if not resend_api_key:
        raise HTTPException(status_code=500, detail="Email service not configured")

    verify_url = f"https://app.revenueinfra.com/auth/verify?token={token}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": "Revenue Activation <team@revenueactivation.com>",
                "to": [email],
                "subject": "Sign in to Revenue Activation",
                "html": f"""
                <h2>Sign in to Revenue Activation</h2>
                <p>Click the link below to sign in:</p>
                <p><a href="{verify_url}">Sign in to Revenue Activation</a></p>
                <p>This link expires in 1 hour.</p>
                <p>If you didn't request this, you can ignore this email.</p>
                """
            }
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to send email")

    return MagicLinkResponse(success=True, message="Magic link sent to your email")


@router.get("/verify-magic-link", response_model=VerifyMagicLinkResponse)
async def verify_magic_link(token: str = Query(...)):
    """
    Verify a magic link token and create a session.

    Creates user and org if they don't exist.
    """
    pool = get_auth_pool()

    # Get and validate token
    token_row = await pool.fetchrow(
        """
        SELECT * FROM core.magic_link_tokens
        WHERE token = $1 AND expires_at > NOW() AND used_at IS NULL
        """,
        token
    )

    if not token_row:
        return VerifyMagicLinkResponse(success=False, message="Invalid or expired link")

    email = token_row["email"]
    domain = email.split("@")[-1]

    # Mark token as used
    await pool.execute(
        "UPDATE core.magic_link_tokens SET used_at = NOW() WHERE token = $1",
        token
    )

    # Check if user exists
    user_row = await pool.fetchrow(
        'SELECT * FROM public."user" WHERE email = $1',
        email
    )

    if not user_row:
        # Create user
        user_id = secrets.token_urlsafe(16)
        name = email.split("@")[0].replace(".", " ").title()

        await pool.execute(
            """
            INSERT INTO public."user" (id, email, name, "emailVerified", "createdAt", "updatedAt")
            VALUES ($1, $2, $3, true, NOW(), NOW())
            """,
            user_id, email, name
        )

        # Get approved domain info for org creation
        approved = await pool.fetchrow(
            "SELECT * FROM core.approved_domains WHERE domain = $1",
            domain
        )

        if approved and approved["auto_create_org"]:
            # Check if org exists for this domain
            org_row = await pool.fetchrow(
                "SELECT * FROM core.orgs WHERE domain = $1",
                domain
            )

            if not org_row:
                # Create org
                org_name = approved["org_name"] or domain.split(".")[0].title()
                slug = domain.replace(".", "-")

                org_result = await pool.fetchrow(
                    """
                    INSERT INTO core.orgs (name, slug, domain, status, services_enabled, created_at, updated_at)
                    VALUES ($1, $2, $3, 'active', '{"intent": false, "inbound": false, "outbound": false}', NOW(), NOW())
                    RETURNING id
                    """,
                    org_name, slug, domain
                )
                org_id = org_result["id"]
            else:
                org_id = org_row["id"]

            # Link user to org
            await pool.execute(
                """
                INSERT INTO core.org_users (org_id, user_id, role, created_at)
                VALUES ($1, $2::uuid, 'member', NOW())
                """,
                org_id, user_id
            )
    else:
        user_id = user_row["id"]

    # Create session
    session_token = secrets.token_urlsafe(32)
    session_expires = datetime.utcnow() + timedelta(days=30)

    await pool.execute(
        """
        INSERT INTO public.session (id, token, "userId", "expiresAt", "createdAt", "updatedAt")
        VALUES ($1, $2, $3, $4, NOW(), NOW())
        """,
        secrets.token_urlsafe(16), session_token, user_id, session_expires
    )

    # Get user for response
    user_row = await pool.fetchrow(
        'SELECT * FROM public."user" WHERE id = $1',
        user_id
    )

    user = User(
        id=str(user_row["id"]),
        email=user_row["email"],
        name=user_row["name"],
        email_verified=True,
        is_active=True,
        created_at=user_row["createdAt"].isoformat() if user_row["createdAt"] else None
    )

    return VerifyMagicLinkResponse(
        success=True,
        token=session_token,
        user=user,
        message="Successfully signed in"
    )
