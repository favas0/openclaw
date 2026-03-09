import unittest

from app.sources.amazon import map_demo_item_to_raw_listing


class AmazonSourceMappingTests(unittest.TestCase):
    def test_map_demo_item_to_raw_listing_includes_traceability(self) -> None:
        item = {
            "asin": "B0TEST1234",
            "title": "Standing Desk Electric 140cm",
            "price": {"value": "249.99", "currency": "GBP"},
            "shipping": {"value": "0.00", "currency": "GBP"},
            "seller": {"name": "DeskStore", "url": "https://example.com/seller/deskstore"},
            "image": {"url": "https://example.com/item.jpg"},
            "productUrl": "https://example.com/amazon/item",
            "department": "Home Office Furniture",
            "condition": "New",
        }

        mapped = map_demo_item_to_raw_listing(item, query="standing desk")

        self.assertEqual(mapped["source_name"], "amazon")
        self.assertEqual(mapped["external_id"], "B0TEST1234")
        self.assertEqual(mapped["price"], 249.99)
        self.assertEqual(mapped["shipping_cost"], 0.0)
        self.assertEqual(mapped["currency"], "GBP")
        self.assertEqual(mapped["seller_name"], "DeskStore")
        self.assertEqual(mapped["raw_payload"]["provider"], "amazon_demo")
        self.assertEqual(mapped["raw_payload"]["query"], "standing desk")


if __name__ == "__main__":
    unittest.main()
