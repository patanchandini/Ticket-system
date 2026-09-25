SEV = {"S1": 100, "S2": 70, "S3": 40, "S4": 15}
TIER = {"gold": 20, "silver": 10, "standard": 5}


def compute(ex, waiting_minutes_business: int, sla_target: int) -> tuple[str, float]:
    severity = SEV.get(ex.issue.severity, 15)
    sentiment = (1 - (ex.sentiment + 1) / 2) * 20
    wait = min(waiting_minutes_business / max(sla_target, 1), 1) * 20
    impact = TIER.get((ex.customer.tier or "standard").lower(), 5)
    if ex.order.value:
        impact += min(ex.order.value / 1000, 10)
    sla_risk = 10

    raw = (
        0.50 * severity +
        0.15 * sentiment +
        0.15 * wait +
        0.15 * impact +
        0.05 * sla_risk
    )

    # Hard rule: S1 severity always lands in P1 or P2
    if ex.issue.severity == "S1":
        if (ex.sentiment or 0) < -0.5 or waiting_minutes_business > 60:
            return "P1", max(raw, 80)
        return "P2", max(raw, 65)

    if raw >= 80: return "P1", raw
    if raw >= 60: return "P2", raw
    if raw >= 40: return "P3", raw
    return "P4", raw