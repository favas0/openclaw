from __future__ import annotations

import json
from typing import Any

from app.llm.ollama_client import OllamaClient


class ClusterEnricher:
    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        self.ollama = ollama_client or OllamaClient()

    def build_prompt(
        self,
        cluster_title: str,
        median_price: float | None,
        seller_count: int | None,
        listing_count: int | None,
        sample_titles: list[str],
    ) -> str:
        sample_block = "\n".join(f"- {title}" for title in sample_titles[:5]) if sample_titles else "- none"

        return f"""
You are extracting structured product intelligence for a UK high-ticket dropshipping research system.

Return JSON only.

You must identify the most specific practical product type being sold.
Do not use broad labels like:
- furniture
- equipment
- appliance
- fitness
- office
- home
unless the titles genuinely do not support anything more specific.

Prefer outputs like:
- folding treadmill
- electric standing desk
- massage chair
- outdoor storage shed
- adjustable weight bench

Rules:
- Do not include markdown
- Do not include explanations
- All scores must be integers from 0 to 10
- supplier_search_terms must be a JSON array of short realistic supplier lookup phrases
- attributes must be a JSON object with concise product attributes
- confidence_score must be an integer from 0 to 10
- product_type must be specific and commercially useful
- category_hint should be a realistic supplier/store category
- buyer_intent should be a short commercial use-case phrase, not a generic verb

Guidance:
- product_type: specific product being sold
- category_hint: broader retail/supplier category
- buyer_intent: why someone buys it
- supplier_search_terms: phrases a human would search on AliExpress, CJ Dropshipping, Alibaba, or UK wholesale sites
- attributes: only include attributes that are likely supported by the titles

Input:
cluster_title: {cluster_title}
median_price: {median_price}
seller_count: {seller_count}
listing_count: {listing_count}
sample_titles:
{sample_block}

Return exactly this JSON schema:
{{
  "product_type": "string",
  "category_hint": "string",
  "attributes": {{
    "material": "string",
    "size": "string",
    "power": "string",
    "foldable": "string",
    "adjustable": "string"
  }},
  "buyer_intent": "string",
  "visual_hook_score": 0,
  "fragility_risk": 0,
  "assembly_complexity": 0,
  "supplier_search_terms": ["string"],
  "confidence_score": 0
}}
""".strip()

    def validate_result(self, data: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "product_type": self._clean_text(data.get("product_type")),
            "category_hint": self._clean_text(data.get("category_hint")),
            "attributes": data.get("attributes") if isinstance(data.get("attributes"), dict) else {},
            "buyer_intent": self._clean_text(data.get("buyer_intent")),
            "visual_hook_score": self._clamp_score(data.get("visual_hook_score")),
            "fragility_risk": self._clamp_score(data.get("fragility_risk")),
            "assembly_complexity": self._clamp_score(data.get("assembly_complexity")),
            "supplier_search_terms": self._validate_terms(data.get("supplier_search_terms")),
            "confidence_score": self._clamp_score(data.get("confidence_score")),
        }
        return result

    def enrich_cluster(
        self,
        cluster_title: str,
        median_price: float | None,
        seller_count: int | None,
        listing_count: int | None,
        sample_titles: list[str],
    ) -> dict[str, Any]:
        prompt = self.build_prompt(
            cluster_title=cluster_title,
            median_price=median_price,
            seller_count=seller_count,
            listing_count=listing_count,
            sample_titles=sample_titles,
        )
        raw = self.ollama.generate_json(prompt)
        return self.validate_result(raw)

    @staticmethod
    def _clamp_score(value: Any) -> int:
        try:
            n = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(10, n))

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _validate_terms(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned: list[str] = []
        seen: set[str] = set()

        for item in value:
            text = str(item).strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(text)

        return cleaned[:10]

    @staticmethod
    def to_json_text(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
