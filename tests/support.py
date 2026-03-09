import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
