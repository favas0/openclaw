from __future__ import annotations

import json
from typing import Any


HIGH_SHIP_COMPLEXITY_TERMS = {
    "sofa",
    "wardrobe",
    "bed",
    "mattress",
    "glass",
    "mirror",
    "treadmill",
    "desk",
}

GOOD_SUPPLIER_TERMS = {
    "desk",
    "walkingpad",
    "treadmill",
    "officechair",
    "storage",
    "shelf",
    "fitness",
}

BAD_SUPPLIER_TERMS = {
    "sofa",
    "wardrobe",
    "bed",
    "mattress",
    "fridge",
    "glass",
    "mirror",
    "engine",
    "bumper",
}


def clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))



def token_words(text: str | None) -> set[str]:
    return set((text or "").lower().split())



def safe_json_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        try:
            raw = json.loads(value)
            if isinstance(raw, list):
                return [str(x).strip() for x in raw if str(x).strip()]
        except Exception:
            pass
    return []



def build_supplier_query(cluster_title: str, supplier_terms: list[str]) -> str:
    parts: list[str] = []
    if cluster_title:
        parts.append(cluster_title)
    for term in supplier_terms:
        if term.lower() not in {p.lower() for p in parts}:
            parts.append(term)
    parts.extend(["uk warehouse", "dropship", "wholesale"])
    return " ".join(parts[:8])



def supplier_intelligence_score(cluster: Any, supplier_terms: list[str]) -> tuple[float, list[str]]:
    words = token_words(getattr(cluster, "cluster_title", ""))
    notes: list[str] = []
    score = 5.0

    if words & GOOD_SUPPLIER_TERMS:
        score += 2.0
        notes.append("title fits common catalog-style goods")
    if words & BAD_SUPPLIER_TERMS:
        score -= 3.0
        notes.append("bulky or awkward supplier profile")
    if supplier_terms:
        score += 1.0
        notes.append("supplier search terms available")
    if getattr(cluster, "seller_count", 0) >= 3:
        score += 1.0
        notes.append("multiple live sellers suggest supplier availability")
    if getattr(cluster, "median_total_price", None) and getattr(cluster, "median_total_price") >= 150:
        score += 0.5
        notes.append("price point can support supplier margin")

    return round(clamp(score), 2), notes



def ad_signal_score(cluster: Any, enrichment: Any) -> tuple[float, list[str]]:
    notes: list[str] = []
    score = 4.0

    visual_hook_score = int(getattr(enrichment, "visual_hook_score", 0) or 0)
    buyer_intent = (getattr(enrichment, "buyer_intent", "") or "").lower()
    listing_count = int(getattr(cluster, "listing_count", 0) or 0)

    score += visual_hook_score * 0.35
    if visual_hook_score >= 7:
        notes.append("strong visual hook for creative testing")
    if any(term in buyer_intent for term in ["impulse", "pain point", "gift", "home office", "fitness"]):
        score += 1.0
        notes.append("buyer intent looks ad-friendly")
    if listing_count >= 3:
        score += 0.75
        notes.append("enough listing volume for ad validation")

    return round(clamp(score), 2), notes



def competitor_saturation_score(cluster: Any) -> tuple[float, list[str]]:
    seller_count = int(getattr(cluster, "seller_count", 0) or 0)
    listing_count = int(getattr(cluster, "listing_count", 0) or 0)
    min_price = getattr(cluster, "min_total_price", None)
    max_price = getattr(cluster, "max_total_price", None)

    notes: list[str] = []
    score = seller_count * 1.6 + min(listing_count, 5) * 0.8

    if min_price is not None and max_price is not None and max_price > 0:
        spread_ratio = (max_price - min_price) / max_price
        if spread_ratio < 0.10:
            score += 2.0
            notes.append("tight price spread suggests commoditisation")
        elif spread_ratio < 0.20:
            score += 1.0
            notes.append("moderate price compression")
        else:
            notes.append("pricing still has room for positioning")

    if seller_count >= 4:
        notes.append("seller count suggests crowded auction/store presence")
    elif seller_count <= 1:
        notes.append("not obviously saturated yet")

    return round(clamp(score), 2), notes



def multi_market_score(cluster: Any, enrichment: Any) -> tuple[float, list[str]]:
    words = token_words(getattr(cluster, "cluster_title", ""))
    category_hint = (getattr(enrichment, "category_hint", "") or "").lower()
    notes: list[str] = []
    score = 4.0

    if words & {"desk", "officechair", "storage", "shelf", "fitness", "walkingpad", "treadmill"}:
        score += 2.0
        notes.append("category likely appears across several marketplaces")
    if any(term in category_hint for term in ["home", "fitness", "office", "furniture"]):
        score += 1.5
        notes.append("category hint is broad enough for cross-market lookup")
    if int(getattr(cluster, "listing_count", 0) or 0) >= 3:
        score += 0.5
        notes.append("base eBay evidence is strong enough to justify expansion")

    return round(clamp(score), 2), notes



def trend_score(cluster: Any, enrichment: Any) -> tuple[float, list[str]]:
    words = token_words(getattr(cluster, "cluster_title", ""))
    notes: list[str] = []
    score = 4.0

    if words & {"walkingpad", "desk", "officechair", "storage"}:
        score += 2.0
        notes.append("fits repeat-purchase or evergreen home/office demand")
    if int(getattr(enrichment, "confidence_score", 0) or 0) >= 7:
        score += 1.0
        notes.append("AI enrichment confidence is high")
    if int(getattr(cluster, "listing_count", 0) or 0) >= 4:
        score += 1.0
        notes.append("listing depth is decent for future monitoring")

    return round(clamp(score), 2), notes



def handling_complexity_score(cluster: Any, enrichment: Any) -> float:
    words = token_words(getattr(cluster, "cluster_title", ""))
    score = float(int(getattr(enrichment, "assembly_complexity", 0) or 0))
    if words & HIGH_SHIP_COMPLEXITY_TERMS:
        score += 2.0
    return round(clamp(score), 2)



def build_research_signal(cluster: Any, enrichment: Any | None) -> dict[str, Any]:
    supplier_terms = safe_json_list(getattr(enrichment, "supplier_search_terms_json", None))

    supplier_score, supplier_notes = supplier_intelligence_score(cluster, supplier_terms)
    ad_score_value, ad_notes = ad_signal_score(cluster, enrichment or object())
    competitor_score, competitor_notes = competitor_saturation_score(cluster)
    multi_market_value, multi_notes = multi_market_score(cluster, enrichment or object())
    trend_value, trend_notes = trend_score(cluster, enrichment or object())
    handling_complexity = handling_complexity_score(cluster, enrichment or object())

    score_adjustment = round(
        (supplier_score * 0.30)
        + (ad_score_value * 0.25)
        + (multi_market_value * 0.20)
        + (trend_value * 0.20)
        - (competitor_score * 0.25)
        - (handling_complexity * 0.15),
        2,
    )

    return {
        "supplier_intelligence_score": supplier_score,
        "ad_signal_score": ad_score_value,
        "competitor_saturation_score": competitor_score,
        "multi_market_score": multi_market_value,
        "trend_score": trend_value,
        "handling_complexity_score": handling_complexity,
        "supplier_search_query": build_supplier_query(getattr(cluster, "cluster_title", ""), supplier_terms),
        "supplier_terms": supplier_terms,
        "supplier_notes": "; ".join(supplier_notes),
        "ad_notes": "; ".join(ad_notes),
        "competitor_notes": "; ".join(competitor_notes),
        "trend_notes": "; ".join(trend_notes + multi_notes),
        "score_adjustment": score_adjustment,
    }
