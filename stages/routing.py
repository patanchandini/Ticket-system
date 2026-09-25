from datetime import datetime
from config import config
from sla_engine import get_calendar

def required_skills(category: str) -> list[str]:
    return config.get("skills")["categories"].get(category, [])

def agent_loads() -> dict:
    # In prod: query open ticket counts per agent
    return {}

def is_agent_available(agent: dict, now: datetime) -> bool:
    cal = get_calendar()
    local = now.astimezone(cal.tz)
    shift = agent["shift"]
    sh, sm = map(int, shift["start"].split(":"))
    eh, em = map(int, shift["end"].split(":"))
    return (cal.is_business_day(local.date())
            and (sh, sm) <= (local.hour, local.minute) < (eh, em))

def route(category: str, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    skills = required_skills(category)
    agents = config.get("skills")["agents"]
    loads = agent_loads()

    candidates = []
    for a in agents:
        if not set(skills).issubset(a["skills"]):
            continue
        if not is_agent_available(a, now):
            continue
        load = loads.get(a["id"], 0)
        if load >= a.get("wip_cap", 5):
            continue
        skill_match = len(set(skills) & set(a["skills"])) / max(len(skills), 1)
        workload_ratio = load / max(a.get("wip_cap", 5), 1)
        score = 0.5*skill_match + 0.3*(1 - workload_ratio) + 0.2*1.0
        candidates.append((score, a))

    if candidates:
        candidates.sort(reverse=True, key=lambda x: x[0])
        a = candidates[0][1]
        return {"team": f"{category}-tier1", "agent": a["id"], "reason": "skill+availability+workload"}

    # Fallback chain
    backups = config.get("skills")["backup"].get(category, [])
    for team in backups:
        if team == "on_call":
            on_call = config.get("skills")["teams"].get("on_call", [])
            if on_call:
                return {"team": "on_call", "agent": on_call[0], "reason": "fallback_on_call"}
        return {"team": team, "agent": None, "reason": "fallback_backup_team"}

    # Off-hours / pending
    cal = get_calendar()
    if not cal.is_business_time(now):
        return {"team": None, "agent": None, "reason": "off_hours"}
    return {"team": None, "agent": None, "reason": "no_skilled_agent"}