import re
from models import Extraction, Customer, Order, Product, Issue, Contact, Evidence

ORDER_RE = re.compile(r"#?(\d{6,})")
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_RE = re.compile(r"\+?\d[\d\s-]{7,}\d")
SKU_RE = re.compile(r"\b[A-Z]{2,}-[A-Z0-9]+\b")

CRM = {
    "4821": {"status": "delivered", "value": 750.0, "tier": "gold", "sku": "WP-X2"},
}

def extract(segment: dict) -> Extraction:
    text = " ".join(t["text"] for t in segment["turns"] if t["speaker"] == "customer")
    low = text.lower()
    ex = Extraction()

    # Customer
    ex.customer.id = "C-UNKNOWN"
    ex.customer.tier = "standard"

    # Order
    m = ORDER_RE.search(text)
    if m:
        oid = m.group(1)
        ex.order.id = oid
        if oid in CRM:
            ex.order.status = CRM[oid]["status"]
            ex.order.value = CRM[oid]["value"]
            ex.customer.tier = CRM[oid]["tier"]

    # Product
    m = SKU_RE.search(text)
    if m:
        ex.product.sku = m.group(0)

    # Contact
    m = EMAIL_RE.search(text)
    if m:
        ex.contact.email = m.group(0)
    m = PHONE_RE.search(text)
    if m:
        ex.contact.phone = m.group(0)

    # Issue category + severity
    if any(w in low for w in ["charge", "refund", "billing", "invoice"]):
        ex.issue.category, ex.issue.severity = "billing", "S2"
    elif any(w in low for w in ["deliver", "ship", "tracking"]):
        ex.issue.category, ex.issue.severity = "delivery", "S3"
    elif any(w in low for w in ["broken", "defect", "damaged"]):
        ex.issue.category, ex.issue.severity = "product_defect", "S2"
    else:
        ex.issue.category, ex.issue.severity = "account", "S4"
    ex.issue.description = text[:500]

    # Evidence
    if m := re.search(r"(https?://\S+)", text):
        ex.evidence.append(Evidence(type="link", ref=m.group(0)))
    if "screenshot" in low:
        ex.evidence.append(Evidence(type="screenshot", ref="attached"))

    # Sentiment (simple)
    neg = sum(w in low for w in ["angry", "frustrated", "terrible", "worst", "unacceptable"])
    pos = sum(w in low for w in ["thanks", "great", "happy", "appreciate"])
    ex.sentiment = max(-1.0, min(1.0, (pos - neg) / 3.0))

    ex.confidence = {"order": 0.9 if ex.order.id else 0.0,
                     "contact": 0.9 if (ex.contact.email or ex.contact.phone) else 0.0,
                     "category": 0.85}
    return ex