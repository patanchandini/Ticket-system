import uuid
import json
from db import SessionLocal, EventRow
from datetime import datetime


def emit(ticket_id: str, event_type: str, policy_version: str, payload: dict):
    """Idempotent event emission. Payload is JSON-safe-ified first."""
    event_id = f"{ticket_id}:{event_type}:{policy_version}"
    # Convert datetimes/enums to strings so SQLite JSON column works
    safe_payload = json.loads(json.dumps(payload, default=str))
    with SessionLocal() as s:
        existing = s.get(EventRow, event_id)
        if existing:
            return False
        s.add(EventRow(
            event_id=event_id,
            ticket_id=ticket_id,
            event_type=event_type,
            policy_version=policy_version,
            payload=safe_payload,
        ))
        s.commit()
    return True