"""
Sales Pipeline Router

Handles Cal.com webhooks and sales pipeline operations.
Database: imfwppinnfbptqdyraod.supabase.co (separate from main warehouse)
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime, timezone
from typing import Optional
import json
import uuid
import os
import asyncio

from db import get_pipeline_pool

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

# Personal email domains to skip for company extraction
PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "me.com", "aol.com", "protonmail.com",
    "mail.com", "live.com", "msn.com"
}

# From email mapping by organizer domain
FROM_EMAIL_MAP = {
    "revenueengineer.com": "benjamin.crane@revenueengineer.com",
    "outboundsolutions.com": "team@outboundsolutions.com",
    "revenueactivation.io": "team@revenueactivation.io",
}
DEFAULT_FROM_EMAIL = "team@outboundsolutions.com"


def get_from_email(organizer_email: Optional[str]) -> str:
    """Get the from email based on organizer domain."""
    if not organizer_email or "@" not in organizer_email:
        return DEFAULT_FROM_EMAIL
    domain = organizer_email.split("@")[1].lower()
    return FROM_EMAIL_MAP.get(domain, DEFAULT_FROM_EMAIL)


async def send_booking_notification(booking_id: str, event_type: str):
    """
    Send email notification for booking events.

    Args:
        booking_id: UUID of the booking
        event_type: 'created', 'rescheduled', or 'cancelled'
    """
    import resend

    if not RESEND_API_KEY:
        print(f"[NOTIFICATION] RESEND_API_KEY not set, skipping email")
        return

    resend.api_key = RESEND_API_KEY
    pool = get_pipeline_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                b.id, b.calcom_uid, b.title, b.start_time, b.end_time,
                b.location, b.video_url, b.status, b.organizer_email,
                p.email, p.name
            FROM bookings b
            JOIN people p ON b.person_id = p.id
            WHERE b.id = $1
        """, uuid.UUID(booking_id) if isinstance(booking_id, str) else booking_id)

        if not row:
            print(f"[NOTIFICATION] Booking {booking_id} not found")
            return

        title = row["title"]
        start_time = row["start_time"]
        video_url = row["video_url"]
        location = row["location"]
        organizer_email = row["organizer_email"]
        to_email = row["email"]
        name = row["name"] or "there"

        from_email = get_from_email(organizer_email)

        # Format time
        start_str = start_time.strftime("%A, %B %d at %I:%M %p") if start_time else "TBD"
        where = video_url or location or "TBD"

        # Build email content
        if event_type == "created":
            subject = f"Meeting Confirmed: {title}"
            html = f"""
            <h2>Your meeting is confirmed</h2>
            <p>Hi {name},</p>
            <p>Your meeting has been scheduled:</p>
            <ul>
                <li><strong>What:</strong> {title}</li>
                <li><strong>When:</strong> {start_str}</li>
                <li><strong>Where:</strong> {where}</li>
            </ul>
            {f'<p><a href="{video_url}">Join Video Call</a></p>' if video_url else ''}
            <p>Looking forward to speaking with you.</p>
            """
        elif event_type == "rescheduled":
            subject = f"Meeting Rescheduled: {title}"
            html = f"""
            <h2>Your meeting has been rescheduled</h2>
            <p>Hi {name},</p>
            <p>Your meeting has been moved to a new time:</p>
            <ul>
                <li><strong>What:</strong> {title}</li>
                <li><strong>New Time:</strong> {start_str}</li>
                <li><strong>Where:</strong> {where}</li>
            </ul>
            {f'<p><a href="{video_url}">Join Video Call</a></p>' if video_url else ''}
            <p>See you then.</p>
            """
        elif event_type == "cancelled":
            subject = f"Meeting Cancelled: {title}"
            html = f"""
            <h2>Your meeting has been cancelled</h2>
            <p>Hi {name},</p>
            <p>The following meeting has been cancelled:</p>
            <ul>
                <li><strong>What:</strong> {title}</li>
                <li><strong>Was Scheduled:</strong> {start_str}</li>
            </ul>
            <p>If you would like to reschedule, please book a new time.</p>
            """
        else:
            print(f"[NOTIFICATION] Unknown event type: {event_type}")
            return

        # Send with retry
        for attempt in range(3):
            try:
                response = resend.Emails.send({
                    "from": from_email,
                    "to": to_email,
                    "subject": subject,
                    "html": html,
                })
                print(f"[NOTIFICATION] Sent {event_type} email to {to_email} from {from_email}")

                # Update notification timestamp
                await conn.execute(
                    "UPDATE bookings SET notification_sent_at = $1 WHERE id = $2",
                    datetime.now(timezone.utc), row["id"]
                )
                return

            except Exception as e:
                print(f"[NOTIFICATION] Attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"[NOTIFICATION] Failed to send {event_type} email after 3 attempts")


def row_to_dict(row):
    """Convert asyncpg Record to dict, handling UUIDs and datetimes."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'hex'):  # UUID
            d[k] = str(v)
        elif isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def extract_domain_from_email(email: str) -> Optional[str]:
    """Extract company domain from email, skipping personal domains."""
    if not email or "@" not in email:
        return None
    domain = email.split("@")[1].lower()
    if domain in PERSONAL_DOMAINS:
        return None
    return domain


# =============================================================================
# Cal.com Webhook Endpoint
# =============================================================================

@router.post("/webhooks/calcom")
async def ingest_calcom_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Receive Cal.com webhook payload.

    Supported events:
    - BOOKING_CREATED
    - BOOKING_CANCELLED
    - BOOKING_RESCHEDULED
    - MEETING_ENDED
    - PING
    """
    pool = get_pipeline_pool()
    trigger_event = payload.get("triggerEvent", "UNKNOWN")
    inner = payload.get("payload", {})

    async with pool.acquire() as conn:
        # Store raw event
        event_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO calcom_events (id, trigger_event, calcom_uid, calcom_booking_id, payload, received_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """,
            event_id,
            trigger_event,
            inner.get("uid"),
            inner.get("bookingId"),
            json.dumps(payload),
            datetime.now(timezone.utc),
        )

        # Process based on event type
        try:
            booking_id = None
            notification_type = None

            if trigger_event == "BOOKING_CREATED":
                booking_id = await handle_booking_created(conn, event_id, payload)
                notification_type = "created"
            elif trigger_event == "BOOKING_CANCELLED":
                booking_id = await handle_booking_cancelled(conn, event_id, payload)
                notification_type = "cancelled"
            elif trigger_event == "BOOKING_RESCHEDULED":
                booking_id = await handle_booking_rescheduled(conn, event_id, payload)
                notification_type = "rescheduled"
            elif trigger_event == "MEETING_ENDED":
                await handle_meeting_ended(conn, event_id, payload)
            elif trigger_event == "PING":
                await conn.execute(
                    "UPDATE calcom_events SET processed = true, processed_at = $1 WHERE id = $2",
                    datetime.now(timezone.utc), event_id
                )

            # Queue email notification in background
            if booking_id and notification_type:
                background_tasks.add_task(send_booking_notification, str(booking_id), notification_type)

            return {
                "status": "received",
                "event_id": event_id,
                "trigger_event": trigger_event,
            }

        except Exception as e:
            # Record error on event
            await conn.execute(
                "UPDATE calcom_events SET error = $1 WHERE id = $2",
                str(e), event_id
            )
            raise HTTPException(status_code=500, detail=str(e))


async def handle_booking_created(conn, event_id: str, payload: dict):
    """Process BOOKING_CREATED - create person, company, booking, deal."""
    inner = payload.get("payload", {})

    # Extract attendee info
    attendees = inner.get("attendees", [])
    if not attendees:
        raise ValueError("No attendees in payload")

    attendee = attendees[0]
    email = attendee.get("email")
    name = attendee.get("name")

    # Extract company from responses or email domain
    responses = inner.get("responses", {})
    company_name = None
    company_domain = None

    for key, val in responses.items():
        if "company" in key.lower() and isinstance(val, dict):
            company_name = val.get("value")
        elif "domain" in key.lower() and isinstance(val, dict):
            company_domain = val.get("value")

    if not company_domain:
        company_domain = extract_domain_from_email(email)

    # Find or create company
    company_id = None
    if company_domain:
        row = await conn.fetchrow("SELECT id FROM companies WHERE domain = $1", company_domain)
        if row:
            company_id = row["id"]
        else:
            company_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO companies (id, name, domain) VALUES ($1, $2, $3)",
                company_id, company_name or company_domain, company_domain
            )

    # Find or create person
    row = await conn.fetchrow("SELECT id FROM people WHERE email = $1", email)
    if row:
        person_id = row["id"]
        if company_id:
            await conn.execute(
                "UPDATE people SET company_id = $1 WHERE id = $2 AND company_id IS NULL",
                company_id, person_id
            )
    else:
        person_id = uuid.uuid4()
        await conn.execute(
            "INSERT INTO people (id, email, name, company_id) VALUES ($1, $2, $3, $4)",
            person_id, email, name, company_id
        )

    # Extract organizer info
    organizer = inner.get("organizer", {})
    organizer_email = organizer.get("email")
    bare_domain = None
    if organizer_email and "@" in organizer_email:
        bare_domain = organizer_email.split("@")[1].lower()

    # Create booking (upsert)
    calcom_uid = inner.get("uid")
    existing = await conn.fetchrow("SELECT id FROM bookings WHERE calcom_uid = $1", calcom_uid)

    if existing:
        await conn.execute("""
            UPDATE bookings SET
                status = $1, start_time = $2, end_time = $3,
                organizer_email = $4, organizer_name = $5, organizer_username = $6,
                bare_domain = $7, updated_at = now()
            WHERE calcom_uid = $8
        """,
            inner.get("status", "ACCEPTED"),
            inner.get("startTime"),
            inner.get("endTime"),
            organizer_email,
            organizer.get("name"),
            organizer.get("username"),
            bare_domain,
            calcom_uid,
        )
        booking_id = existing["id"]
    else:
        booking_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO bookings (
                id, calcom_uid, calcom_booking_id, person_id, title, event_type,
                start_time, end_time, location, video_url, status, ical_uid, raw_payload,
                organizer_email, organizer_name, organizer_username, bare_domain
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        """,
            booking_id,
            calcom_uid,
            inner.get("bookingId"),
            person_id,
            inner.get("title"),
            inner.get("type"),
            inner.get("startTime"),
            inner.get("endTime"),
            inner.get("location"),
            inner.get("videoCallData", {}).get("url"),
            inner.get("status", "ACCEPTED"),
            inner.get("iCalUID"),
            json.dumps(inner),
            organizer_email,
            organizer.get("name"),
            organizer.get("username"),
            bare_domain,
        )

    # Create deal if company exists and no active deal
    if company_id:
        existing_deal = await conn.fetchrow(
            "SELECT id FROM deals WHERE company_id = $1 AND status = 'active'",
            company_id
        )
        if not existing_deal:
            deal_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO deals (id, company_id, status, stage, organizer_email) VALUES ($1, $2, 'active', 'booked', $3)",
                deal_id, company_id, organizer_email
            )

    # Mark processed
    await conn.execute(
        "UPDATE calcom_events SET processed = true, processed_at = $1 WHERE id = $2",
        datetime.now(timezone.utc), event_id
    )

    return booking_id


