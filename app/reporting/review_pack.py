from __future__ import annotations

import csv
import re
from pathlib import Path

from app.reporting.rankings import ensure_parent_dir


REVIEW_PACK_FIELDS = [
    "cluster_id",
    "cluster_title",
    "source_name",
    "query",
    "recommendation",
    "total_score",
    "gross_profit_estimate",
    "max_cpa",
    "listing_count",
    "seller_count",
    "median_total_price",
    "supplier_intelligence_score",
    "supplier_catalog_fit_score",
    "supplier_shipping_profile_score",
    "supplier_margin_support_score",
    "supplier_evidence_score",
    "competitor_saturation_score",
    "competitor_seller_pressure_score",
    "competitor_listing_pressure_score",
    "competitor_price_pressure_score",
    "trend_score",
    "market_snapshots",
    "series_status",
    "score_coverage_status",
    "listing_count_delta",
    "seller_count_delta",
    "median_price_delta",
    "supply_stability_score",
    "recommendation_change",
    "supplier_search_query",
    "supplier_notes",
    "competitor_notes",
    "trend_notes",
    "notes",
    "review_summary",
]


def slugify(value: str | None, fallback: str = "all") -> str:
    text = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return text or fallback


def build_review_summary(row: dict) -> str:
    parts: list[str] = []

    recommendation = row.get("recommendation")
    if recommendation:
        parts.append(f"recommendation={recommendation}")

    gross_profit = row.get("gross_profit_estimate")
    if gross_profit is not None:
        parts.append(f"gross_profit={gross_profit}")

    max_cpa = row.get("max_cpa")
    if max_cpa is not None:
        parts.append(f"max_cpa={max_cpa}")

    supplier_score = row.get("supplier_intelligence_score")
    if supplier_score is not None:
        parts.append(f"supplier={supplier_score}")

    competitor_score = row.get("competitor_saturation_score")
    if competitor_score is not None:
        parts.append(f"competition={competitor_score}")

    series_status = row.get("series_status")
    if series_status:
        parts.append(f"series={series_status}")

    recommendation_change = row.get("recommendation_change")
    if recommendation_change:
        parts.append(f"change={recommendation_change}")

    return " | ".join(parts)


def build_review_pack_rows(rows: list[dict], trend_rows: list[dict]) -> list[dict]:
    trend_map = {row["cluster_id"]: row for row in trend_rows}
    results: list[dict] = []

    for row in rows:
        trend_row = trend_map.get(row["cluster_id"], {})
        combined = {**row, **trend_row}
        combined["review_summary"] = build_review_summary(combined)
        results.append(combined)

    return results


def write_review_pack_csv(path: Path, rows: list[dict]) -> Path:
    ensure_parent_dir(path)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_PACK_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in REVIEW_PACK_FIELDS})

    return path


def write_review_pack_markdown(path: Path, rows: list[dict]) -> Path:
    ensure_parent_dir(path)

    lines: list[str] = ["# OpenClaw Review Pack", ""]

    if not rows:
        lines.append("_No review-pack rows found._")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    for index, row in enumerate(rows, start=1):
        lines.append(f"## {index}. {row.get('cluster_title', 'Unknown cluster')}")
        lines.append("")
        lines.append(f"- Source: `{row.get('source_name', '')}`")
        lines.append(f"- Query: `{row.get('query', '')}`")
        lines.append(f"- Recommendation: **{row.get('recommendation', '')}**")
        lines.append(f"- Total score: `{row.get('total_score', '')}`")
        lines.append(f"- Gross profit estimate: `{row.get('gross_profit_estimate', '')}`")
        lines.append(f"- Max CPA: `{row.get('max_cpa', '')}`")
        lines.append(f"- Supplier intelligence score: `{row.get('supplier_intelligence_score', '')}`")
        lines.append(f"- Competitor saturation score: `{row.get('competitor_saturation_score', '')}`")
        lines.append(f"- Trend score: `{row.get('trend_score', '')}`")
        lines.append(f"- Market snapshots: `{row.get('market_snapshots', '')}`")
        lines.append(f"- Series status: `{row.get('series_status', '')}`")
        lines.append(f"- Score coverage status: `{row.get('score_coverage_status', '')}`")
        lines.append(f"- Listing delta: `{row.get('listing_count_delta', '')}`")
        lines.append(f"- Median price delta: `{row.get('median_price_delta', '')}`")
        lines.append(f"- Recommendation change: `{row.get('recommendation_change', '')}`")
        lines.append(f"- Review summary: {row.get('review_summary', '')}")
        lines.append(f"- Supplier notes: {row.get('supplier_notes') or ''}")
        lines.append(f"- Competitor notes: {row.get('competitor_notes') or ''}")
        lines.append(f"- Trend notes: {row.get('trend_notes') or ''}")
        lines.append(f"- Notes: {row.get('notes') or ''}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
