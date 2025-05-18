-- Create dimension tables
CREATE TABLE IF NOT EXISTS DimMatch (
    match_id TEXT PRIMARY KEY,
    match_date TEXT,
    kick_off TEXT,
    competition_id INTEGER,
    competition_name TEXT,
    season_id INTEGER,
    season_name TEXT,
    home_team_id TEXT,
    home_team_name TEXT,
    away_team_id TEXT,
    away_team_name TEXT
);

CREATE TABLE IF NOT EXISTS DimPlayer (
    player_id TEXT PRIMARY KEY,
    player_name TEXT,
    current_team_id TEXT
);

CREATE TABLE IF NOT EXISTS DimTeam (
    team_id TEXT PRIMARY KEY,
    team_name TEXT,
    team_gender TEXT,
    team_group TEXT,
    country_id INTEGER,
    country_name TEXT
);

CREATE TABLE IF NOT EXISTS DimPeriod (
    period_id INTEGER PRIMARY KEY,
    period_name TEXT
);

-- Create fact table with foreign key constraints
CREATE TABLE IF NOT EXISTS FactEvents (
    event_id TEXT PRIMARY KEY,
    match_id TEXT,
    player_id TEXT,
    team_id TEXT,
    timestamp TEXT,
    period_id INTEGER,
    location_x REAL,
    location_y REAL,
    event_type TEXT,
    possession_id INTEGER,
    duration REAL,
    FOREIGN KEY (match_id) REFERENCES DimMatch(match_id),
    FOREIGN KEY (player_id) REFERENCES DimPlayer(player_id),
    FOREIGN KEY (team_id) REFERENCES DimTeam(team_id),
    FOREIGN KEY (period_id) REFERENCES DimPeriod(period_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_events_match ON FactEvents(match_id);
CREATE INDEX IF NOT EXISTS idx_events_player ON FactEvents(player_id);
CREATE INDEX IF NOT EXISTS idx_events_team ON FactEvents(team_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON FactEvents(event_type);
CREATE INDEX IF NOT EXISTS idx_events_period ON FactEvents(period_id); 