async def handle_booking_cancelled(conn, event_id: str, payload: dict):
    """Process BOOKING_CANCELLED - update booking and cancel deal."""
    inner = payload.get("payload", {})
    calcom_uid = inner.get("uid")

    # Update booking and get booking id + person info
    row = await conn.fetchrow("""
        UPDATE bookings SET status = 'CANCELLED', updated_at = now()
        WHERE calcom_uid = $1
        RETURNING id, person_id
    """, calcom_uid)

    booking_id = None
    if row:
        booking_id = row["id"]
        # Get company and cancel deal
        person_row = await conn.fetchrow("SELECT company_id FROM people WHERE id = $1", row["person_id"])
        if person_row and person_row["company_id"]:
            await conn.execute("""
                UPDATE deals SET status = 'cancelled', updated_at = now()
                WHERE company_id = $1 AND status = 'active'
            """, person_row["company_id"])

    await conn.execute(
        "UPDATE calcom_events SET processed = true, processed_at = $1 WHERE id = $2",
        datetime.now(timezone.utc), event_id
    )

    return booking_id


async def handle_booking_rescheduled(conn, event_id: str, payload: dict):
    """
    Process BOOKING_RESCHEDULED.
    Cal.com creates NEW uid/bookingId - we look up by rescheduleUid.
    """
    inner = payload.get("payload", {})
    new_uid = inner.get("uid")
    new_booking_id = inner.get("bookingId")
    original_uid = inner.get("rescheduleUid")

    if not original_uid:
        raise ValueError("No rescheduleUid in payload")

    row = await conn.fetchrow("""
        UPDATE bookings SET
            calcom_uid = $1,
            calcom_booking_id = $2,
            start_time = $3,
            end_time = $4,
            status = $5,
            updated_at = now()
        WHERE calcom_uid = $6
        RETURNING id
    """,
        new_uid,
        new_booking_id,
        inner.get("startTime"),
        inner.get("endTime"),
        inner.get("status", "ACCEPTED"),
        original_uid,
    )

    booking_id = row["id"] if row else None

    await conn.execute(
        "UPDATE calcom_events SET processed = true, processed_at = $1 WHERE id = $2",
        datetime.now(timezone.utc), event_id
    )

    return booking_id


