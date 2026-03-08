from collections import defaultdict
from statistics import mean, median
from typing import Any

from rapidfuzz import fuzz


def token_set(s: str) -> set[str]:
    return set((s or "").split())


def token_overlap_ratio(a: str, b: str) -> float:
    sa = token_set(a)
    sb = token_set(b)

    if not sa or not sb:
        return 0.0

    overlap = len(sa & sb)
    base = max(len(sa), len(sb))
    return overlap / base if base else 0.0


def similar_enough(a: str, b: str, fuzzy_threshold: int = 88, overlap_threshold: float = 0.60) -> bool:
    if a == b:
        return True

    fuzzy = fuzz.token_sort_ratio(a, b)
    overlap = token_overlap_ratio(a, b)

    return fuzzy >= fuzzy_threshold or overlap >= overlap_threshold


def choose_cluster_title(canonical_tokens_list: list[str]) -> str:
    if not canonical_tokens_list:
        return "unknown cluster"

    shortest = sorted(canonical_tokens_list, key=lambda x: (len(x.split()), len(x)))[0]
    return shortest


def build_clusters(normalized_rows: list[Any]) -> list[dict]:
    buckets: list[dict] = []

    for row in normalized_rows:
        matched_bucket = None

        for bucket in buckets:
            if similar_enough(row.canonical_tokens, bucket["cluster_key"]):
                matched_bucket = bucket
                break

        if matched_bucket is None:
            matched_bucket = {
                "cluster_key": row.canonical_tokens,
                "rows": [],
            }
            buckets.append(matched_bucket)

        matched_bucket["rows"].append(row)

    results = []

    for bucket in buckets:
        rows = bucket["rows"]
        total_prices = [r.total_price for r in rows if r.total_price is not None]
        sellers = {r.seller_name for r in rows if r.seller_name}
        titles = [r.canonical_tokens for r in rows if r.canonical_tokens]

        results.append(
            {
                "cluster_key": bucket["cluster_key"],
                "cluster_title": choose_cluster_title(titles),
                "source_name": rows[0].source_name if rows else "unknown",
                "query": rows[0].query if rows else "",
                "listing_count": len(rows),
                "seller_count": len(sellers),
                "min_total_price": min(total_prices) if total_prices else None,
                "max_total_price": max(total_prices) if total_prices else None,
                "avg_total_price": round(mean(total_prices), 2) if total_prices else None,
                "median_total_price": round(median(total_prices), 2) if total_prices else None,
                "high_ticket_count": sum(1 for r in rows if r.is_high_ticket_candidate),
                "brand_risk_count": sum(1 for r in rows if r.has_brand_risk),
                "normalized_listing_ids": [r.id for r in rows],
            }
        )

    results.sort(key=lambda x: (-x["listing_count"], x["cluster_title"]))
    return results
