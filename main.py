import uuid
import json
import traceback
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from db import init_db, SessionLocal, TicketRow
from models import Ticket, TicketState, Priority, SLAInfo, SLAState
from events import emit
from config import config
from sla_engine import compute_sla_milestones, get_calendar, recompute_from_start
from stages.ingest import normalize, segment
from stages.extract import extract
from stages.validate import check_mandatory, generate_missing_question
from stages.dedup import fingerprint
from stages.priority import compute as compute_priority
from stages.routing import route
from stages.handoff import build_summary


app = FastAPI(title="Ticket System", version="0.1.0")
init_db()


class ConversationIn(BaseModel):
    turns: List[dict]
    meta: dict = {}


def find_duplicate(fp, order_id):
    with SessionLocal() as s:
        q = s.query(TicketRow).filter(TicketRow.fingerprint == fp)
        if order_id:
            q = q.filter(TicketRow.order_id == order_id)
        return q.first()


def persist(ticket):
    with SessionLocal() as s:
        s.add(TicketRow(
            ticket_id=ticket.ticket_id,
            state=ticket.state.value,
            priority=ticket.priority.value,
            priority_score=ticket.priority_score,
            fingerprint=ticket.fingerprint,
            order_id=ticket.order.id,
            customer_id=ticket.customer.id,
            category=ticket.issue.category,
            payload=json.loads(json.dumps(ticket.model_dump(mode="json"), default=str)),
            sla_state=ticket.sla.state.value,
            sla_breach_at=None,
            sla_warn_at=None,
            paused=ticket.sla.paused,
        ))
        s.commit()


@app.post("/conversations", tags=["Tickets"])
def ingest_conversation(body: ConversationIn):
    try:
        conv = normalize(body.model_dump())
        segments = segment(conv)
        created = []

        for seg in segments:
            ex = extract(seg)

            missing = check_mandatory(ex)
            if missing:
                question = generate_missing_question(missing)
                t = Ticket(
                    ticket_id=f"TCK-{uuid.uuid4().hex[:8]}",
                    state=TicketState.AWAITING_INFO,
                    customer=ex.customer, order=ex.order, product=ex.product,
                    issue=ex.issue, contact=ex.contact, evidence=ex.evidence,
                    sentiment=ex.sentiment,
                )
                persist(t)
                emit(t.ticket_id, "AWAITING_INFO", str(config.version), {"question": question})
                created.append({"ticket_id": t.ticket_id, "state": t.state.value, "question": question})
                continue

            fp = fingerprint(ex)
            dup = find_duplicate(fp, ex.order.id)
            if dup:
                emit(dup.ticket_id, "DUPLICATE_MERGED", str(config.version), {"new_fp": fp})
                created.append({"ticket_id": dup.ticket_id, "state": "MERGED_DUPLICATE"})
                continue

            started = datetime.utcnow()
            prio, score = compute_priority(ex, 0, 240)

            sla_cfg = config.get("sla_policies") or {}
            policy_version = sla_cfg.get("version", "v1")
            milestones = compute_sla_milestones(started, prio, ex.issue.category, policy_version)

            r = route(ex.issue.category)
            state = TicketState.OPEN
            if r["reason"] == "off_hours":
                state = TicketState.QUEUED_OFF_HOURS
            elif r["reason"] in ("fallback_backup_team", "no_skilled_agent"):
                state = TicketState.PENDING_TEAM_AVAILABILITY

            t = Ticket(
                ticket_id=f"TCK-{uuid.uuid4().hex[:8]}",
                state=state, priority=Priority(prio), priority_score=score,
                customer=ex.customer, order=ex.order, product=ex.product,
                issue=ex.issue, contact=ex.contact, evidence=ex.evidence,
                sentiment=ex.sentiment, fingerprint=fp,
                sla=SLAInfo(
                    policy_version=milestones["policy_version"],
                    allowed_minutes=milestones["allowed_minutes"],
                    elapsed_minutes=milestones["elapsed_minutes"],
                    warn_at=milestones["warn_at"],
                    breach_at=milestones["breach_at"],
                    state=SLAState.PAUSED if state != TicketState.OPEN else SLAState.OK,
                    paused=state != TicketState.OPEN,
                    started_at=started,
                ),
            )
            t.routing.team = r["team"]
            t.routing.agent = r["agent"]
            t.routing.reason = r["reason"]
            t.handoff_summary = build_summary(t.model_dump(mode="json"))

            persist(t)
            emit(t.ticket_id, "TICKET_CREATED", milestones["policy_version"], t.model_dump(mode="json"))

            created.append({
                "ticket_id": t.ticket_id,
                "state": t.state.value,
                "priority": t.priority.value,
                "routed_to": r,
                "handoff_summary": t.handoff_summary,
            })

        return {"created": created}

    except Exception as e:
        return {
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc().split("\n"),
        }


@app.post("/admin/reload-config", tags=["Admin"])
def reload_config(key: Optional[str] = None):
    config.reload(key)
    affected = []
    with SessionLocal() as s:
        rows = s.query(TicketRow).filter(TicketRow.state.in_(
            ["OPEN", "QUEUED_OFF_HOURS", "PENDING_TEAM_AVAILABILITY"]
        )).all()
        for row in rows:
            payload = dict(row.payload)
            payload = recompute_from_start(payload)
            row.payload = payload
            row.sla_state = payload["sla"]["state"]
            row.priority = payload["priority"]
            affected.append(row.ticket_id)
        s.commit()
    return {"reloaded": key or "all", "version": config.version, "recomputed": affected}


@app.get("/tickets/{ticket_id}", tags=["Tickets"])
def get_ticket(ticket_id: str):
    with SessionLocal() as s:
        row = s.get(TicketRow, ticket_id)
        if not row:
            raise HTTPException(404, "not found")
        return row.payload


@app.get("/", tags=["Info"])
def root():
    return {
        "name": "Ticket System",
        "status": "running",
        "docs": "/docs",
        "endpoints": [
            "POST /conversations",
            "GET  /tickets/{ticket_id}",
            "POST /admin/reload-config",
        ],
    }