CREATE TABLE IF NOT EXISTS user (
    id INT AUTOINCREMENT,
    username TEXT UNQIUE NOT NULL,
    hash TEXT NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS save (
    id INT AUTOINCREMENT,
    user_id INT NOT NULL,
    save_number INT NOT NULL,
    save_name TEXT,
    ruleset INT NOT NULL,
    route_tracking INT,
    current_status INT,
    PRIMARY KEY (id),
    FOREIGN KEY user_id REFERENCES user(id)
);

CREATE TABLE IF NOT EXISTS player (
    id INT AUTOINCREMENT,
    save_id INT NOT NULL,
    player_number INT NOT NULL,
    player_name TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY save_id REFERENCES save(id)
);

CREATE TABLE IF NOT EXISTS pokemon (
    id INT AUTOINCREMENT,
    player_id INT NOT NULL,
    pokedex_id INT NOT NULL,
    sprite_id INT NOT NULL,
    soul_link_id INT,
    nickname TEXT,
    position TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY player_id REFERENCES player(id),
    FOREIGN KEY pokedex_id REFERENCES pokedex(id),
    FOREIGN KEY sprite_id REFERENCES sprite(id),
    FOREIGN KEY soul_link_id REFERENCES soul_link(id)
);

CREATE TABLE IF NOT EXISTS soul_link (
    id INT AUTOINCREMENT,
    soul_link_number INT NOT NULL,
    position TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS route (
    id INT AUTOINCREMENT,
    pokemon_id INT NOT NULL,
    route_list_id INT NOT NULL,
    complete INT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY pokemon_id REFERENCES pokemon(id),
    FOREIGN KEY route_list_id REFERENCES route_list(id)
);

CREATE TABLE IF NOT EXISTS route_list (
    id INT AUTOINCREMENT,
    name TEXT NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS pokedex (
    id INT AUTOINCREMENT,
    number INT NOT NULL,
    species TEXT NOT NULL,
    type_primary TEXT NOT NULL,
    type_secondary TEXT,
    family INT NOT NULL,
    family_order INT NOT NULL,
    name_1 TEXT,
    name_2 TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS pokedex_stats (
    id INT AUTOINCREMENT,
    pokedex_id INT NOT NULL,
    hp INT NOT NULL,
    attack INT NOT NULL,
    defense INT NOT NULL,
    sp_attack INT NOT NULL,
    sp_defense INT NOT NULL,
    speed INT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY pokedex_id REFERENCES pokedex(id)
);

CREATE TABLE IF NOT EXISTS sprite (
    id INT AUTOINCREMENT,
    variant_let TEXT NOT NULL,
    pokedex_id INT,
    artist_id INT,
    PRIMARY KEY (id),
    FOREIGN KEY pokedex_id REFERENCES pokedex(id),
    FOREIGN KEY artist_id REFERENCES artist(id)
);

CREATE TABLE IF NOT EXISTS artist (
    id INT AUTOINCREMENT,
    name TEXT NOT NULL,
    PRIMARY KEY (id)
);