async def handle_meeting_ended(conn, event_id: str, payload: dict):
    """Process MEETING_ENDED - mark attended and advance deal."""
    inner = payload.get("payload", {})
    calcom_uid = inner.get("uid")

    row = await conn.fetchrow("""
        UPDATE bookings SET attended = true, updated_at = now()
        WHERE calcom_uid = $1
        RETURNING person_id
    """, calcom_uid)

    if row:
        person_row = await conn.fetchrow("SELECT company_id FROM people WHERE id = $1", row["person_id"])
        if person_row and person_row["company_id"]:
            await conn.execute("""
                UPDATE deals SET stage = 'met', updated_at = now()
                WHERE company_id = $1 AND status = 'active'
            """, person_row["company_id"])

    await conn.execute(
        "UPDATE calcom_events SET processed = true, processed_at = $1 WHERE id = $2",
        datetime.now(timezone.utc), event_id
    )


# =============================================================================
# Pipeline View Endpoints
# =============================================================================

@router.post("/view")
async def get_pipeline_view(payload: dict = {}):
    """
    Main pipeline view - returns deals with company, contact, and latest booking info.

    Filters (optional):
    - status: 'active', 'won', 'lost', 'cancelled'
    - stage: 'booked', 'met', 'proposal', etc.
    """
    pool = get_pipeline_pool()
    status_filter = payload.get("status", "active")  # Default to active deals
    stage_filter = payload.get("stage")

    query = """
        SELECT
            d.id as deal_id,
            d.status as deal_status,
            d.stage,
            d.notes,
            d.value,
            d.payment_type,
            d.organizer_email,
            d.created_at as deal_created_at,
            c.id as company_id,
            c.name as company_name,
            c.domain as company_domain,
            p.id as contact_id,
            p.name as contact_name,
            p.email as contact_email,
            b.id as booking_id,
            b.title as meeting_title,
            b.start_time as meeting_date,
            b.attended as meeting_attended,
            b.status as booking_status
        FROM deals d
        LEFT JOIN companies c ON d.company_id = c.id
        LEFT JOIN people p ON p.company_id = c.id
        LEFT JOIN LATERAL (
            SELECT * FROM bookings
            WHERE person_id = p.id
            ORDER BY start_time DESC
            LIMIT 1
        ) b ON true
        WHERE 1=1
    """
    params = []

    if status_filter:
        params.append(status_filter)
        query += f" AND d.status = ${len(params)}"
    if stage_filter:
        params.append(stage_filter)
        query += f" AND d.stage = ${len(params)}"

    query += " ORDER BY b.start_time DESC NULLS LAST, d.created_at DESC"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return {"data": [row_to_dict(r) for r in rows]}


