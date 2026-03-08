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


def _demo_item(
    *,
    item_id: str,
    title: str,
    price: str,
    seller: str,
    category: str,
    shipping: str = "0.00",
) -> dict[str, Any]:
    slug = item_id.lower()
    return {
        "itemId": item_id,
        "title": title,
        "price": {"value": price, "currency": "GBP"},
        "itemWebUrl": f"https://example.com/{slug}",
        "image": {"imageUrl": f"https://example.com/{slug}.jpg"},
        "seller": {"username": seller},
        "condition": "New",
        "categoryPath": category,
        "shippingOptions": [{"shippingCost": {"value": shipping, "currency": "GBP"}}],
    }


def _walking_pad_demo_items() -> list[dict[str, Any]]:
    category = "Sporting Goods > Fitness, Running & Yoga > Cardio Equipment"

    return [
        _demo_item(
            item_id="demo-wp-1001",
            title="Under Desk Walking Pad Treadmill 2.5HP Remote LED Display",
            price="189.99",
            seller="fitgear_uk",
            category=category,
        ),
        _demo_item(
            item_id="demo-wp-1002",
            title="Walking Pad Treadmill Under Desk 2.5HP Remote Control",
            price="199.99",
            seller="homefit_direct",
            category=category,
        ),
        _demo_item(
            item_id="demo-wp-1003",
            title="Compact Walking Pad Under Desk Treadmill 1-6kmh",
            price="184.99",
            seller="uk_cardio_store",
            category=category,
        ),
        _demo_item(
            item_id="demo-wp-2001",
            title="Incline Walking Pad Treadmill Foldable 2 in 1 Home Office",
            price="229.99",
            seller="fitgear_uk",
            category=category,
        ),
        _demo_item(
            item_id="demo-wp-2002",
            title="2 in 1 Foldable Walking Pad Treadmill with Incline",
            price="239.99",
            seller="cardiohub_uk",
            category=category,
        ),
        _demo_item(
            item_id="demo-wp-3001",
            title="Slim Walking Pad Treadmill Portable Under Desk Quiet Motor",
            price="169.99",
            seller="motionliving",
            category=category,
        ),
    ]


def _standing_desk_demo_items() -> list[dict[str, Any]]:
    category = "Home, Furniture & DIY > Furniture > Desks & Computer Furniture"

    return [
        _demo_item(
            item_id="demo-sd-1001",
            title="Electric Standing Desk 140cm Height Adjustable Home Office",
            price="219.99",
            seller="uk_office_store",
            category=category,
        ),
        _demo_item(
            item_id="demo-sd-1002",
            title="140cm Sit Stand Desk Electric Adjustable Computer Table",
            price="229.99",
            seller="ergodesk_uk",
            category=category,
        ),
        _demo_item(
            item_id="demo-sd-1003",
            title="Height Adjustable Standing Desk 120cm Electric Workstation",
            price="199.99",
            seller="uk_office_store",
            category=category,
        ),
        _demo_item(
            item_id="demo-sd-2001",
            title="L Shaped Standing Desk Electric Adjustable Corner Desk",
            price="289.99",
            seller="workspace_plus",
            category=category,
        ),
        _demo_item(
            item_id="demo-sd-2002",
            title="Corner Sit Stand Desk Electric L Shape Home Office",
            price="309.99",
            seller="workspace_plus",
            category=category,
        ),
    ]


def _office_chair_demo_items() -> list[dict[str, Any]]:
    category = "Home, Furniture & DIY > Furniture > Chairs"

    return [
        _demo_item(
            item_id="demo-oc-1001",
            title="Ergonomic Office Chair Reclining High Back Footrest",
            price="179.95",
            seller="chairwarehouse_uk",
            category=category,
        ),
        _demo_item(
            item_id="demo-oc-1002",
            title="Executive Office Chair Ergonomic Recliner with Footrest",
            price="189.95",
            seller="chairwarehouse_uk",
            category=category,
        ),
        _demo_item(
            item_id="demo-oc-1003",
            title="Mesh Ergonomic Office Chair Adjustable Headrest Footrest",
            price="169.99",
            seller="workseat_direct",
            category=category,
        ),
        _demo_item(
            item_id="demo-oc-2001",
            title="Heavy Duty Executive Office Chair Wide Seat Reclining",
            price="209.99",
            seller="deskcomfort",
            category=category,
        ),
    ]


def _generic_demo_items(query: str) -> list[dict[str, Any]]:
    category = "Home, Furniture & DIY > Furniture > Other Furniture"

    clean_query = " ".join(query.strip().split()) or "storage cabinet"
    title_base = clean_query.title()

    return [
        _demo_item(
            item_id="demo-generic-1001",
            title=f"{title_base} Large Storage Unit",
            price="149.99",
            seller="demo_store_one",
            category=category,
        ),
        _demo_item(
            item_id="demo-generic-1002",
            title=f"{title_base} Premium Home Organizer",
            price="159.99",
            seller="demo_store_two",
            category=category,
        ),
        _demo_item(
            item_id="demo-generic-1003",
            title=f"{title_base} Heavy Duty Storage Cabinet",
            price="179.99",
            seller="demo_store_three",
            category=category,
        ),
    ]


def get_demo_items(query: str) -> list[dict[str, Any]]:
    q = " ".join((query or "").strip().lower().split())

    if "walking pad" in q or "walkingpad" in q or "treadmill" in q:
        return _walking_pad_demo_items()

    if "standing desk" in q or "sit stand desk" in q or "adjustable desk" in q or q == "desk":
        return _standing_desk_demo_items()

    if "office chair" in q or "chair" in q:
        return _office_chair_demo_items()

    return _generic_demo_items(query)
