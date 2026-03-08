import base64
from typing import Any

import httpx

from app.config import settings


class EbayClient:
    def __init__(self) -> None:
        self.env = settings.ebay_env.lower().strip()
        self.marketplace_id = settings.ebay_marketplace_id.strip() or "EBAY_GB"

        if self.env == "sandbox":
            self.identity_base = "https://api.sandbox.ebay.com"
            self.api_base = "https://api.sandbox.ebay.com"
        else:
            self.identity_base = "https://api.ebay.com"
            self.api_base = "https://api.ebay.com"

    def has_credentials(self) -> bool:
        return bool(settings.ebay_app_id and settings.ebay_client_secret)

    def get_access_token(self) -> str:
        if not self.has_credentials():
            raise RuntimeError("Missing eBay credentials: EBAY_APP_ID and/or EBAY_CLIENT_SECRET")

        raw = f"{settings.ebay_app_id}:{settings.ebay_client_secret}".encode("utf-8")
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

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, data=data)
            response.raise_for_status()
            payload = response.json()

        token = payload.get("access_token")
        if not token:
            raise RuntimeError("eBay OAuth succeeded but no access_token was returned")

        return token

    def search_items(self, query: str, limit: int = 20) -> dict[str, Any]:
        token = self.get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
        }

        params = {
            "q": query,
            "limit": min(limit, 200),
        }

        url = f"{self.api_base}/buy/browse/v1/item_summary/search"

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()


def extract_item_summaries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload.get("itemSummaries", []) or []


def map_item_summary_to_raw_listing(item: dict[str, Any], query: str) -> dict[str, Any]:
    price_value = None
    shipping_cost = None
    currency = None

    price = item.get("price") or {}
    if price:
        try:
            price_value = float(price.get("value")) if price.get("value") is not None else None
        except (TypeError, ValueError):
            price_value = None
        currency = price.get("currency")

    shipping_options = item.get("shippingOptions") or []
    if shipping_options:
        first_shipping = shipping_options[0] or {}
        shipping_cost_obj = first_shipping.get("shippingCost") or {}
        try:
            shipping_cost = (
                float(shipping_cost_obj.get("value"))
                if shipping_cost_obj.get("value") is not None
                else None
            )
        except (TypeError, ValueError):
            shipping_cost = None

    seller = item.get("seller") or {}
    image = item.get("image") or {}

    category_path = item.get("categoryPath")
    condition = item.get("condition")
    item_web_url = item.get("itemWebUrl") or item.get("itemHref") or ""
    external_id = item.get("itemId")

    return {
        "source_name": "ebay",
        "external_id": external_id,
        "query": query,
        "title": item.get("title") or "Untitled",
        "price": price_value,
        "shipping_cost": shipping_cost,
        "currency": currency,
        "seller_name": seller.get("username"),
        "seller_url": None,
        "item_url": item_web_url,
        "image_url": image.get("imageUrl"),
        "category": category_path,
        "condition": condition,
        "is_sold_signal": False,
        "raw_payload": item,
    }


def get_demo_items(query: str) -> list[dict[str, Any]]:
    demo = [
        {
            "itemId": "demo-1001",
            "title": f"{query.title()} Electric Adjustable Desk 140cm Home Office",
            "price": {"value": "219.99", "currency": "GBP"},
            "itemWebUrl": "https://example.com/demo-adjustable-desk",
            "image": {"imageUrl": "https://example.com/demo-adjustable-desk.jpg"},
            "seller": {"username": "uk_office_store"},
            "condition": "New",
            "categoryPath": "Home, Furniture & DIY > Furniture > Desks & Computer Furniture",
            "shippingOptions": [{"shippingCost": {"value": "0.00", "currency": "GBP"}}],
        },
        {
            "itemId": "demo-1002",
            "title": f"{query.title()} Ergonomic Executive Office Chair Reclining Footrest",
            "price": {"value": "179.95", "currency": "GBP"},
            "itemWebUrl": "https://example.com/demo-office-chair",
            "image": {"imageUrl": "https://example.com/demo-office-chair.jpg"},
            "seller": {"username": "chairwarehouse_uk"},
            "condition": "New",
            "categoryPath": "Home, Furniture & DIY > Furniture > Chairs",
            "shippingOptions": [{"shippingCost": {"value": "0.00", "currency": "GBP"}}],
        },
        {
            "itemId": "demo-1003",
            "title": f"{query.title()} Walking Pad Treadmill Under Desk 2.5HP LED Remote",
            "price": {"value": "189.99", "currency": "GBP"},
            "itemWebUrl": "https://example.com/demo-walking-pad",
            "image": {"imageUrl": "https://example.com/demo-walking-pad.jpg"},
            "seller": {"username": "fitgear_uk"},
            "condition": "New",
            "categoryPath": "Sporting Goods > Fitness, Running & Yoga > Cardio Equipment",
            "shippingOptions": [{"shippingCost": {"value": "0.00", "currency": "GBP"}}],
        },
    ]
    return demo
