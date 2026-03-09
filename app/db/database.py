from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    f"sqlite:///{settings.openclaw_db_path}",
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()


ADDITIVE_SCHEMA_COLUMNS: dict[str, dict[str, str]] = {
    "cluster_research_signals": {
        "supplier_breakdown_json": "TEXT",
        "competitor_breakdown_json": "TEXT",
    },
    "cluster_score_snapshots": {
        "source_name": "VARCHAR(50)",
        "query": "VARCHAR(255)",
    },
}

ADDITIVE_SCHEMA_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS ix_cluster_score_snapshots_source_name ON cluster_score_snapshots (source_name)",
    "CREATE INDEX IF NOT EXISTS ix_cluster_score_snapshots_query ON cluster_score_snapshots (query)",
)


def ensure_additive_schema(bind_engine) -> None:
    with bind_engine.begin() as connection:
        for table_name, columns in ADDITIVE_SCHEMA_COLUMNS.items():
            existing_columns = {
                row[1]
                for row in connection.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()
            }
            if not existing_columns:
                continue

            for column_name, column_sql in columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
                )

        for statement in ADDITIVE_SCHEMA_INDEXES:
            connection.execute(text(statement))
