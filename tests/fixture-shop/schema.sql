-- fixture-shop schema. SQLite dialect; nothing here needs a real database to be audited.

CREATE TABLE settings (
    name  TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT INTO settings VALUES ('payment_window_hours', '48');
INSERT INTO settings VALUES ('cod_enabled', '0');            -- shop policy: no cash on delivery
INSERT INTO settings VALUES ('pickup_hold_days', '7');

CREATE TABLE shipping_chains (
    chain    TEXT PRIMARY KEY,                                -- '711', 'FAMI', 'HILIFE', 'OK'
    enabled  INTEGER NOT NULL DEFAULT 1
);
INSERT INTO shipping_chains VALUES ('711', 1), ('FAMI', 1), ('HILIFE', 0), ('OK', 0);

CREATE TABLE orders (
    id                INTEGER PRIMARY KEY,
    status            TEXT NOT NULL,        -- pending, paid, expired, shipped, pickup_ready,
                                            -- picked_up, returned_uncollected, cancelled
    total             INTEGER NOT NULL,     -- TWD, whole units
    shipping_method   TEXT NOT NULL,        -- 'courier', 'cvs_pickup', 'cvs_pickup_cod'
    chain             TEXT,
    payment_deadline  TEXT,                 -- ISO-8601, frozen at placement
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    paid_at           TEXT,
    gateway_ref       TEXT,
    reminder_sent_at  TEXT
);

CREATE TABLE gateway_events (
    id          INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL,
    provider_tx TEXT NOT NULL UNIQUE,       -- verified control: one provider tx, one row
    payload     TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE TABLE job_heartbeats (
    job      TEXT PRIMARY KEY,
    last_run TEXT NOT NULL
);
