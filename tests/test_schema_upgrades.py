import unittest

from sqlalchemy import create_engine, text

from app.db.database import ensure_additive_schema


class SchemaUpgradeTests(unittest.TestCase):
    def test_ensure_additive_schema_adds_missing_columns(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        CREATE TABLE cluster_research_signals (
                            id INTEGER PRIMARY KEY,
                            cluster_id INTEGER,
                            supplier_intelligence_score FLOAT
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        CREATE TABLE cluster_score_snapshots (
                            id INTEGER PRIMARY KEY,
                            cluster_id INTEGER,
                            total_score FLOAT
                        )
                        """
                    )
                )

            ensure_additive_schema(engine)

            with engine.begin() as connection:
                research_columns = {
                    row[1]
                    for row in connection.execute(
                        text("PRAGMA table_info('cluster_research_signals')")
                    ).fetchall()
                }
                snapshot_columns = {
                    row[1]
                    for row in connection.execute(
                        text("PRAGMA table_info('cluster_score_snapshots')")
                    ).fetchall()
                }

            self.assertIn("supplier_breakdown_json", research_columns)
            self.assertIn("competitor_breakdown_json", research_columns)
            self.assertIn("source_name", snapshot_columns)
            self.assertIn("query", snapshot_columns)
        finally:
            engine.dispose()
