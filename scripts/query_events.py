import pandas as pd
from pathlib import Path
from typing import Union, List, Dict
import warnings
from sqlalchemy import create_engine, text
import sqlite3
import json
import ast

class EventQuery:
    def __init__(self, events_file="data/euro_2024/all_events.csv", matches_file="data/euro_2024/matches.csv"):
        """Initialize the query engine with the event and match data."""
        # Read the CSV files
        self.events_df = pd.read_csv(events_file, low_memory=False)
        self.matches_df = pd.read_csv(matches_file)
        
        # Convert string dictionaries to actual dictionaries and then to JSON strings
        json_columns = ['type', 'possession_team', 'play_pattern', 'team', 'tactics', 
                       'player', 'position', 'pass', 'shot', 'goalkeeper']
        
        for col in json_columns:
            if col in self.events_df.columns:
                self.events_df[col] = self.events_df[col].apply(
                    lambda x: json.dumps(ast.literal_eval(x)) if pd.notna(x) and isinstance(x, str) else None
                )
        
        # Create SQLite database in memory
        self.engine = create_engine('sqlite:///:memory:')
        
        # Store events data
        self.events_df.to_sql('events', self.engine, index=False)
        
        # Store matches data
        self.matches_df.to_sql('matches', self.engine, index=False)
        
        # Print available tables and their schemas
        self._print_schema()
    
    def _print_schema(self):
        """Print the schema of all tables in the database."""
        with self.engine.connect() as conn:
            # Get list of tables
            tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
            
            print("\nAvailable tables:")
            for i, table in enumerate(tables['name'], 1):
                print(f"{i}. {table}")
            
            # Print schema for each table
            for table in tables['name']:
                print(f"\n{table.capitalize()} table schema:")
                schema = pd.read_sql_query(f"PRAGMA table_info({table});", conn)
                print(schema.to_string())
    
    def query(self, sql_query: str, return_type: str = 'dataframe') -> Union[pd.DataFrame, Dict, List]:
        """
        Execute a SQL query on the events and matches data.
        
        Args:
            sql_query (str): SQL query string
                Examples:
                - "SELECT * FROM events WHERE type_name = 'Shot' AND team_name = 'England'"
                - "SELECT e.*, m.home_team FROM events e JOIN matches m ON e.match_id = m.match_id"
                - "SELECT player_name, COUNT(*) as shots FROM events WHERE type_name = 'Shot' GROUP BY player_name"
            return_type (str): Type of return value ('dataframe', 'dict', or 'list')
            
        Returns:
            Union[pd.DataFrame, Dict, List]: Query results in the specified format
        """
        try:
            result = pd.read_sql_query(sql_query, self.engine)
            
            if return_type == 'dataframe':
                return result
            elif return_type == 'dict':
                return result.to_dict('records')
            elif return_type == 'list':
                return result.values.tolist()
            else:
                warnings.warn(f"Unknown return_type '{return_type}'. Defaulting to 'dataframe'.")
                return result
            
        except Exception as e:
            raise ValueError(f"Error executing query: {str(e)}")
    
    def get_match_events(self, team_name: str = None, stage: str = None) -> pd.DataFrame:
        """
        Get events for specific matches based on team name and/or competition stage.
        
        Args:
            team_name (str, optional): Team name to filter by
            stage (str, optional): Competition stage to filter by
            
        Returns:
            pd.DataFrame: Filtered events
        """
        query_parts = []
        
        if team_name:
            query_parts.append(f"(team_name == '{team_name}')")
        
        if stage:
            query_parts.append(f"(competition_stage == '{stage}')")
        
        if query_parts:
            query_str = " and ".join(query_parts)
            return self.query(query_str)
        
        return self.events_df
    
    def get_player_events(self, player_name: str, event_types: List[str] = None) -> pd.DataFrame:
        """
        Get all events for a specific player, optionally filtered by event types.
        
        Args:
            player_name (str): Name of the player
            event_types (List[str], optional): List of event types to include
            
        Returns:
            pd.DataFrame: Player's events
        """
        query_parts = [f"player_name == '{player_name}'"]
        
        if event_types:
            event_types_str = "', '".join(event_types)
            query_parts.append(f"type_name in ('{event_types_str}')")
        
        query_str = " and ".join(query_parts)
        return self.query(query_str)

