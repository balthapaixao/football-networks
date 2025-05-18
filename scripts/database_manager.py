import sqlite3
import os
from pathlib import Path

class FootballDatabaseManager:
    def __init__(self, db_path='data/football_events.db'):
        """Initialize the database manager."""
        self.db_path = db_path
        self._ensure_data_directory()
        self.conn = None
        self.cursor = None

    def _ensure_data_directory(self):
        """Ensure the data directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        """Connect to the SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        """Disconnect from the SQLite database."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def initialize_database(self):
        """Initialize the database with the schema."""
        try:
            self.connect()
            
            # Read and execute the SQL script
            script_path = Path('scripts/create_database.sql')
            with open(script_path, 'r') as f:
                sql_script = f.read()
            
            # Execute the script
            self.cursor.executescript(sql_script)
            self.conn.commit()
            
            print("Database initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            raise
        finally:
            self.disconnect()

    def insert_event(self, event_data):
        """
        Insert a single event into the FactEvents table.
        
        Args:
            event_data (dict): Dictionary containing event data
        """
        try:
            self.connect()
            
            query = """
            INSERT INTO FactEvents (
                event_id, match_id, player_id, team_id, timestamp,
                period_id, location_x, location_y, event_type_id,
                possession_id, duration
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self.cursor.execute(query, (
                event_data['event_id'],
                event_data['match_id'],
                event_data['player_id'],
                event_data['team_id'],
                event_data['timestamp'],
                event_data['period_id'],
                event_data['location_x'],
                event_data['location_y'],
                event_data['event_type_id'],
                event_data['possession_id'],
                event_data['duration']
            ))
            
            self.conn.commit()
            
        finally:
            self.disconnect()

    def insert_dimension_data(self, table_name, data):
        """
        Insert data into dimension tables.
        
        Args:
            table_name (str): Name of the dimension table
            data (dict): Dictionary containing the dimension data
        """
        try:
            self.connect()
            
            # Create the placeholders for the SQL query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            
            query = f"""
            INSERT INTO {table_name} ({columns})
            VALUES ({placeholders})
            """
            
            self.cursor.execute(query, tuple(data.values()))
            self.conn.commit()
            
        finally:
            self.disconnect()

    def execute_query(self, query, params=None):
        """
        Execute a custom SQL query.
        
        Args:
            query (str): SQL query to execute
            params (tuple): Optional parameters for the query
            
        Returns:
            list: Query results
        """
        try:
            self.connect()
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            results = self.cursor.fetchall()
            return results
            
        finally:
            self.disconnect()

if __name__ == "__main__":
    # Example usage
    db_manager = FootballDatabaseManager()
    db_manager.initialize_database() 