import json

from app.db.repo import (
    get_cluster_trends,
    insert_score_snapshot,
    upsert_cluster_market_snapshot,
    upsert_product_cluster,
)
from tests.support import DatabaseTestCase


class TrendReportingTests(DatabaseTestCase):
    def test_get_cluster_trends_reports_market_deltas(self) -> None:
        cluster = upsert_product_cluster(
            self.db,
            cluster_key="walkingpad treadmill",
            cluster_title="walkingpad treadmill",
            source_name="ebay",
            query="walking pad",
            listing_count=3,
            seller_count=3,
            min_total_price=189.99,
            max_total_price=209.99,
            avg_total_price=199.99,
            median_total_price=199.99,
            high_ticket_count=3,
            brand_risk_count=0,
        )

        upsert_cluster_market_snapshot(
            self.db,
            cluster_id=cluster.id,
            run_id=1,
            source_name="ebay",
            query="walking pad",
            listing_count=2,
            seller_count=2,
            min_total_price=194.99,
            max_total_price=199.99,
            avg_total_price=197.49,
            median_total_price=197.49,
            external_ids_json=json.dumps(["a", "b"]),
            seller_names_json=json.dumps(["s1", "s2"]),
        )
        upsert_cluster_market_snapshot(
            self.db,
            cluster_id=cluster.id,
            run_id=2,
            source_name="ebay",
            query="walking pad",
            listing_count=3,
            seller_count=3,
            min_total_price=189.99,
            max_total_price=209.99,
            avg_total_price=199.99,
            median_total_price=189.99,
            external_ids_json=json.dumps(["b", "c", "d"]),
            seller_names_json=json.dumps(["s2", "s3", "s4"]),
        )

        insert_score_snapshot(
            self.db,
            cluster_id=cluster.id,
            total_score=40.0,
            recommendation="watch",
            gross_profit_estimate=70.0,
            max_cpa=42.0,
        )
        insert_score_snapshot(
            self.db,
            cluster_id=cluster.id,
            total_score=48.5,
            recommendation="test",
            gross_profit_estimate=79.0,
            max_cpa=47.0,
        )

        rows = get_cluster_trends(self.db, limit=10)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["market_snapshots"], 2)
        self.assertEqual(row["listing_count_delta"], 1)
        self.assertEqual(row["seller_count_delta"], 1)
        self.assertEqual(row["median_price_delta"], -7.5)
        self.assertEqual(row["new_items_since_last_snapshot"], 2)
        self.assertEqual(row["removed_items_since_last_snapshot"], 1)
        self.assertEqual(row["score_delta"], 8.5)
        self.assertEqual(row["latest_recommendation"], "test")
