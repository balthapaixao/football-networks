# SQL Translation Prompt for Football Play Sequences

Use the following prompt when asking an AI to translate natural language football play descriptions into SQL queries:

```
I have a football events database with Statsbomb data that follows this schema:

Tables:
1. FactEvents:
   - event_id (TEXT, PK)
   - match_id (TEXT, FK)
   - player_id (TEXT, FK)
   - team_id (TEXT, FK)
   - timestamp (TEXT)
   - period_id (INTEGER, FK)
   - location_x (REAL) - X coordinate on the pitch
   - location_y (REAL) - Y coordinate on the pitch
   - event_type (TEXT)
   - possession_id (INTEGER)
   - duration (REAL)

2. DimMatch:
   - match_id (TEXT, PK)
   - match_date (TEXT)
   - kick_off (TEXT)
   - competition_id (INTEGER)
   - competition_name (TEXT)
   - season_id (INTEGER)
   - season_name (TEXT)
   - home_team_id (TEXT)
   - home_team_name (TEXT)
   - away_team_id (TEXT)
   - away_team_name (TEXT)

3. DimPlayer:
   - player_id (TEXT, PK)
   - player_name (TEXT)
   - current_team_id (TEXT)

4. DimTeam:
   - team_id (TEXT, PK)
   - team_name (TEXT)
   - team_gender (TEXT)
   - team_group (TEXT)
   - country_id (INTEGER)
   - country_name (TEXT)

5. DimPeriod:
   - period_id (INTEGER, PK)
   - period_name (TEXT)

Available event types:
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
(and others)

The pitch coordinates are:
- location_x: 0 to 120 (length of the pitch)
- location_y: 0 to 80 (width of the pitch)
- (0,0) is top-left corner
- (120,80) is bottom-right corner

Common pitch zones:
- Left Wing: y ∈ [0,20]
- Center: y ∈ [20,60]
- Right Wing: y ∈ [60,80]
- Defensive Third: x ∈ [0,40]
- Middle Third: x ∈ [40,80]
- Attacking Third: x ∈ [80,120]

I need you to act as a SQL query translator. I will describe football play sequences in natural language, and you should translate them into SQL queries that will find these sequences in the database.

For example, if I say "I want to find all plays where the goalkeeper passes to a player on the left wing", you should create a SQL query that:
1. Finds sequences of events within the same possession
2. Considers the pitch coordinates to determine positions
3. Links the relevant dimension tables to get player and team information
4. Orders events by timestamp within each possession

Please provide the SQL query and explain how it works. Feel free to ask clarifying questions if the play description is ambiguous.

My play sequence request is: [YOUR PLAY SEQUENCE DESCRIPTION HERE]
```

## How to Use This Prompt

1. Copy the entire prompt above
2. Replace `[YOUR PLAY SEQUENCE DESCRIPTION HERE]` with your specific play sequence request
3. Send it to the AI

## Example Play Sequence Requests

Here are some example requests you can use:

1. "Find all sequences where a team completes at least 5 passes in the attacking third"
2. "Show me counter-attacks that start with a ball recovery in the defensive third and end with a shot within 15 seconds"
3. "Find plays where a team switches play from one wing to the other with a single pass"
4. "Show all build-up sequences that start from the goalkeeper and involve at least 3 different players in the defensive third"
5. "Find instances where a team recovers the ball in the middle third and immediately launches a counter-attack"

## Tips for Good Requests

1. **Be Specific**
   - Mention specific pitch areas
   - Include number of players/passes if relevant
   - Specify time constraints if applicable

2. **Consider Events**
   - Use events that exist in the database
   - Think about sequence of events
   - Include relevant player roles

3. **Think About Context**
   - Mention team context if important
   - Consider match situations
   - Include tactical elements if relevant

4. **Clarify Success Criteria**
   - Define what makes a sequence successful
   - Specify any required outcomes
   - Include any specific conditions

## Common Analysis Patterns

1. **Build-up Play**
   ```
   "Find sequences starting with the goalkeeper where the team completes at least 
   4 passes in their own half before entering the attacking third"
   ```

2. **Pressing Success**
   ```
   "Show instances where a team applies pressure in the attacking third and 
   recovers the ball within 5 seconds"
   ```

3. **Wing Play**
   ```
   "Find sequences where a team progresses from their defensive third to the 
   attacking third using only the wings (y < 20 or y > 60)"
   ```

4. **Counter-Attacks**
   ```
   "Identify possessions where a team recovers the ball in their defensive third 
   and creates a shot within 10 seconds"
   ```

5. **Positional Play**
   ```
   "Show sequences where a team completes at least 8 passes while maintaining 
   possession in the middle third of the pitch"
   ``` 