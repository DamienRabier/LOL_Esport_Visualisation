-- Table des équipes
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    region TEXT,
    foundation DATE
);

-- Table des joueurs
CREATE TABLE players (
    player_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    join_date DATE,
    current_team_id INT REFERENCES teams(team_id),
    country TEXT,
    role TEXT
);

-- Table des champions
CREATE TABLE champions (
    champion_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Table des parties (games)
CREATE TABLE games (
    game_id SERIAL PRIMARY KEY,
    date TIMESTAMP,
    blue_team_id INT REFERENCES teams(team_id),
    red_team_id INT REFERENCES teams(team_id),
    winner_team_id INT REFERENCES teams(team_id),
    duration_minutes FLOAT,
    patch TEXT,
    tournament TEXT
);

-- Table des statistiques des joueurs en match
CREATE TABLE player_stats (
    player_id INT REFERENCES players(player_id),
    game_id INT REFERENCES games(game_id),
    team_id INT REFERENCES teams(team_id),
    champion_id INT REFERENCES champions(champion_id),
    kills INT,
    deaths INT,
    assists INT,
    cs INT,
    gold INT,
    kda FLOAT,
    position TEXT,
    PRIMARY KEY (player_id, game_id)
);
