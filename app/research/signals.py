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

SUPPLIER_CATEGORY_HINTS = {
    "home",
    "office",
    "furniture",
    "fitness",
    "storage",
}

COMPACT_SUPPLIER_TERMS = {
    "officechair",
    "storage",
    "shelf",
    "walkingpad",
}

TREND_FRIENDLY_TERMS = {
    "walkingpad",
    "desk",
    "officechair",
    "storage",
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


def _join_notes(strengths: list[str], risks: list[str]) -> str:
    parts: list[str] = []
    if strengths:
        parts.append("strengths: " + "; ".join(strengths[:3]))
    if risks:
        parts.append("risks: " + "; ".join(risks[:3]))
    return " | ".join(parts)


def supplier_catalog_fit_signal(cluster: Any, enrichment: Any) -> tuple[float, list[str], list[str]]:
    words = token_words(getattr(cluster, "cluster_title", ""))
    category_hint = token_words(getattr(enrichment, "category_hint", ""))
    strengths: list[str] = []
    risks: list[str] = []
    score = 5.0

    if words & GOOD_SUPPLIER_TERMS:
        score += 2.5
        strengths.append("title matches common catalog-style goods")
    if words & BAD_SUPPLIER_TERMS:
        score -= 3.5
        risks.append("title looks bulky or awkward for supplier catalogs")
    if category_hint & SUPPLIER_CATEGORY_HINTS:
        score += 1.0
        strengths.append("enrichment category looks supplier-friendly")
    if int(getattr(cluster, "brand_risk_count", 0) or 0) > 0:
        score -= 1.0
        risks.append("brand risk reduces supplier flexibility")

    return round(clamp(score), 2), strengths, risks


def supplier_shipping_profile_signal(cluster: Any, enrichment: Any) -> tuple[float, list[str], list[str]]:
    words = token_words(getattr(cluster, "cluster_title", ""))
    fragility_risk = int(getattr(enrichment, "fragility_risk", 0) or 0)
    assembly_complexity = int(getattr(enrichment, "assembly_complexity", 0) or 0)
    strengths: list[str] = []
    risks: list[str] = []
    score = 6.0

    if words & HIGH_SHIP_COMPLEXITY_TERMS:
        score -= 2.5
        risks.append("shipping profile looks bulky or difficult")
    if words & COMPACT_SUPPLIER_TERMS:
        score += 1.0
        strengths.append("product type looks easier to warehouse and ship")
    if fragility_risk >= 6:
        score -= 1.5
        risks.append("fragility risk is elevated")
    elif fragility_risk <= 3:
        strengths.append("fragility risk looks manageable")
    if assembly_complexity >= 6:
        score -= 1.0
        risks.append("assembly complexity increases fulfillment friction")

    return round(clamp(score), 2), strengths, risks


def supplier_margin_support_signal(cluster: Any) -> tuple[float, list[str], list[str]]:
    median_price = getattr(cluster, "median_total_price", None)
    strengths: list[str] = []
    risks: list[str] = []
    score = 4.0

    if median_price is None:
        risks.append("no median price available yet")
        return score, strengths, risks

    if 140 <= median_price <= 450:
        score += 3.5
        strengths.append("price band leaves room for supplier margin")
    elif 120 <= median_price < 140 or 450 < median_price <= 600:
        score += 1.5
        strengths.append("price band may still support margin")
    elif median_price < 90:
        score -= 2.5
        risks.append("price band looks thin for paid acquisition margin")
    else:
        score -= 1.0
        risks.append("price band may be awkward for clean unit economics")

    return round(clamp(score), 2), strengths, risks


def supplier_evidence_signal(cluster: Any, supplier_terms: list[str]) -> tuple[float, list[str], list[str]]:
    listing_count = int(getattr(cluster, "listing_count", 0) or 0)
    seller_count = int(getattr(cluster, "seller_count", 0) or 0)
    strengths: list[str] = []
    risks: list[str] = []
    score = 3.5

    if supplier_terms:
        score += 2.0
        strengths.append("supplier search terms are available")
    else:
        risks.append("supplier search terms are thin")
    if seller_count >= 3:
        score += 2.0
        strengths.append("multiple sellers imply reusable supply")
    elif seller_count <= 1:
        score -= 1.5
        risks.append("single-seller evidence is weak")
    if listing_count >= 4:
        score += 1.5
        strengths.append("listing depth supports supplier lookup")
    elif listing_count <= 1:
        score -= 1.0
        risks.append("listing evidence is thin")

    return round(clamp(score), 2), strengths, risks


def supplier_confidence_signal(enrichment: Any) -> tuple[float, list[str], list[str]]:
    confidence = int(getattr(enrichment, "confidence_score", 0) or 0)
    strengths: list[str] = []
    risks: list[str] = []
    score = round(clamp(3.0 + (confidence * 0.7)), 2)

    if confidence >= 7:
        strengths.append("enrichment confidence is strong")
    elif confidence <= 3:
        risks.append("enrichment confidence is weak")

    return score, strengths, risks


def supplier_intelligence_score(cluster: Any, enrichment: Any, supplier_terms: list[str]) -> tuple[float, dict[str, Any], str]:
    catalog_score, catalog_strengths, catalog_risks = supplier_catalog_fit_signal(cluster, enrichment)
    shipping_score, shipping_strengths, shipping_risks = supplier_shipping_profile_signal(cluster, enrichment)
    margin_score, margin_strengths, margin_risks = supplier_margin_support_signal(cluster)
    evidence_score, evidence_strengths, evidence_risks = supplier_evidence_signal(cluster, supplier_terms)
    confidence_score, confidence_strengths, confidence_risks = supplier_confidence_signal(enrichment)

    final_score = round(
        clamp(
            (catalog_score * 0.30)
            + (shipping_score * 0.25)
            + (margin_score * 0.20)
            + (evidence_score * 0.15)
            + (confidence_score * 0.10)
        ),
        2,
    )

    breakdown = {
        "catalog_fit_score": catalog_score,
        "shipping_profile_score": shipping_score,
        "margin_support_score": margin_score,
        "evidence_score": evidence_score,
        "confidence_score": confidence_score,
        "strengths": (
            catalog_strengths
            + shipping_strengths
            + margin_strengths
            + evidence_strengths
            + confidence_strengths
        ),
        "risks": (
            catalog_risks
            + shipping_risks
            + margin_risks
            + evidence_risks
            + confidence_risks
        ),
    }
    notes = _join_notes(breakdown["strengths"], breakdown["risks"])
    return final_score, breakdown, notes


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


def competitor_seller_pressure_signal(cluster: Any) -> tuple[float, list[str], list[str]]:
    seller_count = int(getattr(cluster, "seller_count", 0) or 0)
    strengths: list[str] = []
    risks: list[str] = []
    score = clamp(seller_count * 2.2)

    if seller_count >= 4:
        risks.append("seller count suggests a crowded market")
    elif seller_count <= 1:
        strengths.append("seller count is still relatively light")

    return round(score, 2), strengths, risks


def competitor_listing_pressure_signal(cluster: Any) -> tuple[float, list[str], list[str]]:
    listing_count = int(getattr(cluster, "listing_count", 0) or 0)
    strengths: list[str] = []
    risks: list[str] = []
    score = clamp(min(listing_count, 6) * 1.5)

    if listing_count >= 5:
        risks.append("listing volume suggests crowded discovery pages")
    elif listing_count <= 2:
        strengths.append("listing volume is not saturated yet")

    return round(score, 2), strengths, risks


def competitor_price_pressure_signal(cluster: Any) -> tuple[float, list[str], list[str]]:
    min_price = getattr(cluster, "min_total_price", None)
    max_price = getattr(cluster, "max_total_price", None)
    strengths: list[str] = []
    risks: list[str] = []
    score = 4.0

    if min_price is None or max_price is None or max_price <= 0:
        return score, strengths, risks

    spread_ratio = (max_price - min_price) / max_price
    if spread_ratio < 0.10:
        score += 4.0
        risks.append("tight price spread suggests commoditisation")
    elif spread_ratio < 0.20:
        score += 2.0
        risks.append("moderate price compression is visible")
    else:
        score -= 1.0
        strengths.append("wider spread leaves room for positioning")

    return round(clamp(score), 2), strengths, risks


def competitor_market_maturity_signal(cluster: Any) -> tuple[float, list[str], list[str]]:
    seller_count = int(getattr(cluster, "seller_count", 0) or 0)
    listing_count = int(getattr(cluster, "listing_count", 0) or 0)
    strengths: list[str] = []
    risks: list[str] = []
    score = 3.5

    if seller_count >= 3 and listing_count >= 4:
        score += 3.0
        risks.append("market looks established rather than early")
    elif seller_count <= 1 and listing_count <= 2:
        score -= 1.5
        strengths.append("market may still be early enough to test")

    return round(clamp(score), 2), strengths, risks


def competitor_saturation_score(cluster: Any) -> tuple[float, dict[str, Any], str]:
    seller_score, seller_strengths, seller_risks = competitor_seller_pressure_signal(cluster)
    listing_score, listing_strengths, listing_risks = competitor_listing_pressure_signal(cluster)
    price_score, price_strengths, price_risks = competitor_price_pressure_signal(cluster)
    maturity_score, maturity_strengths, maturity_risks = competitor_market_maturity_signal(cluster)

    final_score = round(
        clamp(
            (seller_score * 0.35)
            + (listing_score * 0.25)
            + (price_score * 0.25)
            + (maturity_score * 0.15)
        ),
        2,
    )

    breakdown = {
        "seller_pressure_score": seller_score,
        "listing_pressure_score": listing_score,
        "price_pressure_score": price_score,
        "market_maturity_score": maturity_score,
        "strengths": seller_strengths + listing_strengths + price_strengths + maturity_strengths,
        "risks": seller_risks + listing_risks + price_risks + maturity_risks,
    }
    notes = _join_notes(breakdown["strengths"], breakdown["risks"])
    return final_score, breakdown, notes


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

    if words & TREND_FRIENDLY_TERMS:
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
    active_enrichment = enrichment or object()
    supplier_terms = safe_json_list(getattr(active_enrichment, "supplier_search_terms_json", None))

    supplier_score, supplier_breakdown, supplier_notes = supplier_intelligence_score(
        cluster,
        active_enrichment,
        supplier_terms,
    )
    ad_score_value, ad_notes = ad_signal_score(cluster, active_enrichment)
    competitor_score, competitor_breakdown, competitor_notes = competitor_saturation_score(cluster)
    multi_market_value, multi_notes = multi_market_score(cluster, active_enrichment)
    trend_value, trend_notes = trend_score(cluster, active_enrichment)
    handling_complexity = handling_complexity_score(cluster, active_enrichment)

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
        "supplier_breakdown": supplier_breakdown,
        "supplier_notes": supplier_notes,
        "ad_notes": "; ".join(ad_notes),
        "competitor_breakdown": competitor_breakdown,
        "competitor_notes": competitor_notes,
        "trend_notes": "; ".join(trend_notes + multi_notes),
        "score_adjustment": score_adjustment,
    }
