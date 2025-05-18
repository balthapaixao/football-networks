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
        WITH pass_sequence AS (
            SELECT 
                e.id,
                e.match_id,
                e.possession,
                json_extract(json(e.team), '$.name') as team_name,
                e.minute,
                e.second,
                json_extract(json(e.player), '$.name') as player_name,
                json_extract(json(e.position), '$.name') as position_name,
                json_extract(json(e.pass), '$.recipient.name') as pass_recipient_name,
                CAST(json_extract(json(e.pass), '$.length') AS FLOAT) as pass_length,
                json_extract(json(e.pass), '$.height.name') as pass_height,
                json_extract(json(e.pass), '$.outcome.name') as pass_outcome,
                json_extract(json(e.type), '$.name') as event_type
            FROM events e
            WHERE json_extract(json(e.type), '$.name') = 'Pass'
        ),
        
        goalkeeper_pass AS (
            SELECT 
                e1.match_id,
                e1.possession,
                e1.team_name,
                e1.minute as gk_minute,
                e1.second as gk_second,
                e1.player_name as gk_name,
                e1.pass_recipient_name as defender_name,
                e1.id as pass_id,
                e1.pass_length as gk_pass_length,
                e1.pass_height as gk_pass_height
            FROM pass_sequence e1
            WHERE e1.position_name = 'Goalkeeper'
            AND e1.pass_outcome IS NULL
        ),

        defender_pass AS (
            SELECT 
                e2.match_id,
                e2.possession,
                e2.team_name,
                e2.minute as def_minute,
                e2.second as def_second,
                e2.player_name as defender_name,
                e2.pass_recipient_name as rb_name,
                e2.id as pass_id,
                e2.pass_length as def_pass_length,
                e2.pass_height as def_pass_height,
                gp.gk_name,
                gp.gk_minute,
                gp.gk_second,
                gp.gk_pass_length,
                gp.gk_pass_height
            FROM pass_sequence e2
            JOIN goalkeeper_pass gp 
                ON e2.match_id = gp.match_id 
                AND e2.possession = gp.possession
                AND e2.player_name = gp.defender_name
            WHERE e2.pass_outcome IS NULL
            AND e2.minute >= gp.gk_minute
            AND (e2.minute > gp.gk_minute OR e2.second > gp.gk_second)
        ),

        rb_pass AS (
            SELECT 
                e3.match_id,
                e3.possession,
                e3.team_name,
                e3.minute as rb_minute,
                e3.second as rb_second,
                e3.player_name as rb_name,
                e3.pass_recipient_name as rw_name,
                e3.id as pass_id,
                e3.pass_length as rb_pass_length,
                e3.pass_height as rb_pass_height,
                dp.*
            FROM pass_sequence e3
            JOIN defender_pass dp 
                ON e3.match_id = dp.match_id 
                AND e3.possession = dp.possession
                AND e3.player_name = dp.rb_name
            WHERE e3.pass_outcome IS NULL
            AND e3.minute >= dp.def_minute
            AND (e3.minute > dp.def_minute OR e3.second > dp.def_second)
        ),

        rw_pass AS (
            SELECT 
                e4.match_id,
                e4.possession,
                e4.team_name,
                e4.minute as rw_minute,
                e4.second as rw_second,
                e4.player_name as rw_name,
                e4.pass_recipient_name as lw_name,
                e4.id as pass_id,
                e4.pass_length as rw_pass_length,
                e4.pass_height as rw_pass_height,
                rp.*
            FROM pass_sequence e4
            JOIN rb_pass rp 
                ON e4.match_id = rp.match_id 
                AND e4.possession = rp.possession
                AND e4.player_name = rp.rw_name
            WHERE e4.pass_outcome IS NULL
            AND e4.minute >= rp.rb_minute
            AND (e4.minute > rp.rb_minute OR e4.second > rp.rb_second)
        ),

        lw_shot AS (
            SELECT 
                e5.match_id,
                e5.possession,
                json_extract(json(e5.team), '$.name') as team_name,
                e5.minute as shot_minute,
                e5.second as shot_second,
                json_extract(json(e5.player), '$.name') as lw_name,
                json_extract(json(e5.shot), '$.outcome.name') as shot_outcome,
                e5.id as shot_id,
                CAST(json_extract(json(e5.shot), '$.statsbomb_xg') AS FLOAT) as xg,
                json_extract(json(e5.shot), '$.first_time') as first_time_shot,
                rwp.*
            FROM events e5
            JOIN rw_pass rwp 
                ON e5.match_id = rwp.match_id 
                AND e5.possession = rwp.possession
                AND json_extract(json(e5.player), '$.name') = rwp.lw_name
            WHERE json_extract(json(e5.type), '$.name') = 'Shot'
            AND e5.minute >= rwp.rw_minute
            AND (e5.minute > rwp.rw_minute OR e5.second > rwp.rw_second)
        )

        SELECT 
            ls.team_name,
            m.competition_stage_name,
            m.home_team_name,
            m.away_team_name,
            -- Sequence timing
            ls.gk_minute || ':' || ls.gk_second as sequence_start,
            ls.shot_minute || ':' || ls.shot_second as sequence_end,
            -- Player sequence
            ls.gk_name as "1. Goalkeeper",
            ls.defender_name as "2. Defender",
            ls.rb_name as "3. Right Back",
            ls.rw_name as "4. Right Winger",
            ls.lw_name as "5. Left Winger (Scorer)",
            -- Pass details
            ls.gk_pass_height as "GK Pass Type",
            ls.gk_pass_length as "GK Pass Length",
            ls.def_pass_height as "DEF Pass Type",
            ls.def_pass_length as "DEF Pass Length",
            ls.rb_pass_height as "RB Pass Type",
            ls.rb_pass_length as "RB Pass Length",
            ls.rw_pass_height as "RW Pass Type",
            ls.rw_pass_length as "RW Pass Length",
            -- Shot details
            ls.xg as "Expected Goals",
            CASE WHEN ls.first_time_shot = 'true' THEN 'Yes' ELSE 'No' END as "First Time Shot"
        FROM lw_shot ls
        JOIN matches m ON ls.match_id = m.match_id
        WHERE ls.shot_outcome = 'Goal'
        ORDER BY ls.match_id, ls.shot_minute, ls.shot_second;
        """
    else:
        sql_query = """
        WITH pass_sequence AS (
            SELECT 
                e.id,
                e.match_id,
                e.possession,
                json_extract(json(e.team), '$.name') as team_name,
                e.minute,
                e.second,
                json_extract(json(e.player), '$.name') as player_name,
                json_extract(json(e.position), '$.name') as position_name,
                json_extract(json(e.pass), '$.recipient.name') as pass_recipient_name,
                CAST(json_extract(json(e.pass), '$.length') AS FLOAT) as pass_length,
                json_extract(json(e.pass), '$.height.name') as pass_height,
                json_extract(json(e.pass), '$.outcome.name') as pass_outcome,
                json_extract(json(e.type), '$.name') as event_type
            FROM events e
            WHERE json_extract(json(e.type), '$.name') = 'Pass'
        ),
        
        goalkeeper_pass AS (
            SELECT 
                e1.match_id,
                e1.possession,
                e1.team_name,
                e1.minute as gk_minute,
                e1.second as gk_second,
                e1.player_name as gk_name,
                e1.pass_recipient_name as next_player_name,
                e1.id as pass_id,
                e1.pass_length as gk_pass_length,
                e1.pass_height as gk_pass_height
            FROM pass_sequence e1
            WHERE e1.position_name LIKE '%Goalkeeper%'
            AND e1.pass_outcome IS NULL
        ),

        second_pass AS (
            SELECT 
                e2.match_id,
                e2.possession,
                e2.team_name,
                e2.minute as second_minute,
                e2.second as second_second,
                e2.player_name as second_player_name,
                e2.position_name as second_position,
                e2.pass_recipient_name as third_player_name,
                e2.id as pass_id,
                e2.pass_length as second_pass_length,
                e2.pass_height as second_pass_height,
                gp.gk_name,
                gp.gk_minute,
                gp.gk_second,
                gp.gk_pass_length,
                gp.gk_pass_height
            FROM pass_sequence e2
            JOIN goalkeeper_pass gp 
                ON e2.match_id = gp.match_id 
                AND e2.possession = gp.possession
                AND e2.player_name = gp.next_player_name
            WHERE e2.pass_outcome IS NULL
            AND (e2.position_name LIKE '%Back%' OR e2.position_name LIKE '%Center Back%' OR e2.position_name LIKE '%Defence%')
            AND e2.minute >= gp.gk_minute
            AND (e2.minute > gp.gk_minute OR e2.second > gp.gk_second)
        ),

        third_pass AS (
            SELECT 
                e3.match_id,
                e3.possession,
                e3.team_name,
                e3.minute as third_minute,
                e3.second as third_second,
                e3.player_name as third_player_name,
                e3.position_name as third_position,
                e3.pass_recipient_name as fourth_player_name,
                e3.id as pass_id,
                e3.pass_length as third_pass_length,
                e3.pass_height as third_pass_height,
                sp.*
            FROM pass_sequence e3
            JOIN second_pass sp 
                ON e3.match_id = sp.match_id 
                AND e3.possession = sp.possession
                AND e3.player_name = sp.third_player_name
            WHERE e3.pass_outcome IS NULL
            AND e3.minute >= sp.second_minute
            AND (e3.minute > sp.second_minute OR e3.second > sp.second_second)
        ),

        fourth_pass AS (
            SELECT 
                e4.match_id,
                e4.possession,
                e4.team_name,
                e4.minute as fourth_minute,
                e4.second as fourth_second,
                e4.player_name as fourth_player_name,
                e4.position_name as fourth_position,
                e4.pass_recipient_name as final_player_name,
                e4.id as pass_id,
                e4.pass_length as fourth_pass_length,
                e4.pass_height as fourth_pass_height,
                tp.*
            FROM pass_sequence e4
            JOIN third_pass tp 
                ON e4.match_id = tp.match_id 
                AND e4.possession = tp.possession
                AND e4.player_name = tp.fourth_player_name
            WHERE e4.pass_outcome IS NULL
            AND e4.minute >= tp.third_minute
            AND (e4.minute > tp.third_minute OR e4.second > tp.third_second)
        ),

        final_shot AS (
            SELECT 
                e5.match_id,
                e5.possession,
                json_extract(json(e5.team), '$.name') as team_name,
                e5.minute as shot_minute,
                e5.second as shot_second,
                json_extract(json(e5.player), '$.name') as scorer_name,
                json_extract(json(e5.position), '$.name') as scorer_position,
                json_extract(json(e5.shot), '$.outcome.name') as shot_outcome,
                e5.id as shot_id,
                CAST(json_extract(json(e5.shot), '$.statsbomb_xg') AS FLOAT) as xg,
                json_extract(json(e5.shot), '$.first_time') as first_time_shot,
                fp.*
            FROM events e5
            JOIN fourth_pass fp 
                ON e5.match_id = fp.match_id 
                AND e5.possession = fp.possession
                AND json_extract(json(e5.player), '$.name') = fp.final_player_name
            WHERE json_extract(json(e5.type), '$.name') = 'Shot'
            AND e5.minute >= fp.fourth_minute
            AND (e5.minute > fp.fourth_minute OR e5.second > fp.fourth_second)
        )

        SELECT 
            fs.team_name,
            m.competition_stage_name,
            m.home_team_name,
            m.away_team_name,
            -- Sequence timing
            fs.gk_minute || ':' || fs.gk_second as sequence_start,
            fs.shot_minute || ':' || fs.shot_second as sequence_end,
            -- Player sequence
            fs.gk_name as "1. Goalkeeper",
            fs.second_player_name as "2. Player",
            fs.second_position as "2. Position",
            fs.third_player_name as "3. Player",
            fs.third_position as "3. Position",
            fs.fourth_player_name as "4. Player",
            fs.fourth_position as "4. Position",
            fs.scorer_name as "5. Scorer",
            fs.scorer_position as "5. Position",
            -- Pass details
            fs.gk_pass_height as "GK Pass Type",
            fs.gk_pass_length as "GK Pass Length",
            fs.second_pass_height as "2nd Pass Type",
            fs.second_pass_length as "2nd Pass Length",
            fs.third_pass_height as "3rd Pass Type",
            fs.third_pass_length as "3rd Pass Length",
            fs.fourth_pass_height as "4th Pass Type",
            fs.fourth_pass_length as "4th Pass Length",
            -- Shot details
            fs.xg as "Expected Goals",
            CASE WHEN fs.first_time_shot = 'true' THEN 'Yes' ELSE 'No' END as "First Time Shot"
        FROM final_shot fs
        JOIN matches m ON fs.match_id = m.match_id
        WHERE fs.shot_outcome = 'Goal'
        ORDER BY fs.match_id, fs.shot_minute, fs.shot_second;
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
    print("\nFlexible position matching:")
    glauco_example(strict=False) 