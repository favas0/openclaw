from app.db.models import RawListing
from app.normalize.titles import (
    canonical_title_from_tokens,
    detect_brand_risk,
    normalize_title,
    tokenize_title,
)


def compute_total_price(price: float | None, shipping_cost: float | None) -> float | None:
    if price is None and shipping_cost is None:
        return None
    return float(price or 0.0) + float(shipping_cost or 0.0)


def is_high_ticket_candidate(total_price: float | None) -> bool:
    if total_price is None:
        return False
    return 120.0 <= total_price <= 600.0


def normalize_raw_listing(raw: RawListing) -> dict:
    normalized_title = normalize_title(raw.title)
    tokens = tokenize_title(raw.title)
    canonical_tokens = canonical_title_from_tokens(tokens)
    total_price = compute_total_price(raw.price, raw.shipping_cost)
    brand_risk = detect_brand_risk(raw.title)
    high_ticket = is_high_ticket_candidate(total_price)

    return {
        "raw_listing_id": raw.id,
        "source_name": raw.source_name,
        "query": raw.query,
        "original_title": raw.title,
        "normalized_title": normalized_title,
        "canonical_tokens": canonical_tokens,
        "price": raw.price,
        "shipping_cost": raw.shipping_cost,
        "total_price": total_price,
        "currency": raw.currency,
        "seller_name": raw.seller_name,
        "category": raw.category,
        "condition": raw.condition,
        "token_count": len(tokens),
        "has_brand_risk": brand_risk,
        "is_high_ticket_candidate": high_ticket,
    }
