from __future__ import annotations

import csv
from pathlib import Path


RANKING_FIELDS = [
    "cluster_id",
    "cluster_title",
    "query",
    "listing_count",
    "seller_count",
    "median_total_price",
    "demand_score",
    "sales_signal_score",
    "competition_score",
    "supplier_fit_score",
    "risk_score",
    "sell_price_estimate",
    "supplier_cost_estimate",
    "shipping_cost_estimate",
    "fees_estimate",
    "gross_profit_estimate",
    "max_cpa",
    "visual_hook_score",
    "fragility_risk",
    "assembly_complexity",
    "confidence_score",
    "enrichment_adjustment",
    "base_total_score",
    "total_score",
    "recommendation",
    "notes",
]


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_ranked_csv(path: Path, rows: list[dict]) -> Path:
    ensure_parent_dir(path)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RANKING_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in RANKING_FIELDS})

    return path


def write_ranked_markdown(path: Path, rows: list[dict]) -> Path:
    ensure_parent_dir(path)

    lines: list[str] = []
    lines.append("# OpenClaw Ranked Products")
    lines.append("")

    if not rows:
        lines.append("_No ranked products found._")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    for idx, row in enumerate(rows, start=1):
        lines.append(f"## {idx}. {row.get('cluster_title', 'Unknown cluster')}")
        lines.append("")
        lines.append(f"- Recommendation: **{row.get('recommendation', '')}**")
        lines.append(f"- Total score: **{row.get('total_score', '')}**")
        lines.append(f"- Query: `{row.get('query', '')}`")
        lines.append(f"- Listing count: `{row.get('listing_count', '')}`")
        lines.append(f"- Seller count: `{row.get('seller_count', '')}`")
        lines.append(f"- Median total price: `{row.get('median_total_price', '')}`")
        lines.append(f"- Gross profit estimate: `{row.get('gross_profit_estimate', '')}`")
        lines.append(f"- Max CPA: `{row.get('max_cpa', '')}`")
        lines.append(f"- Demand score: `{row.get('demand_score', '')}`")
        lines.append(f"- Sales signal score: `{row.get('sales_signal_score', '')}`")
        lines.append(f"- Competition score: `{row.get('competition_score', '')}`")
        lines.append(f"- Supplier fit score: `{row.get('supplier_fit_score', '')}`")
        lines.append(f"- Risk score: `{row.get('risk_score', '')}`")
        lines.append(f"- Visual hook score: `{row.get('visual_hook_score', '')}`")
        lines.append(f"- Fragility risk: `{row.get('fragility_risk', '')}`")
        lines.append(f"- Assembly complexity: `{row.get('assembly_complexity', '')}`")
        lines.append(f"- Confidence score: `{row.get('confidence_score', '')}`")
        lines.append(f"- Enrichment adjustment: `{row.get('enrichment_adjustment', '')}`")
        lines.append(f"- Base total score: `{row.get('base_total_score', '')}`")
        lines.append(f"- Sell price estimate: `{row.get('sell_price_estimate', '')}`")
        lines.append(f"- Supplier cost estimate: `{row.get('supplier_cost_estimate', '')}`")
        lines.append(f"- Shipping cost estimate: `{row.get('shipping_cost_estimate', '')}`")
        lines.append(f"- Fees estimate: `{row.get('fees_estimate', '')}`")
        notes = row.get("notes") or ""
        lines.append(f"- Notes: {notes}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
