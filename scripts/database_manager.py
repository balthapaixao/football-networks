import sqlite3
import os
from pathlib import Path
import logging

class FootballDatabaseManager:
    def __init__(self, db_path='data/football_events.db'):
        """Initialize the database manager."""
        self.db_path = db_path
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Ensure the data directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self):
        """Create and configure a new database connection."""
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("PRAGMA cache_size=-4000000")
        conn.execute("PRAGMA busy_timeout=60000")
        return conn

    def initialize_database(self):
        """Initialize the database schema."""
        conn = self.get_connection()
        try:
            with open('scripts/create_database.sql', 'r') as f:
                conn.executescript(f.read())
            conn.commit()
        finally:
            conn.close()

    def batch_insert_dimension_data(self, table_name, data_list):
        """Insert multiple records into dimension tables."""
        if not data_list:
            return
            
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Get columns from first record
            columns = list(data_list[0].keys())
            placeholders = ', '.join(['?' for _ in columns])
            columns_str = ', '.join(columns)
            
            query = f"""
                INSERT OR IGNORE INTO {table_name} ({columns_str})
                VALUES ({placeholders})
            """
            
            # Convert list of dicts to list of tuples
            values = [tuple(record[col] for col in columns) for record in data_list]
            
            cursor.executemany(query, values)
            conn.commit()
        except Exception as e:
            logging.error(f"Error batch inserting into {table_name}: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def batch_insert_events(self, event_data_list):
        """Insert multiple events in a batch."""
        if not event_data_list:
            return
            
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Get columns from first record
            columns = list(event_data_list[0].keys())
            placeholders = ', '.join(['?' for _ in columns])
            columns_str = ', '.join(columns)
            
            query = f"""
                INSERT OR IGNORE INTO FactEvents ({columns_str})
                VALUES ({placeholders})
            """
            
            # Convert list of dicts to list of tuples
            values = [tuple(record[col] for col in columns) for record in event_data_list]
            
            cursor.executemany(query, values)
            conn.commit()
        except Exception as e:
            logging.error(f"Error batch inserting events: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()

if __name__ == "__main__":
    # Example usage
    db_manager = FootballDatabaseManager()
    db_manager.initialize_database() 