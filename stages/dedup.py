import hashlib

def fingerprint(ex) -> str:
    key = f"{ex.customer.id}|{ex.product.sku}|{ex.issue.category}|{ex.issue.description[:80]}"
    return hashlib.sha256(key.encode()).hexdigest()