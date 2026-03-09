import json

from rich import print


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def shortlist_rows(
    *,
    rows: list[dict],
    min_profit: float,
    min_cpa: float,
    min_listings: int,
    limit: int,
) -> list[dict]:
    filtered: list[dict] = []

    for row in rows:
        gross_profit = row.get("gross_profit_estimate")
        max_cpa = row.get("max_cpa")
        listing_count = row.get("listing_count") or 0

        if gross_profit is None or gross_profit < min_profit:
            continue
        if max_cpa is None or max_cpa < min_cpa:
            continue
        if listing_count < min_listings:
            continue

        filtered.append(row)

    filtered = sorted(
        filtered,
        key=lambda row: (
            -(row.get("total_score") or 0.0),
            -(row.get("gross_profit_estimate") or 0.0),
            -(row.get("listing_count") or 0),
            row.get("cluster_id") or 0,
        ),
    )[:limit]

    return filtered


def explain_row(row: dict) -> dict:
    strengths: list[str] = []
    weaknesses: list[str] = []

    listing_count = row.get("listing_count") or 0
    seller_count = row.get("seller_count") or 0
    demand_score = row.get("demand_score") or 0.0
    sales_signal_score = row.get("sales_signal_score") or 0.0
    competition_score = row.get("competition_score") or 0.0
    supplier_fit_score = row.get("supplier_fit_score") or 0.0
    risk_score = row.get("risk_score") or 0.0
    supplier_intelligence_score = row.get("supplier_intelligence_score") or 0.0
    competitor_saturation_score = row.get("competitor_saturation_score") or 0.0
    gross_profit_estimate = row.get("gross_profit_estimate")
    max_cpa = row.get("max_cpa")
    recommendation = row.get("recommendation")
    notes = row.get("notes") or ""

    if listing_count >= 3:
        strengths.append(f"good listing evidence ({listing_count} listings)")
    elif listing_count <= 1:
        weaknesses.append(f"thin listing evidence ({listing_count} listing)")

    if seller_count >= 2:
        strengths.append(f"multi-seller validation ({seller_count} sellers)")
    elif seller_count <= 1:
        weaknesses.append(f"single-seller evidence ({seller_count} seller)")

    if demand_score >= 7:
        strengths.append(f"strong demand score ({demand_score})")
    elif demand_score <= 3:
        weaknesses.append(f"weak demand score ({demand_score})")

    if sales_signal_score >= 7:
        strengths.append(f"strong sales-signal score ({sales_signal_score})")
    elif sales_signal_score <= 3:
        weaknesses.append(f"weak sales-signal score ({sales_signal_score})")

    if supplier_fit_score >= 7:
        strengths.append(f"good supplier-fit score ({supplier_fit_score})")
    elif supplier_fit_score <= 4:
        weaknesses.append(f"awkward supplier-fit score ({supplier_fit_score})")

    if risk_score <= 2:
        strengths.append(f"low risk score ({risk_score})")
    elif risk_score >= 5:
        weaknesses.append(f"elevated risk score ({risk_score})")

    if competition_score >= 7:
        weaknesses.append(f"high competition score ({competition_score})")
    elif competition_score <= 4:
        strengths.append(f"manageable competition score ({competition_score})")

    if supplier_intelligence_score >= 7:
        strengths.append(f"strong supplier intelligence ({supplier_intelligence_score})")
    elif supplier_intelligence_score <= 4:
        weaknesses.append(f"weak supplier intelligence ({supplier_intelligence_score})")

    if competitor_saturation_score >= 7:
        weaknesses.append(f"market looks saturated ({competitor_saturation_score})")
    elif competitor_saturation_score <= 4 and competitor_saturation_score > 0:
        strengths.append(f"competition may still be workable ({competitor_saturation_score})")

    if gross_profit_estimate is not None:
        if gross_profit_estimate >= 100:
            strengths.append(f"very strong gross profit (£{gross_profit_estimate})")
        elif gross_profit_estimate >= 60:
            strengths.append(f"healthy gross profit (£{gross_profit_estimate})")
        elif gross_profit_estimate < 30:
            weaknesses.append(f"weak gross profit (£{gross_profit_estimate})")

    if max_cpa is not None:
        if max_cpa >= 50:
            strengths.append(f"excellent ad headroom max CPA (£{max_cpa})")
        elif max_cpa >= 30:
            strengths.append(f"usable ad headroom max CPA (£{max_cpa})")
        elif max_cpa < 15:
            weaknesses.append(f"tight ad headroom max CPA (£{max_cpa})")

    if recommendation == "test":
        strengths.append("currently recommended for testing")
    elif recommendation == "watch":
        strengths.append("currently worth watching")
    elif recommendation == "avoid":
        weaknesses.append("currently marked avoid")

    summary_parts: list[str] = []

    if strengths:
        summary_parts.append("Strengths: " + "; ".join(strengths[:4]))
    if weaknesses:
        summary_parts.append("Weaknesses: " + "; ".join(weaknesses[:4]))
    if notes:
        summary_parts.append(f"Notes: {notes}")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "summary": " | ".join(summary_parts),
    }
