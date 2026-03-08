from typing import Any


SUPPLIER_FIT_BAD_TERMS = {
    "sofa",
    "wardrobe",
    "bed",
    "fridge",
    "refrigerator",
    "mattress",
    "glass",
    "mirror",
    "diesel",
    "engine",
    "bumper",
    "tyre",
    "tire",
}

SUPPLIER_FIT_GOOD_TERMS = {
    "treadmill",
    "walkingpad",
    "officechair",
    "desk",
    "storage",
    "shelf",
    "fitness",
    "ergonomic",
    "footrest",
}

RISK_TERMS = {
    "medical",
    "medicine",
    "supplement",
    "pharmaceutical",
    "baby",
    "infant",
    "weapon",
    "knife",
    "gun",
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def estimate_supplier_cost(sell_price: float | None) -> float | None:
    if sell_price is None:
        return None
    return round(sell_price * 0.42, 2)


def estimate_shipping_cost(cluster_title: str, sell_price: float | None) -> float | None:
    if sell_price is None:
        return None

    words = set(cluster_title.split())

    if {"desk", "treadmill", "officechair", "wardrobe", "sofa", "bed"} & words:
        return 20.0
    if {"storage", "shelf", "cabinet"} & words:
        return 15.0
    return 10.0


def estimate_fees(sell_price: float | None) -> float | None:
    if sell_price is None:
        return None
    return round((sell_price * 0.06) + 1.0, 2)


def demand_score(cluster: Any) -> float:
    score = (cluster.listing_count * 2.0) + (cluster.seller_count * 1.5)
    return round(clamp(score, 0.0, 10.0), 2)


def sales_signal_score(cluster: Any) -> float:
    score = (cluster.seller_count * 2.0) + min(cluster.listing_count, 3) * 1.0
    return round(clamp(score, 0.0, 10.0), 2)


def competition_score(cluster: Any) -> float:
    seller_pressure = cluster.seller_count * 1.5

    price_compression = 0.0
    if (
        cluster.min_total_price is not None
        and cluster.max_total_price is not None
        and cluster.max_total_price > 0
    ):
        spread_ratio = (cluster.max_total_price - cluster.min_total_price) / cluster.max_total_price
        if spread_ratio < 0.10:
            price_compression = 4.0
        elif spread_ratio < 0.20:
            price_compression = 2.0
        else:
            price_compression = 1.0

    score = seller_pressure + price_compression
    return round(clamp(score, 0.0, 10.0), 2)


def supplier_fit_score(cluster: Any) -> float:
    words = set(cluster.cluster_title.split())
    score = 5.0

    if words & SUPPLIER_FIT_GOOD_TERMS:
        score += 3.0
    if words & SUPPLIER_FIT_BAD_TERMS:
        score -= 4.0

    if cluster.median_total_price is not None and 120 <= cluster.median_total_price <= 600:
        score += 1.0

    return round(clamp(score, 0.0, 10.0), 2)


def risk_score(cluster: Any) -> float:
    words = set(cluster.cluster_title.split())
    score = 0.0

    score += cluster.brand_risk_count * 2.0

    if words & RISK_TERMS:
        score += 4.0

    if cluster.median_total_price is not None and cluster.median_total_price > 500:
        score += 1.0

    return round(clamp(score, 0.0, 10.0), 2)


def estimate_unit_economics(cluster: Any) -> dict[str, float | None]:
    sell_price = cluster.median_total_price
    supplier_cost = estimate_supplier_cost(sell_price)
    shipping_cost = estimate_shipping_cost(cluster.cluster_title, sell_price)
    fees = estimate_fees(sell_price)

    if None in (sell_price, supplier_cost, shipping_cost, fees):
        return {
            "sell_price_estimate": sell_price,
            "supplier_cost_estimate": supplier_cost,
            "shipping_cost_estimate": shipping_cost,
            "fees_estimate": fees,
            "gross_profit_estimate": None,
            "max_cpa": None,
        }

    gross_profit = round(sell_price - supplier_cost - shipping_cost - fees, 2)
    max_cpa = round(max(gross_profit * 0.60, 0.0), 2)

    return {
        "sell_price_estimate": sell_price,
        "supplier_cost_estimate": supplier_cost,
        "shipping_cost_estimate": shipping_cost,
        "fees_estimate": fees,
        "gross_profit_estimate": gross_profit,
        "max_cpa": max_cpa,
    }


def recommendation_from_scores(
    *,
    demand: float,
    sales_signal: float,
    competition: float,
    supplier_fit: float,
    risk: float,
    max_cpa: float | None,
) -> tuple[str, str]:
    notes = []

    if max_cpa is None:
        return "avoid", "Missing price data"

    if max_cpa >= 35:
        notes.append("strong CPA headroom")
    elif max_cpa >= 20:
        notes.append("acceptable CPA headroom")
    else:
        notes.append("weak CPA headroom")

    if competition >= 7:
        notes.append("crowded niche")
    elif competition <= 4:
        notes.append("competition looks manageable")

    if supplier_fit >= 7:
        notes.append("supplier path looks practical")
    elif supplier_fit <= 4:
        notes.append("supplier path may be awkward")

    if risk >= 5:
        notes.append("risk flags present")
    elif risk <= 2:
        notes.append("low obvious risk")

    if (
        demand >= 6
        and sales_signal >= 5
        and competition <= 6
        and supplier_fit >= 6
        and risk <= 4
        and max_cpa >= 25
    ):
        return "test", "; ".join(notes)

    if (
        demand >= 3
        and supplier_fit >= 4
        and risk <= 6
        and max_cpa >= 15
    ):
        return "watch", "; ".join(notes)

    return "avoid", "; ".join(notes)


def total_score(
    *,
    demand: float,
    sales_signal: float,
    competition: float,
    supplier_fit: float,
    risk: float,
    max_cpa: float | None,
) -> float:
    cpa_score = 0.0
    if max_cpa is not None:
        if max_cpa >= 35:
            cpa_score = 10.0
        elif max_cpa >= 25:
            cpa_score = 8.0
        elif max_cpa >= 15:
            cpa_score = 5.0
        elif max_cpa >= 5:
            cpa_score = 2.0

    score = (
        demand * 1.5
        + sales_signal * 1.5
        + supplier_fit * 1.2
        + cpa_score * 1.8
        - competition * 1.0
        - risk * 1.3
    )
    return round(score, 2)


def score_cluster(cluster: Any) -> dict[str, Any]:
    demand = demand_score(cluster)
    sales_signal = sales_signal_score(cluster)
    competition = competition_score(cluster)
    supplier_fit = supplier_fit_score(cluster)
    risk = risk_score(cluster)

    economics = estimate_unit_economics(cluster)

    recommendation, notes = recommendation_from_scores(
        demand=demand,
        sales_signal=sales_signal,
        competition=competition,
        supplier_fit=supplier_fit,
        risk=risk,
        max_cpa=economics["max_cpa"],
    )

    final_total = total_score(
        demand=demand,
        sales_signal=sales_signal,
        competition=competition,
        supplier_fit=supplier_fit,
        risk=risk,
        max_cpa=economics["max_cpa"],
    )

    return {
        "demand_score": demand,
        "sales_signal_score": sales_signal,
        "competition_score": competition,
        "supplier_fit_score": supplier_fit,
        "risk_score": risk,
        "sell_price_estimate": economics["sell_price_estimate"],
        "supplier_cost_estimate": economics["supplier_cost_estimate"],
        "shipping_cost_estimate": economics["shipping_cost_estimate"],
        "fees_estimate": economics["fees_estimate"],
        "gross_profit_estimate": economics["gross_profit_estimate"],
        "max_cpa": economics["max_cpa"],
        "total_score": final_total,
        "recommendation": recommendation,
        "notes": notes,
    }
