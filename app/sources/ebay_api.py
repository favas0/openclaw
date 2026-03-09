import base64
from typing import Any

import httpx

from app.config import settings


def _parse_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _response_detail(response: httpx.Response) -> str:
    body = response.text.strip()
    if not body:
        return f"status={response.status_code}"
    return f"status={response.status_code} body={body[:500]}"


class EbayBrowseApiClient:
    def __init__(self) -> None:
        self.env = settings.ebay_env.lower().strip()
        self.default_marketplace_id = settings.ebay_marketplace_id.strip() or "EBAY_GB"

        if self.env == "sandbox":
            self.identity_base = "https://api.sandbox.ebay.com"
            self.api_base = "https://api.sandbox.ebay.com"
        else:
            self.identity_base = "https://api.ebay.com"
            self.api_base = "https://api.ebay.com"

    def resolve_marketplace_id(self, marketplace_id: str | None = None) -> str:
        value = (marketplace_id or self.default_marketplace_id or "EBAY_GB").strip()
        return value or "EBAY_GB"

    def has_credentials(self) -> bool:
        return bool(settings.ebay_client_id and settings.ebay_client_secret)

    def get_app_token(self) -> str:
        if not self.has_credentials():
            raise RuntimeError("Missing eBay credentials: EBAY_CLIENT_ID/EBAY_APP_ID and/or EBAY_CLIENT_SECRET/EBAY_CERT_ID")

        raw = f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode("utf-8")
        auth_b64 = base64.b64encode(raw).decode("utf-8")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_b64}",
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }
        url = f"{self.identity_base}/identity/v1/oauth2/token"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, data=data)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"eBay OAuth failed: {_response_detail(exc.response)}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"eBay OAuth request failed: {exc}") from exc

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("eBay OAuth succeeded but no access_token was returned")
        return token

    def search_items(
        self,
        query: str,
        limit: int = 20,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        token = self.get_app_token()
        active_marketplace_id = self.resolve_marketplace_id(marketplace_id)

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": active_marketplace_id,
        }
        params = {
            "q": query,
            "limit": min(limit, 200),
        }
        url = f"{self.api_base}/buy/browse/v1/item_summary/search"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"eBay Browse API search failed: {_response_detail(exc.response)}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"eBay Browse API request failed: {exc}") from exc

        return response.json()


def extract_item_summaries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload.get("itemSummaries", []) or []


def map_api_item_to_raw_listing(
    item: dict[str, Any],
    query: str,
    marketplace_id: str = "EBAY_GB",
) -> dict[str, Any]:
    price = item.get("price") or {}
    shipping_options = item.get("shippingOptions") or []
    first_shipping = shipping_options[0] if shipping_options else {}
    shipping_cost_obj = (first_shipping or {}).get("shippingCost") or {}
    seller = item.get("seller") or {}
    image = item.get("image") or {}

    return {
        "source_name": "ebay",
        "external_id": item.get("itemId"),
        "query": query,
        "title": item.get("title") or "Untitled",
        "price": _parse_float(price.get("value")),
        "shipping_cost": _parse_float(shipping_cost_obj.get("value")),
        "currency": price.get("currency") or shipping_cost_obj.get("currency"),
        "seller_name": seller.get("username"),
        "seller_url": None,
        "item_url": item.get("itemWebUrl") or item.get("itemHref") or "",
        "image_url": image.get("imageUrl"),
        "category": item.get("categoryPath"),
        "condition": item.get("condition"),
        "is_sold_signal": False,
        "raw_payload": {
            "provider": "ebay_browse_api",
            "marketplace_id": marketplace_id,
            "query": query,
            "item": item,
        },
    }
