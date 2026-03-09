import json
from types import SimpleNamespace

from app.db.repo import get_reporting_summary, upsert_cluster_research_signal, upsert_cluster_score, upsert_product_cluster
from app.research.signals import build_research_signal
from tests.support import DatabaseTestCase


class ResearchSignalTests(DatabaseTestCase):
    def test_build_research_signal_returns_structured_supplier_and_competitor_breakdowns(self) -> None:
        cluster = SimpleNamespace(
            cluster_title="walkingpad treadmill",
            listing_count=5,
            seller_count=3,
            min_total_price=189.99,
            max_total_price=239.99,
            median_total_price=199.99,
            brand_risk_count=0,
        )
        enrichment = SimpleNamespace(
            category_hint="home office fitness",
            buyer_intent="home office fitness",
            visual_hook_score=8,
            fragility_risk=2,
            assembly_complexity=2,
            supplier_search_terms_json=json.dumps(["walking pad supplier", "folding treadmill"]),
            confidence_score=8,
        )

        signal = build_research_signal(cluster, enrichment)

        self.assertGreaterEqual(signal["supplier_intelligence_score"], 7.0)
        self.assertIn("catalog_fit_score", signal["supplier_breakdown"])
        self.assertIn("shipping_profile_score", signal["supplier_breakdown"])
        self.assertIn("margin_support_score", signal["supplier_breakdown"])
        self.assertTrue(signal["supplier_breakdown"]["strengths"])
        self.assertIn("seller_pressure_score", signal["competitor_breakdown"])
        self.assertIn("price_pressure_score", signal["competitor_breakdown"])
        self.assertTrue(signal["supplier_notes"])
        self.assertTrue(signal["competitor_notes"])

    def test_build_research_signal_marks_crowded_tight_price_cluster_as_more_saturated(self) -> None:
        cluster = SimpleNamespace(
            cluster_title="officechair recliner",
            listing_count=6,
            seller_count=5,
            min_total_price=189.0,
            max_total_price=199.0,
            median_total_price=194.0,
            brand_risk_count=0,
        )

        signal = build_research_signal(cluster, None)

        self.assertGreaterEqual(signal["competitor_saturation_score"], 7.0)
        self.assertGreaterEqual(signal["competitor_breakdown"]["price_pressure_score"], 7.0)
        self.assertIn("crowded", signal["competitor_notes"])


class ReportingSummaryTests(DatabaseTestCase):
    def test_get_reporting_summary_merges_research_signal_breakdown_fields(self) -> None:
        cluster = upsert_product_cluster(
            self.db,
            cluster_key="walkingpad treadmill",
            cluster_title="walkingpad treadmill",
            source_name="ebay",
            query="walking pad",
            listing_count=4,
            seller_count=3,
            min_total_price=189.99,
            max_total_price=229.99,
            avg_total_price=204.99,
            median_total_price=199.99,
            high_ticket_count=4,
            brand_risk_count=0,
        )

        upsert_cluster_score(
            self.db,
            cluster_id=cluster.id,
            demand_score=8.0,
            sales_signal_score=7.0,
            competition_score=5.0,
            supplier_fit_score=8.0,
            risk_score=1.0,
            sell_price_estimate=199.99,
            supplier_cost_estimate=84.0,
            shipping_cost_estimate=20.0,
            fees_estimate=13.0,
            gross_profit_estimate=82.99,
            max_cpa=49.79,
            total_score=44.0,
            recommendation="test",
            notes="solid economics",
        )
        upsert_cluster_research_signal(
            self.db,
            cluster_id=cluster.id,
            supplier_intelligence_score=8.4,
            ad_signal_score=7.0,
            competitor_saturation_score=5.8,
            multi_market_score=6.5,
            trend_score=6.0,
            handling_complexity_score=2.0,
            supplier_search_query="walkingpad treadmill supplier wholesale",
            supplier_terms_json=json.dumps(["walking pad supplier"]),
            supplier_breakdown_json=json.dumps(
                {
                    "catalog_fit_score": 8.5,
                    "shipping_profile_score": 7.5,
                    "margin_support_score": 8.0,
                    "evidence_score": 8.5,
                    "confidence_score": 7.0,
                    "strengths": ["supplier-friendly category"],
                    "risks": ["bulky to ship"],
                }
            ),
            supplier_notes="strengths: supplier-friendly category | risks: bulky to ship",
            ad_notes="good visual hook",
            competitor_breakdown_json=json.dumps(
                {
                    "seller_pressure_score": 6.0,
                    "listing_pressure_score": 5.0,
                    "price_pressure_score": 7.0,
                    "market_maturity_score": 5.0,
                    "strengths": ["not fully commoditised"],
                    "risks": ["tight spread"],
                }
            ),
            competitor_notes="strengths: not fully commoditised | risks: tight spread",
            trend_notes="evergreen",
            score_adjustment=2.1,
        )

        rows = get_reporting_summary(self.db, limit=None)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source_name"], "ebay")
        self.assertEqual(row["supplier_catalog_fit_score"], 8.5)
        self.assertEqual(row["supplier_evidence_score"], 8.5)
        self.assertEqual(row["competitor_price_pressure_score"], 7.0)
        self.assertEqual(row["supplier_terms"], ["walking pad supplier"])
        self.assertEqual(row["supplier_strengths"], ["supplier-friendly category"])
        self.assertEqual(row["competitor_risks"], ["tight spread"])
