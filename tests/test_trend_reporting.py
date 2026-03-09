import json

from app.db.repo import (
    assign_listing_to_cluster,
    create_ingestion_run,
    finish_ingestion_run,
    get_cluster_trends,
    get_latest_market_snapshot_rows_for_query,
    insert_raw_listing,
    insert_score_snapshot,
    upsert_cluster_market_snapshot,
    upsert_normalized_listing,
    upsert_product_cluster,
    upsert_cluster_score,
)
from app.research.trend_snapshots import capture_trend_snapshots
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

    def test_get_cluster_trends_keeps_query_series_separate(self) -> None:
        cluster = upsert_product_cluster(
            self.db,
            cluster_key="walkingpad treadmill",
            cluster_title="walkingpad treadmill",
            source_name="ebay",
            query="walking pad",
            listing_count=3,
            seller_count=3,
            min_total_price=180.0,
            max_total_price=220.0,
            avg_total_price=200.0,
            median_total_price=200.0,
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
            min_total_price=190.0,
            max_total_price=200.0,
            avg_total_price=195.0,
            median_total_price=195.0,
            external_ids_json=json.dumps(["a", "b"]),
            seller_names_json=json.dumps(["s1", "s2"]),
        )
        upsert_cluster_market_snapshot(
            self.db,
            cluster_id=cluster.id,
            run_id=2,
            source_name="ebay",
            query="walking pad",
            listing_count=4,
            seller_count=3,
            min_total_price=185.0,
            max_total_price=205.0,
            avg_total_price=195.0,
            median_total_price=192.5,
            external_ids_json=json.dumps(["a", "b", "c", "d"]),
            seller_names_json=json.dumps(["s1", "s2", "s3"]),
        )
        upsert_cluster_market_snapshot(
            self.db,
            cluster_id=cluster.id,
            run_id=3,
            source_name="ebay",
            query="treadmill",
            listing_count=1,
            seller_count=1,
            min_total_price=220.0,
            max_total_price=220.0,
            avg_total_price=220.0,
            median_total_price=220.0,
            external_ids_json=json.dumps(["x"]),
            seller_names_json=json.dumps(["seller_x"]),
        )

        insert_score_snapshot(
            self.db,
            cluster_id=cluster.id,
            total_score=42.0,
            recommendation="watch",
            gross_profit_estimate=75.0,
            max_cpa=45.0,
        )

        rows = get_cluster_trends(self.db, limit=10)

        self.assertEqual(len(rows), 2)
        walking_pad_row = next(row for row in rows if row["query"] == "walking pad")
        treadmill_row = next(row for row in rows if row["query"] == "treadmill")

        self.assertEqual(walking_pad_row["market_snapshots"], 2)
        self.assertEqual(walking_pad_row["listing_count_delta"], 2)
        self.assertEqual(walking_pad_row["latest_listing_count"], 4)

        self.assertEqual(treadmill_row["market_snapshots"], 1)
        self.assertEqual(treadmill_row["listing_count_delta"], 0)
        self.assertEqual(treadmill_row["latest_listing_count"], 1)

        filtered_rows = get_cluster_trends(self.db, limit=10, query="walking pad")

        self.assertEqual(len(filtered_rows), 1)
        self.assertEqual(filtered_rows[0]["query"], "walking pad")
        self.assertEqual(filtered_rows[0]["latest_listing_count"], 4)

    def test_get_cluster_trends_supports_new_item_sorting(self) -> None:
        cluster_one = upsert_product_cluster(
            self.db,
            cluster_key="cluster one",
            cluster_title="cluster one",
            source_name="ebay",
            query="chairs",
            listing_count=4,
            seller_count=2,
            min_total_price=100.0,
            max_total_price=140.0,
            avg_total_price=120.0,
            median_total_price=120.0,
            high_ticket_count=2,
            brand_risk_count=0,
        )
        cluster_two = upsert_product_cluster(
            self.db,
            cluster_key="cluster two",
            cluster_title="cluster two",
            source_name="ebay",
            query="chairs",
            listing_count=3,
            seller_count=2,
            min_total_price=100.0,
            max_total_price=130.0,
            avg_total_price=115.0,
            median_total_price=115.0,
            high_ticket_count=2,
            brand_risk_count=0,
        )

        upsert_cluster_market_snapshot(
            self.db,
            cluster_id=cluster_one.id,
            run_id=1,
            source_name="ebay",
            query="chairs",
            listing_count=1,
            seller_count=1,
            min_total_price=100.0,
            max_total_price=100.0,
            avg_total_price=100.0,
            median_total_price=100.0,
            external_ids_json=json.dumps(["a"]),
            seller_names_json=json.dumps(["s1"]),
        )
        upsert_cluster_market_snapshot(
            self.db,
            cluster_id=cluster_one.id,
            run_id=2,
            source_name="ebay",
            query="chairs",
            listing_count=4,
            seller_count=2,
            min_total_price=100.0,
            max_total_price=140.0,
            avg_total_price=120.0,
            median_total_price=120.0,
            external_ids_json=json.dumps(["a", "b", "c", "d"]),
            seller_names_json=json.dumps(["s1", "s2"]),
        )

        upsert_cluster_market_snapshot(
            self.db,
            cluster_id=cluster_two.id,
            run_id=1,
            source_name="ebay",
            query="chairs",
            listing_count=1,
            seller_count=1,
            min_total_price=110.0,
            max_total_price=110.0,
            avg_total_price=110.0,
            median_total_price=110.0,
            external_ids_json=json.dumps(["x"]),
            seller_names_json=json.dumps(["s1"]),
        )
        upsert_cluster_market_snapshot(
            self.db,
            cluster_id=cluster_two.id,
            run_id=2,
            source_name="ebay",
            query="chairs",
            listing_count=3,
            seller_count=2,
            min_total_price=100.0,
            max_total_price=130.0,
            avg_total_price=115.0,
            median_total_price=115.0,
            external_ids_json=json.dumps(["x", "y", "z"]),
            seller_names_json=json.dumps(["s1", "s2"]),
        )

        rows = get_cluster_trends(self.db, limit=10, sort_by="new-items")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["cluster_id"], cluster_one.id)
        self.assertEqual(rows[0]["new_items_since_last_snapshot"], 3)
        self.assertEqual(rows[1]["cluster_id"], cluster_two.id)
        self.assertEqual(rows[1]["new_items_since_last_snapshot"], 2)

    def test_capture_trend_snapshots_uses_explicit_run_id(self) -> None:
        run_one = create_ingestion_run(self.db, source_name="ebay", query="walking pad")
        run_two = create_ingestion_run(self.db, source_name="ebay", query="walking pad")

        raw_one = insert_raw_listing(
            self.db,
            run_id=run_one.id,
            source_name="ebay",
            query="walking pad",
            external_id="one",
            title="Walking Pad One",
            price=190.0,
            shipping_cost=0.0,
            seller_name="seller_one",
            item_url="https://example.com/one",
        )
        raw_two = insert_raw_listing(
            self.db,
            run_id=run_two.id,
            source_name="ebay",
            query="walking pad",
            external_id="two",
            title="Walking Pad Two",
            price=200.0,
            shipping_cost=0.0,
            seller_name="seller_two",
            item_url="https://example.com/two",
        )

        cluster = upsert_product_cluster(
            self.db,
            cluster_key="walkingpad treadmill",
            cluster_title="walkingpad treadmill",
            source_name="ebay",
            query="walking pad",
            listing_count=2,
            seller_count=2,
            min_total_price=190.0,
            max_total_price=200.0,
            avg_total_price=195.0,
            median_total_price=195.0,
            high_ticket_count=2,
            brand_risk_count=0,
        )

        norm_one = upsert_normalized_listing(
            self.db,
            raw_listing_id=raw_one.id,
            source_name="ebay",
            query="walking pad",
            original_title="Walking Pad One",
            normalized_title="walking pad one",
            canonical_tokens="one walkingpad",
            price=190.0,
            shipping_cost=0.0,
            total_price=190.0,
            currency="GBP",
            seller_name="seller_one",
            category="Fitness",
            condition="New",
            token_count=3,
            has_brand_risk=False,
            is_high_ticket_candidate=True,
        )
        norm_two = upsert_normalized_listing(
            self.db,
            raw_listing_id=raw_two.id,
            source_name="ebay",
            query="walking pad",
            original_title="Walking Pad Two",
            normalized_title="walking pad two",
            canonical_tokens="two walkingpad",
            price=200.0,
            shipping_cost=0.0,
            total_price=200.0,
            currency="GBP",
            seller_name="seller_two",
            category="Fitness",
            condition="New",
            token_count=3,
            has_brand_risk=False,
            is_high_ticket_candidate=True,
        )

        assign_listing_to_cluster(self.db, normalized_listing_id=norm_one.id, cluster_id=cluster.id)
        assign_listing_to_cluster(self.db, normalized_listing_id=norm_two.id, cluster_id=cluster.id)

        upsert_cluster_score(
            self.db,
            cluster_id=cluster.id,
            demand_score=6.0,
            sales_signal_score=6.0,
            competition_score=5.0,
            supplier_fit_score=8.0,
            risk_score=1.0,
            sell_price_estimate=195.0,
            supplier_cost_estimate=81.9,
            shipping_cost_estimate=20.0,
            fees_estimate=12.7,
            gross_profit_estimate=80.4,
            max_cpa=48.2,
            total_score=41.3,
            recommendation="watch",
            notes="ok",
        )

        finish_ingestion_run(self.db, run_id=run_one.id, status="completed", listings_found=1)
        finish_ingestion_run(self.db, run_id=run_two.id, status="completed", listings_found=1)

        result = capture_trend_snapshots(self.db, run_id=run_one.id)
        snapshot_rows = get_latest_market_snapshot_rows_for_query(
            self.db,
            source_name="ebay",
            query="walking pad",
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["snapshot_run_id"], run_one.id)
        self.assertEqual(result["market_snapshots_written"], 1)
        self.assertEqual(len(snapshot_rows), 1)
        self.assertEqual(snapshot_rows[0].run_id, run_one.id)
