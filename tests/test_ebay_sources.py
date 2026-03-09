import unittest

from app.sources.ebay import map_demo_item_to_raw_listing
from app.sources.ebay_api import map_api_item_to_raw_listing


class EbaySourceMappingTests(unittest.TestCase):
    def test_map_api_item_to_raw_listing_includes_traceability(self) -> None:
        item = {
            "itemId": "v1|123|0",
            "title": "Walking Pad Treadmill",
            "price": {"value": "199.99", "currency": "GBP"},
            "shippingOptions": [{"shippingCost": {"value": "9.99", "currency": "GBP"}}],
            "seller": {"username": "demo_seller"},
            "image": {"imageUrl": "https://example.com/item.jpg"},
            "itemWebUrl": "https://www.ebay.co.uk/itm/123",
            "categoryPath": "Fitness > Cardio",
            "condition": "New",
        }

        mapped = map_api_item_to_raw_listing(item, query="walking pad", marketplace_id="EBAY_GB")

        self.assertEqual(mapped["source_name"], "ebay")
        self.assertEqual(mapped["external_id"], "v1|123|0")
        self.assertEqual(mapped["price"], 199.99)
        self.assertEqual(mapped["shipping_cost"], 9.99)
        self.assertEqual(mapped["currency"], "GBP")
        self.assertEqual(mapped["seller_name"], "demo_seller")
        self.assertEqual(mapped["raw_payload"]["provider"], "ebay_browse_api")
        self.assertEqual(mapped["raw_payload"]["marketplace_id"], "EBAY_GB")
        self.assertEqual(mapped["raw_payload"]["query"], "walking pad")

    def test_map_demo_item_to_raw_listing_marks_demo_provider(self) -> None:
        item = {
            "itemId": "demo-1",
            "title": "Desk",
            "price": {"value": "149.99", "currency": "GBP"},
            "shippingOptions": [{"shippingCost": {"value": "0.00", "currency": "GBP"}}],
            "seller": {"username": "demo_store"},
            "image": {"imageUrl": "https://example.com/demo.jpg"},
            "itemWebUrl": "https://example.com/demo",
            "categoryPath": "Furniture",
            "condition": "New",
        }

        mapped = map_demo_item_to_raw_listing(item, query="desk")

        self.assertEqual(mapped["raw_payload"]["provider"], "ebay_demo")
        self.assertEqual(mapped["raw_payload"]["query"], "desk")


if __name__ == "__main__":
    unittest.main()
