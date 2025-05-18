-- Create dimension tables
CREATE TABLE IF NOT EXISTS DimMatch (
    match_id INTEGER PRIMARY KEY,
    competition_id INTEGER,
    season_id INTEGER,
    home_team_id INTEGER,
    away_team_id INTEGER,
    match_date DATE
);

CREATE TABLE IF NOT EXISTS DimPlayer (
    player_id INTEGER PRIMARY KEY,
    player_name TEXT,
    current_team_id INTEGER,
    position TEXT
);

CREATE TABLE IF NOT EXISTS DimTeam (
    team_id INTEGER PRIMARY KEY,
    team_name TEXT,
    country TEXT
);

CREATE TABLE IF NOT EXISTS DimEventType (
    event_type_id INTEGER PRIMARY KEY,
    event_name TEXT,
    event_category TEXT
);

CREATE TABLE IF NOT EXISTS DimPeriod (
    period_id INTEGER PRIMARY KEY,
    period_name TEXT
);

-- Create fact table with foreign key constraints
CREATE TABLE IF NOT EXISTS FactEvents (
    event_id INTEGER PRIMARY KEY,
    match_id INTEGER,
    player_id INTEGER,
    team_id INTEGER,
    timestamp DATETIME,
    period_id INTEGER,
    location_x FLOAT,
    location_y FLOAT,
    event_type_id INTEGER,
    possession_id INTEGER,
    duration FLOAT,
    FOREIGN KEY (match_id) REFERENCES DimMatch(match_id),
    FOREIGN KEY (player_id) REFERENCES DimPlayer(player_id),
    FOREIGN KEY (team_id) REFERENCES DimTeam(team_id),
    FOREIGN KEY (period_id) REFERENCES DimPeriod(period_id),
    FOREIGN KEY (event_type_id) REFERENCES DimEventType(event_type_id)
);

-- Create indexes for better query performance
CREATE INDEX idx_events_match ON FactEvents(match_id);
CREATE INDEX idx_events_player ON FactEvents(player_id);
CREATE INDEX idx_events_team ON FactEvents(team_id);
CREATE INDEX idx_events_event_type ON FactEvents(event_type_id);
CREATE INDEX idx_events_possession ON FactEvents(possession_id); 