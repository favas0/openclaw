import unittest

from app.reporting.review_pack import build_review_pack_rows


class ReviewPackTests(unittest.TestCase):
    def test_build_review_pack_rows_merges_trend_context_and_summary(self) -> None:
        reporting_rows = [
            {
                "cluster_id": 1,
                "cluster_title": "walkingpad treadmill",
                "source_name": "ebay",
                "query": "walking pad",
                "recommendation": "test",
                "total_score": 47.5,
                "gross_profit_estimate": 82.0,
                "max_cpa": 49.0,
                "supplier_intelligence_score": 8.2,
                "competitor_saturation_score": 5.4,
            }
        ]
        trend_rows = [
            {
                "cluster_id": 1,
                "market_snapshots": 3,
                "series_status": "active",
                "score_coverage_status": "scored",
                "listing_count_delta": 1,
                "median_price_delta": -5.0,
                "recommendation_change": "watch -> test",
            }
        ]

        rows = build_review_pack_rows(reporting_rows, trend_rows)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["series_status"], "active")
        self.assertEqual(row["score_coverage_status"], "scored")
        self.assertEqual(row["recommendation_change"], "watch -> test")
        self.assertIn("recommendation=test", row["review_summary"])
        self.assertIn("supplier=8.2", row["review_summary"])
        self.assertIn("series=active", row["review_summary"])


if __name__ == "__main__":
    unittest.main()
