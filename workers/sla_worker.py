"""Run periodically (e.g., every minute via cron/Celery Beat)."""
from datetime import datetime
from db import SessionLocal, TicketRow
from events import emit
from config import config
from sla_engine import get_calendar

def tick():
    cal = get_calendar()
    now = datetime.utcnow()
    with SessionLocal() as s:
        rows = s.query(TicketRow).filter(TicketRow.state.in_(
            ["OPEN", "QUEUED_OFF_HOURS", "PENDING_TEAM_AVAILABILITY"]
        )).all()
        for row in rows:
            payload = dict(row.payload)
            sla = payload["sla"]

            # Pause if in a pause state
            if payload["state"] in config.get("calendar")["pause_states"]:
                sla["paused"] = True
                sla["state"] = "PAUSED"
                row.sla_state = "PAUSED"
                continue

            sla["paused"] = False
            started = datetime.fromisoformat(sla["started_at"].replace("Z", ""))
            elapsed = cal.elapsed_business_minutes(started, now)
            sla["elapsed_minutes"] = elapsed

            if elapsed >= sla["breach_at"] and sla["state"] != "BREACHED":
                sla["state"] = "BREACHED"
                row.sla_state = "BREACHED"
                payload["state"] = "ESCALATED"
                payload["priority"] = "P1"
                row.state = "ESCALATED"
                row.priority = "P1"
                emit(row.ticket_id, "SLA_BREACH", sla["policy_version"],
                     {"elapsed": elapsed, "allowed": sla["allowed_minutes"]})
            elif elapsed >= sla["warn_at"] and sla["state"] == "OK":
                sla["state"] = "WARNED"
                row.sla_state = "WARNED"
                emit(row.ticket_id, "SLA_WARNING", sla["policy_version"],
                     {"elapsed": elapsed, "warn_at": sla["warn_at"]})

            row.payload = payload
        s.commit()


if __name__ == "__main__":
    tick()