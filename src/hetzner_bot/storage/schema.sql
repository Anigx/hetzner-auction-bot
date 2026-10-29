CREATE TABLE IF NOT EXISTS guilds (
    guild_id    INTEGER PRIMARY KEY,
    channel_id  INTEGER NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS filters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    name          TEXT NOT NULL,
    criteria_json TEXT NOT NULL,
    mention       INTEGER NOT NULL DEFAULT 0,
    active        INTEGER NOT NULL DEFAULT 1,
    baseline_pending INTEGER NOT NULL DEFAULT 0,
    delivery      TEXT NOT NULL DEFAULT 'channel',
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (guild_id, user_id, name)
);

CREATE TABLE IF NOT EXISTS seen (
    filter_id INTEGER NOT NULL,
    server_id INTEGER NOT NULL,
    PRIMARY KEY (filter_id, server_id)
);

CREATE TABLE IF NOT EXISTS posts (
    guild_id       INTEGER NOT NULL,
    server_id      INTEGER NOT NULL,
    last_price_eur TEXT NOT NULL,
    posted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (guild_id, server_id)
);

CREATE TABLE IF NOT EXISTS baselines (
    guild_id    INTEGER NOT NULL,
    server_id   INTEGER NOT NULL,
    price_eur   TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (guild_id, server_id)
);

CREATE TABLE IF NOT EXISTS dm_posts (
    filter_id      INTEGER NOT NULL,
    server_id      INTEGER NOT NULL,
    last_price_eur TEXT NOT NULL,
    posted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (filter_id, server_id)
);

CREATE TABLE IF NOT EXISTS queue (
    guild_id     INTEGER NOT NULL,
    server_id    INTEGER NOT NULL,
    filter_ids   TEXT NOT NULL,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    attempts     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, server_id)
);
