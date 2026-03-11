"""meta_capi.py — Send server-side events to Meta Conversions API.

Fires a 'Lead' event when someone submits the audit form.
This runs alongside the browser-side Pixel for redundant tracking —
Meta deduplicates using event_id.
"""

import hashlib
import logging
import os
import time
import uuid

import httpx

logger = logging.getLogger(__name__)

PIXEL_ID = os.getenv("META_PIXEL_ID", "1263685122494774")
ACCESS_TOKEN = os.getenv("META_CAPI_TOKEN", "")
GRAPH_URL = f"https://graph.facebook.com/v21.0/{PIXEL_ID}/events"


def _hash(value: str | None) -> str | None:
    """SHA-256 hash a value (lowercase, stripped) per Meta requirements."""
    if not value or not value.strip():
        return None
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


async def send_lead_event(
    email: str,
    full_name: str | None = None,
    phone: str | None = None,
    source_url: str | None = None,
    fbc: str | None = None,
    fbp: str | None = None,
    event_id: str | None = None,
) -> dict:
    """Send a Lead event to Meta Conversions API.

    Args:
        email: Lead's email (will be hashed).
        full_name: Lead's full name (will be hashed as fn + ln).
        phone: Lead's phone (will be hashed).
        source_url: The landing page URL.
        fbc: The _fbc cookie from the browser (click attribution).
        fbp: The _fbp cookie from the browser (browser ID).
        event_id: Unique ID for deduplication with browser Pixel.

    Returns:
        Dict with success status and Meta's response.
    """
    if not ACCESS_TOKEN:
        logger.warning("meta_capi: META_CAPI_TOKEN not set — skipping")
        return {"success": False, "error": "No access token configured"}

    ev_id = event_id or str(uuid.uuid4())

    # Parse first/last name
    fn, ln = None, None
    if full_name and full_name.strip():
        parts = full_name.strip().split(" ", 1)
        fn = parts[0] if parts else None
        ln = parts[1] if len(parts) > 1 else None

    # Build user_data with hashed PII
    user_data: dict = {}
    if email:
        user_data["em"] = [_hash(email)]
    if fn:
        user_data["fn"] = [_hash(fn)]
    if ln:
        user_data["ln"] = [_hash(ln)]
    if phone:
        user_data["ph"] = [_hash(phone)]
    if fbc:
        user_data["fbc"] = fbc
    if fbp:
        user_data["fbp"] = fbp

    payload = {
        "data": [
            {
                "event_name": "Lead",
                "event_time": int(time.time()),
                "event_id": ev_id,
                "event_source_url": source_url or "https://audits.luminaclippers.com",
                "action_source": "website",
                "user_data": user_data,
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                GRAPH_URL,
                params={"access_token": ACCESS_TOKEN},
                json=payload,
            )
            result = resp.json()
            logger.info(
                "meta_capi: Lead event sent — event_id=%s status=%s response=%s",
                ev_id, resp.status_code, result,
            )
            return {
                "success": resp.status_code == 200,
                "event_id": ev_id,
                "meta_response": result,
            }
    except Exception as exc:
        logger.error("meta_capi: failed to send Lead event — %s", exc)
        return {"success": False, "event_id": ev_id, "error": str(exc)}
