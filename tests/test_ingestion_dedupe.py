from app.db.repo import (
    create_ingestion_run,
    find_existing_raw_listing_in_run,
    insert_raw_listing,
)
from tests.support import DatabaseTestCase


class IngestionDedupeTests(DatabaseTestCase):
    def test_find_existing_raw_listing_in_same_run_by_external_id(self) -> None:
        run = create_ingestion_run(
            self.db,
            source_name="ebay",
            query="walking pad",
        )
        inserted = insert_raw_listing(
            self.db,
            run_id=run.id,
            source_name="ebay",
            query="walking pad",
            external_id="abc123",
            title="Walking Pad",
            item_url="https://example.com/abc123",
            seller_name="seller_one",
        )

        existing = find_existing_raw_listing_in_run(
            self.db,
            run_id=run.id,
            source_name="ebay",
            external_id="abc123",
        )

        self.assertIsNotNone(existing)
        self.assertEqual(existing.id, inserted.id)

    def test_find_existing_raw_listing_does_not_cross_runs(self) -> None:
        first_run = create_ingestion_run(
            self.db,
            source_name="ebay",
            query="walking pad",
        )
        second_run = create_ingestion_run(
            self.db,
            source_name="ebay",
            query="walking pad",
        )
        insert_raw_listing(
            self.db,
            run_id=first_run.id,
            source_name="ebay",
            query="walking pad",
            external_id="abc123",
            title="Walking Pad",
            item_url="https://example.com/abc123",
            seller_name="seller_one",
        )

        existing = find_existing_raw_listing_in_run(
            self.db,
            run_id=second_run.id,
            source_name="ebay",
            external_id="abc123",
        )

        self.assertIsNone(existing)
