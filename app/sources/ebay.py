from typing import Any


def _parse_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def map_demo_item_to_raw_listing(item: dict[str, Any], query: str) -> dict[str, Any]:
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
        "item_url": item.get("itemWebUrl") or "",
        "image_url": image.get("imageUrl"),
        "category": item.get("categoryPath"),
        "condition": item.get("condition"),
        "is_sold_signal": False,
        "raw_payload": {
            "provider": "ebay_demo",
            "query": query,
            "item": item,
        },
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
