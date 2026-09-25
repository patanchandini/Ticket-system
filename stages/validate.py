from config import config
from models import Extraction

def check_mandatory(ex: Extraction) -> list[str]:
    mf = config.get("mandatory_fields")
    key = ex.issue.category + "_issue" if ex.issue.category else "default"
    required = mf.get(key, mf.get("default", []))
    missing = []
    for f in required:
        val = ex
        for part in f.split("."):
            val = getattr(val, part, None)
            if val is None:
                break
        if not val:
            missing.append(f)
    return missing


def generate_missing_question(missing: list[str]) -> str:
    prompts = {
        "order.id": "Could you share your order ID?",
        "contact.email": "What's the best email to reach you?",
        "evidence": "Could you attach a screenshot or link?",
        "product.sku": "Which product (SKU) is this about?",
        "customer.id": "Could you confirm your account ID?",
    }
    top = missing[:2]
    return " ".join(prompts.get(f, f"Please provide {f}.") for f in top)