@router.post("/deal")
async def get_deal(payload: dict):
    """
    Get single deal with full context.

    Required: deal_id
    """
    pool = get_pipeline_pool()
    deal_id = payload.get("deal_id")

    if not deal_id:
        raise HTTPException(status_code=400, detail="deal_id is required")

    async with pool.acquire() as conn:
        # Get deal with company
        deal = await conn.fetchrow("""
            SELECT
                d.*,
                c.name as company_name,
                c.domain as company_domain
            FROM deals d
            LEFT JOIN companies c ON d.company_id = c.id
            WHERE d.id = $1
        """, uuid.UUID(deal_id))

        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        # Get contacts at this company
        contacts = await conn.fetch("""
            SELECT id, name, email, phone
            FROM people
            WHERE company_id = $1
        """, deal["company_id"])

        # Get bookings for these contacts
        contact_ids = [c["id"] for c in contacts]
        bookings = []
        if contact_ids:
            bookings = await conn.fetch("""
                SELECT b.*, p.name as person_name, p.email as person_email
                FROM bookings b
                JOIN people p ON b.person_id = p.id
                WHERE b.person_id = ANY($1)
                ORDER BY b.start_time DESC
            """, contact_ids)

        return {
            "deal": row_to_dict(deal),
            "contacts": [row_to_dict(c) for c in contacts],
            "bookings": [row_to_dict(b) for b in bookings],
        }


# =============================================================================
# Form Submission Endpoints
# =============================================================================

