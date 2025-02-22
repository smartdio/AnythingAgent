import os
import lancedb
import pyarrow as pa
from typing import Optional
from app.core.config import settings

class Database:
    """Database connection management class"""
    _instance: Optional['Database'] = None
    _db = None

    def __new__(cls) -> 'Database':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._db is None:
            self._ensure_db_dir()
            self._db = lancedb.connect(settings.LANCEDB_URI)

    def _ensure_db_dir(self):
        """Ensure database directory exists"""
        os.makedirs(settings.LANCEDB_URI, exist_ok=True)

    @property
    def db(self):
        """Get database connection"""
        return self._db

    def get_table(self, table_name: str):
        """
        Get or create table

        Args:
            table_name: Name of the table

        Returns:
            Table object
        """
        try:
            return self._db.open_table(table_name)
        except Exception:
            # If table doesn't exist, create a new one
            schema = pa.schema([
                ('id', pa.string()),
                ('vector', pa.list_(pa.float32(), settings.VECTOR_SIZE)),
                ('metadata', pa.string())
            ])
            return self._db.create_table(table_name, schema=schema)

    def close(self):
        """Close database connection"""
        if self._db:
            self._db = None

db = Database() 