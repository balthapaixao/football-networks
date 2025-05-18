# Football Play Sequence Analysis Tutorial

This tutorial explains how to query and analyze football play sequences using the Statsbomb database.

## Database Schema Reference

### Fact Table: FactEvents
Contains all match events with their locations, timings, and relationships:
- `event_id` (TEXT, PK)
- `match_id` (TEXT, FK)
- `player_id` (TEXT, FK)
- `team_id` (TEXT, FK)
- `timestamp` (TEXT)
- `period_id` (INTEGER, FK)
- `location_x` (REAL) - X coordinate on the pitch
- `location_y` (REAL) - Y coordinate on the pitch
- `event_type` (TEXT)
- `possession_id` (INTEGER)
- `duration` (REAL)

### Dimension Tables
- `DimMatch`: Match details and teams
- `DimPlayer`: Player information
- `DimTeam`: Team details
- `DimPeriod`: Game periods

## Available Event Types
```sql
SELECT DISTINCT event_type FROM FactEvents;
```
Key events include:
- Pass
- Shot
- Ball Receipt*
- Carry
- Goal Keeper
- Dribble
- Pressure
- Ball Recovery
- Interception
- Block
- Clearance

## Understanding Pitch Coordinates

The pitch uses a coordinate system where:
- `location_x`: 0 to 120 (length)
- `location_y`: 0 to 80 (width)
- Origin (0,0): Top-left corner
- (120,80): Bottom-right corner

Common pitch zones:
- Left Wing: x ∈ [0,120], y ∈ [0,20]
- Center: x ∈ [0,120], y ∈ [20,60]
- Right Wing: x ∈ [0,120], y ∈ [60,80]
- Defensive Third: x ∈ [0,40]
- Middle Third: x ∈ [40,80]
- Attacking Third: x ∈ [80,120]

## Querying Play Sequences

When translating natural language to SQL queries, consider these aspects:

### 1. Event Sequence Tracking
- Use `possession_id` to group related events
- Order by `timestamp` within possessions
- Link consecutive events using window functions

### 2. Position Analysis
- Use `location_x` and `location_y` to determine pitch positions
- Consider both absolute and relative positions
- Account for team's playing direction

### 3. Player Roles
- Join with `DimPlayer` for player information
- Use event types to identify roles (e.g., 'Goal Keeper')
- Track player movements between events

### 4. Team Context
- Join with `DimTeam` for team details
- Consider home/away status from `DimMatch`
- Account for team strategies and formations

## Query Examples

### Example 1: Goalkeeper to Left Wing
Natural Language:
> "Find all plays where the goalkeeper passes to a player on the left wing"

SQL Translation:
```sql
WITH possession_sequence AS (
    SELECT 
        e1.match_id,
        e1.possession_id,
        e1.timestamp as gk_time,
        e2.timestamp as receiver_time,
        p1.player_name as goalkeeper,
        p2.player_name as receiver,
        e2.location_y as receive_y
    FROM FactEvents e1
    JOIN FactEvents e2 
        ON e1.possession_id = e2.possession_id
        AND e1.match_id = e2.match_id
    JOIN DimPlayer p1 ON e1.player_id = p1.player_id
    JOIN DimPlayer p2 ON e2.player_id = p2.player_id
    WHERE e1.event_type = 'Goal Keeper'
    AND e2.event_type = 'Ball Receipt*'
    AND e2.timestamp > e1.timestamp
    -- Left wing coordinates
    AND e2.location_y BETWEEN 0 AND 20
)
SELECT * FROM possession_sequence
ORDER BY gk_time;
```

### Example 2: Build-up Through Center
Natural Language:
> "Show all possessions with at least 3 consecutive passes in the middle third"

SQL Translation:
```sql
WITH consecutive_passes AS (
    SELECT 
        match_id,
        possession_id,
        COUNT(*) as pass_count
    FROM FactEvents
    WHERE event_type = 'Pass'
    AND location_x BETWEEN 40 AND 80
    GROUP BY match_id, possession_id
    HAVING COUNT(*) >= 3
)
SELECT 
    m.match_date,
    m.competition_name,
    t.team_name,
    cp.pass_count
FROM consecutive_passes cp
JOIN DimMatch m ON cp.match_id = m.match_id
JOIN FactEvents e ON cp.match_id = e.match_id 
    AND cp.possession_id = e.possession_id
JOIN DimTeam t ON e.team_id = t.team_id
GROUP BY cp.match_id, cp.possession_id;
```

## Tips for Query Construction

1. **Start Simple**
   - Begin with basic event filtering
   - Add complexity incrementally
   - Test each addition separately

2. **Performance Optimization**
   - Use appropriate indexes
   - Filter early in CTEs
   - Avoid unnecessary joins

3. **Common Patterns**
   - Track possession changes
   - Follow player movements
   - Analyze team formations

4. **Validation**
   - Check event sequences make sense
   - Verify coordinate ranges
   - Confirm team possession logic

## Advanced Analysis

### Possession Chains
```sql
SELECT 
    possession_id,
    GROUP_CONCAT(event_type, ' -> ') as chain
FROM FactEvents
GROUP BY possession_id
ORDER BY possession_id;
```

### Player Movement Tracking
```sql
SELECT 
    player_id,
    AVG(location_x) as avg_x,
    AVG(location_y) as avg_y,
    COUNT(*) as events
FROM FactEvents
GROUP BY player_id;
```

### Team Patterns
```sql
SELECT 
    team_id,
    event_type,
    COUNT(*) as frequency,
    AVG(location_x) as avg_x,
    AVG(location_y) as avg_y
FROM FactEvents
GROUP BY team_id, event_type;
```

## Next Steps

1. Experiment with different play patterns
2. Combine multiple event sequences
3. Add temporal analysis
4. Incorporate match context
5. Analyze success rates

Remember to adjust coordinates and thresholds based on your specific analysis needs.