from datetime import datetime, timedelta
from dateutil import parser as dtparser
import pytz
from config import config

class SLACalendar:
    def __init__(self, cfg: dict):
        self.tz = pytz.timezone(cfg["timezone"])
        self.weekends = set(cfg["weekends"])
        self.holidays = set(dtparser.parse(h).date() for h in cfg.get("holidays", []))
        self.start = datetime.strptime(cfg["business_hours"]["start"], "%H:%M").time()
        self.end = datetime.strptime(cfg["business_hours"]["end"], "%H:%M").time()

    def is_business_day(self, d) -> bool:
        return d.weekday() not in self.weekends and d not in self.holidays

    def is_business_time(self, dt: datetime) -> bool:
        local = dt.astimezone(self.tz)
        return (self.is_business_day(local.date())
                and self.start <= local.time() < self.end)

    def next_business_instant(self, dt: datetime) -> datetime:
        cur = dt.astimezone(self.tz)
        while True:
            if self.is_business_day(cur.date()):
                if cur.time() < self.start:
                    cur = self.tz.localize(datetime.combine(cur.date(), self.start))
                    return cur
                if cur.time() < self.end:
                    return cur
            # advance to next day 00:00
            cur = self.tz.localize(
                datetime.combine(cur.date() + timedelta(days=1), datetime.min.time())
            )

    def add_business_minutes(self, start: datetime, minutes: int) -> datetime:
        cur = start.astimezone(self.tz)
        remaining = minutes
        while remaining > 0:
            if self.is_business_time(cur):
                cur += timedelta(minutes=1)
                remaining -= 1
            else:
                cur = self.next_business_instant(cur)
        return cur

    def elapsed_business_minutes(self, start: datetime, end: datetime) -> int:
        cur = start.astimezone(self.tz)
        end = end.astimezone(self.tz)
        count = 0
        while cur < end:
            if self.is_business_time(cur):
                count += 1
            cur += timedelta(minutes=1)
        return count


def get_calendar() -> SLACalendar:
    return SLACalendar(config.get("calendar"))


def get_allowed_minutes(priority: str, category: str) -> int:
    pol = config.get("sla_policies")
    overrides = pol.get("overrides", {}).get(priority, {})
    if category in overrides:
        return overrides[category]
    return pol["defaults"][priority]


def compute_sla_milestones(started_at: datetime, priority: str, category: str,
                           policy_version: str) -> dict:
    cal = get_calendar()
    allowed = get_allowed_minutes(priority, category)
    warn_at = int(allowed * 0.75)
    warn_dt = cal.add_business_minutes(started_at, warn_at)
    breach_dt = cal.add_business_minutes(started_at, allowed)
    return {
        "policy_version": policy_version,
        "allowed_minutes": allowed,
        "warn_at": warn_at,
        "breach_at": allowed,
        "warn_dt": warn_dt,
        "breach_dt": breach_dt,
        "elapsed_minutes": cal.elapsed_business_minutes(started_at, datetime.utcnow()),
    }


def recompute_from_start(ticket_payload: dict) -> dict:
    """Runtime SLA policy change: recompute from original start, preserving elapsed."""
    sla = ticket_payload["sla"]
    started_at = dtparser.parse(sla["started_at"])
    new = compute_sla_milestones(
        started_at,
        ticket_payload["priority"],
        ticket_payload["issue"]["category"],
        policy_version=config.get("sla_policies").get("version", "v1"),
    )
    sla.update({
        "policy_version": new["policy_version"],
        "allowed_minutes": new["allowed_minutes"],
        "warn_at": new["warn_at"],
        "breach_at": new["breach_at"],
        "elapsed_minutes": new["elapsed_minutes"],
    })
    # Re-evaluate state
    if sla["elapsed_minutes"] >= sla["breach_at"]:
        sla["state"] = "BREACHED"
    elif sla["elapsed_minutes"] >= sla["warn_at"]:
        sla["state"] = "WARNED"
    else:
        sla["state"] = "OK"
    return ticket_payload