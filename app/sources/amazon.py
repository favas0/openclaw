from typing import Any


def _parse_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def map_demo_item_to_raw_listing(item: dict[str, Any], query: str) -> dict[str, Any]:
    price = item.get("price") or {}
    seller = item.get("seller") or {}
    shipping = item.get("shipping") or {}
    image = item.get("image") or {}

    return {
        "source_name": "amazon",
        "external_id": item.get("asin"),
        "query": query,
        "title": item.get("title") or "Untitled",
        "price": _parse_float(price.get("value")),
        "shipping_cost": _parse_float(shipping.get("value")),
        "currency": price.get("currency") or shipping.get("currency"),
        "seller_name": seller.get("name"),
        "seller_url": seller.get("url"),
        "item_url": item.get("productUrl") or "",
        "image_url": image.get("url"),
        "category": item.get("department"),
        "condition": item.get("condition") or "New",
        "is_sold_signal": False,
        "raw_payload": {
            "provider": "amazon_demo",
            "query": query,
            "item": item,
        },
    }


def _demo_item(
    *,
    asin: str,
    title: str,
    price: str,
    seller_name: str,
    department: str,
    shipping: str = "0.00",
) -> dict[str, Any]:
    slug = asin.lower()
    return {
        "asin": asin,
        "title": title,
        "price": {"value": price, "currency": "GBP"},
        "shipping": {"value": shipping, "currency": "GBP"},
        "seller": {
            "name": seller_name,
            "url": f"https://example.com/seller/{seller_name.lower()}",
        },
        "productUrl": f"https://example.com/amazon/{slug}",
        "image": {"url": f"https://example.com/amazon/{slug}.jpg"},
        "department": department,
        "condition": "New",
    }


def _walking_pad_demo_items() -> list[dict[str, Any]]:
    department = "Sports & Outdoors > Fitness"
    return [
        _demo_item(
            asin="B0WALKPAD01",
            title="Amazon Choice Walking Pad Treadmill 2 in 1 Foldable Under Desk 2.5HP Prime",
            price="229.99",
            seller_name="AmazonScoutDirect",
            department=department,
        ),
        _demo_item(
            asin="B0WALKPAD02",
            title="Sponsored Walking Pad Under Desk Treadmill Remote Control Home Office",
            price="199.99",
            seller_name="CardioHomeMarket",
            department=department,
        ),
        _demo_item(
            asin="B0WALKPAD03",
            title="Walking Pad Treadmill Portable 6km/h Compact Fitness Machine Pack of 2",
            price="189.99",
            seller_name="UKMotionHub",
            department=department,
        ),
    ]


def _standing_desk_demo_items() -> list[dict[str, Any]]:
    department = "Home Office Furniture"
    return [
        _demo_item(
            asin="B0DESK001",
            title="Amazon Basics Standing Desk Electric Height Adjustable 140cm Home Office Black",
            price="249.99",
            seller_name="DeskScoutDirect",
            department=department,
        ),
        _demo_item(
            asin="B0DESK002",
            title="Prime Sponsored Sit Stand Desk 120cm Electric Workstation Memory Preset",
            price="219.99",
            seller_name="DeskScoutDirect",
            department=department,
        ),
        _demo_item(
            asin="B0DESK003",
            title="Electric Standing Desk Adjustable Computer Table White ASIN B0XYZ12345",
            price="209.99",
            seller_name="WorkspaceLab",
            department=department,
        ),
    ]


def _office_chair_demo_items() -> list[dict[str, Any]]:
    department = "Home Office Furniture"
    return [
        _demo_item(
            asin="B0CHAIR01",
            title="Amazon Choice Ergonomic Office Chair High Back Reclining Footrest",
            price="179.99",
            seller_name="ChairMarketUK",
            department=department,
        ),
        _demo_item(
            asin="B0CHAIR02",
            title="Prime Mesh Office Chair Adjustable Headrest Lumbar Support",
            price="169.99",
            seller_name="ChairMarketUK",
            department=department,
        ),
        _demo_item(
            asin="B0CHAIR03",
            title="Sponsored Executive Desk Chair Wide Seat Home Office",
            price="189.99",
            seller_name="SeatHubUK",
            department=department,
        ),
    ]


def _generic_demo_items(query: str) -> list[dict[str, Any]]:
    department = "Home & Kitchen"
    title_base = " ".join(query.strip().split()).title() or "Storage Cabinet"

    return [
        _demo_item(
            asin="B0GENERIC1",
            title=f"Amazon Choice {title_base} Large Storage Unit",
            price="149.99",
            seller_name="ScoutStoreOne",
            department=department,
        ),
        _demo_item(
            asin="B0GENERIC2",
            title=f"{title_base} Home Organizer Prime",
            price="159.99",
            seller_name="ScoutStoreTwo",
            department=department,
        ),
        _demo_item(
            asin="B0GENERIC3",
            title=f"Sponsored {title_base} Heavy Duty Cabinet",
            price="179.99",
            seller_name="ScoutStoreThree",
            department=department,
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
