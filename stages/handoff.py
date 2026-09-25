def mask_name(name: str | None) -> str:
    if not name: return "N/A"
    parts = name.split()
    return " ".join(p[0] + "***" for p in parts)

def mask_email(e: str | None) -> str:
    if not e or "@" not in e: return "N/A"
    local, dom = e.split("@", 1)
    return f"{local[0]}***@{dom}"

def mask_phone(p: str | None) -> str:
    if not p: return "N/A"
    return "***" + p[-4:]

def mask_order(o: str | None) -> str:
    return "***" + o[-4:] if o else "N/A"

def build_summary(ticket: dict) -> str:
    c = ticket["customer"]; o = ticket["order"]; i = ticket["issue"]
    sla = ticket["sla"]
    pct = int(100 * sla["elapsed_minutes"] / max(sla["allowed_minutes"], 1))
    warn = " ⚠️" if pct >= 75 else ""
    return (
        f"Ticket {ticket['ticket_id']} | {ticket['priority']} | {i['category']}\n"
        f"Customer: {mask_name(c.get('name'))} (Tier: {c.get('tier')})\n"
        f"Order: {mask_order(o.get('id'))} | Value: {o.get('value')}\n"
        f"Product: {ticket['product'].get('sku')}\n"
        f"Issue: {i.get('description','')[:200]}\n"
        f"Sentiment: {ticket.get('sentiment')}\n"
        f"SLA: {pct}% consumed{warn}\n"
    )