@router.post("/meeting-outcome")
async def submit_meeting_outcome(payload: dict):
    """
    Submit meeting outcome form.

    Required:
    - deal_id: UUID of the deal
    - outcome: 'completed', 'no_show', 'rescheduled', 'cancelled'

    Optional:
    - notes: Text notes about the meeting
    - next_step: 'follow_up', 'send_proposal', 'close_won', 'close_lost'
    - follow_up_date: ISO date string for next follow up
    """
    pool = get_pipeline_pool()

    deal_id = payload.get("deal_id")
    outcome = payload.get("outcome")

    if not deal_id:
        raise HTTPException(status_code=400, detail="deal_id is required")
    if not outcome:
        raise HTTPException(status_code=400, detail="outcome is required")

    notes = payload.get("notes")
    next_step = payload.get("next_step")

    async with pool.acquire() as conn:
        # Verify deal exists
        deal = await conn.fetchrow("SELECT id, stage FROM deals WHERE id = $1", uuid.UUID(deal_id))
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        # Store form submission
        submission_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO form_submissions (id, form_type, deal_id, payload, submitted_at)
            VALUES ($1, 'meeting_outcome', $2, $3, $4)
        """, submission_id, uuid.UUID(deal_id), json.dumps(payload), datetime.now(timezone.utc))

        # Update deal based on outcome
        new_stage = deal["stage"]
        new_status = "active"

        if outcome == "completed":
            new_stage = "met"
        if next_step == "send_proposal":
            new_stage = "proposal"
        elif next_step == "close_won":
            new_status = "won"
        elif next_step == "close_lost":
            new_status = "lost"

        # Update deal
        await conn.execute("""
            UPDATE deals
            SET stage = $1, status = $2, notes = COALESCE($3, notes), updated_at = now()
            WHERE id = $4
        """, new_stage, new_status, notes, uuid.UUID(deal_id))

        return {
            "status": "submitted",
            "submission_id": str(submission_id),
            "deal_id": deal_id,
            "new_stage": new_stage,
            "new_status": new_status,
        }


@router.post("/offer")
async def submit_offer(payload: dict):
    """
    Submit offer/proposal form.

    Required:
    - deal_id: UUID of the deal
    - value: Numeric value of the offer

    Optional:
    - payment_type: 'one_time', 'monthly', 'quarterly', 'annual'
    - scope: Text description of scope
    - terms: Special terms or conditions
    """
    pool = get_pipeline_pool()

    deal_id = payload.get("deal_id")
    value = payload.get("value")

    if not deal_id:
        raise HTTPException(status_code=400, detail="deal_id is required")
    if value is None:
        raise HTTPException(status_code=400, detail="value is required")

    payment_type = payload.get("payment_type", "one_time")
    scope = payload.get("scope")
    terms = payload.get("terms")

    async with pool.acquire() as conn:
        # Verify deal exists
        deal = await conn.fetchrow("SELECT id FROM deals WHERE id = $1", uuid.UUID(deal_id))
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        # Store form submission
        submission_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO form_submissions (id, form_type, deal_id, payload, submitted_at)
            VALUES ($1, 'offer', $2, $3, $4)
        """, submission_id, uuid.UUID(deal_id), json.dumps(payload), datetime.now(timezone.utc))

        # Update deal with offer details
        await conn.execute("""
            UPDATE deals
            SET value = $1, payment_type = $2, stage = 'proposal', updated_at = now()
            WHERE id = $3
        """, value, payment_type, uuid.UUID(deal_id))

        return {
            "status": "submitted",
            "submission_id": str(submission_id),
            "deal_id": deal_id,
            "value": value,
            "payment_type": payment_type,
        }


# =============================================================================
# Stats Endpoint
# =============================================================================

@router.post("/stats")
async def get_pipeline_stats(payload: dict = {}):
    """Get pipeline statistics."""
    pool = get_pipeline_pool()

    async with pool.acquire() as conn:
        # Deal counts by status
        deal_stats = await conn.fetch("""
            SELECT status, COUNT(*) as count
            FROM deals
            GROUP BY status
        """)

        # Deal counts by stage (active only)
        stage_stats = await conn.fetch("""
            SELECT stage, COUNT(*) as count
            FROM deals
            WHERE status = 'active'
            GROUP BY stage
        """)

        # Total value by status
        value_stats = await conn.fetch("""
            SELECT status, COALESCE(SUM(value), 0) as total_value
            FROM deals
            GROUP BY status
        """)

        return {
            "by_status": {row["status"]: row["count"] for row in deal_stats},
            "by_stage": {row["stage"]: row["count"] for row in stage_stats},
            "value_by_status": {row["status"]: float(row["total_value"]) for row in value_stats},
        }