def example_usage():
    """Example usage of the EventQuery class with SQL queries"""
    # Initialize the query engine
    eq = EventQuery()
    
    # Example 1: Get all shots by England with player name and outcome
    england_shots = eq.query("""
        SELECT minute, player_name, outcome_name, shot_statsbomb_xg
        FROM events
        WHERE type_name = 'Shot' 
        AND team_name = 'England'
        ORDER BY minute
        LIMIT 5
    """)
    print("\nEngland shots:")
    print(england_shots)
    
    # Example 2: Get successful passes in the first 15 minutes with team info
    early_passes = eq.query("""
        SELECT e.minute, e.team_name, e.player_name, m.home_team, m.away_team
        FROM events e
        JOIN matches m ON e.match_id = m.match_id
        WHERE e.type_name = 'Pass'
        AND e.period = 1 
        AND e.minute <= 15
        LIMIT 5
    """)
    print("\nEarly successful passes:")
    print(early_passes)
    
    # Example 3: Get shot statistics by team
    shot_stats = eq.query("""
        SELECT 
            team_name,
            COUNT(*) as total_shots,
            SUM(CASE WHEN outcome_name = 'Goal' THEN 1 ELSE 0 END) as goals,
            AVG(shot_statsbomb_xg) as avg_xg
        FROM events
        WHERE type_name = 'Shot'
        GROUP BY team_name
        ORDER BY goals DESC
    """)
    print("\nShot statistics by team:")
    print(shot_stats)

def glauco_example(strict=True):
    """Example query to find specific passing sequences ending in goals.
    
    Args:
        strict (bool): If True, uses original strict position matching.
                      If False, uses more flexible position matching.
    """
    if strict:
        sql_query = """
                WITH defender_to_midfield AS (
            -- First pass: Defender to midfielder
            SELECT 
                e1.match_id,
                e1.possession_id,
                e1.timestamp as first_pass_time,
                e1.player_id as defender_id,
                e2.player_id as midfielder_id,
                e1.location_x as pass_x,
                e1.location_y as pass_y
            FROM FactEvents e1
            JOIN FactEvents e2 
                ON e1.possession_id = e2.possession_id
                AND e1.match_id = e2.match_id
                AND e2.timestamp > e1.timestamp
            WHERE e1.event_type = 'Pass'
            AND e2.event_type = 'Ball Receipt*'
            -- Defender is in defensive third
            AND e1.location_x BETWEEN 0 AND 40
            -- Midfielder is in middle third
            AND e2.location_x BETWEEN 40 AND 80
        ),
        midfield_to_wing AS (
            -- Second pass: Midfielder to right winger
            SELECT 
                d.*,
                e3.timestamp as second_pass_time,
                e3.player_id as winger_id,
                e3.location_x as winger_x,
                e3.location_y as winger_y
            FROM defender_to_midfield d
            JOIN FactEvents e3
                ON d.possession_id = e3.possession_id
                AND d.match_id = e3.match_id
                AND e3.timestamp > d.first_pass_time
            WHERE e3.event_type = 'Pass'
            -- Right winger is on the right wing
            AND e3.location_y BETWEEN 60 AND 80
        ),
        final_sequence AS (
            -- Final shot and goal
            SELECT 
                m.*,
                e4.timestamp as shot_time,
                e4.location_x as shot_x,
                e4.location_y as shot_y
            FROM midfield_to_wing m
            JOIN FactEvents e4
                ON m.possession_id = e4.possession_id
                AND m.match_id = e4.match_id
                AND e4.timestamp > m.second_pass_time
            WHERE e4.event_type = 'Shot'
        )
        SELECT 
            m.match_date,
            m.competition_name,
            t.team_name,
            p1.player_name as defender,
            p2.player_name as midfielder,
            p3.player_name as winger,
            fs.shot_time,
            fs.shot_x,
            fs.shot_y
        FROM final_sequence fs
        JOIN DimMatch m ON fs.match_id = m.match_id
        JOIN DimTeam t ON fs.team_id = t.team_id
        JOIN DimPlayer p1 ON fs.defender_id = p1.player_id
        JOIN DimPlayer p2 ON fs.midfielder_id = p2.player_id
        JOIN DimPlayer p3 ON fs.winger_id = p3.player_id
        ORDER BY m.match_date, fs.shot_time;
        """
    
    eq = EventQuery()
    result = eq.query(sql_query)
    
    if len(result) > 0:
        print("\nFound the following goal sequences:")
        print(result.to_string(index=False))
        print(f"\nTotal sequences found: {len(result)}")
    else:
        print("\nNo sequences found matching the criteria.")

if __name__ == "__main__":
    # Run both strict and flexible searches
    print("\nStrict position matching:")
    glauco_example(strict=True)
    # print("\nFlexible position matching:")
    # glauco_example(strict=False) 