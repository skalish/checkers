-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS game;
DROP TABLE IF EXISTS move;
DROP TABLE IF EXISTS piece;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  game_id INTEGER,
  FOREIGN KEY (game_id) REFERENCES game (id)
);

CREATE TABLE game (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player1_id INTEGER,
  player2_id INTEGER,
  player_turn INTEGER DEFAULT 1
);

CREATE TABLE piece (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL,
  game_id INTEGER NOT NULL,
  ingame_id INTEGER NOT NULL,
  position TEXT NOT NULL,
  king INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (player_id) REFERENCES user (id),
  FOREIGN KEY (game_id) REFERENCES game (id)
);

CREATE TABLE move (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL,
  game_id INTEGER NULL,
  piece_id INTEGER NOT NULL,
  position_before TEXT NOT NULL,
  position_after TEXT NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (player_id) REFERENCES user (id),
  FOREIGN KEY (game_id) REFERENCES game (id),
  FOREIGN KEY (piece_id) REFERENCES piece (id)
);


