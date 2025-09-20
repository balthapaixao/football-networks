import sqlite3
from database_manager import FootballDatabaseManager

def print_schema():
    db_manager = FootballDatabaseManager()
    conn = db_manager.get_connection()
    
    try:
        cursor = conn.cursor()
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\nAvailable tables:")
        for table in tables:
            print(f"\n{table[0]} table schema:")
            cursor.execute(f"PRAGMA table_info({table[0]});")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
    except Exception as e:
        print(f"Error getting schema: {str(e)}")
    finally:
        conn.close()

def query_sequence():
    db_manager = FootballDatabaseManager()
    conn = db_manager.get_connection()
    
    query = """
    WITH defender_to_midfield AS (
        -- First pass: Defender to midfielder
        SELECT 
            e1.match_id,
            e1.possession_id,
            e1.timestamp as first_pass_time,
            e1.player_id as defender_id,
            e1.team_id as team_id,
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
        fs.match_id,
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
    
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Print column names
        columns = [description[0] for description in cursor.description]
        print("\nColumns:", columns)
        
        # Print results
        print("\nResults:")
        for row in results:
            print(row)
            
    except Exception as e:
        print(f"Error executing query: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    print_schema()
    query_sequence() 