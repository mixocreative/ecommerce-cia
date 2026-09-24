-- fixture-shop-live — the schema the live fixture runs on.
-- SQLite, because the fixture must start with one command and no service.

CREATE TABLE products (
    sku         TEXT PRIMARY KEY,
    parent_sku  TEXT,                      -- NULL for a standalone product or a parent
    title       TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    stock       INTEGER NOT NULL
);

-- The storefront reads this, not products.stock. Refreshed by Jobs/RefreshStockCache.
CREATE TABLE stock_cache (
    sku         TEXT PRIMARY KEY,
    qty         INTEGER NOT NULL,
    refreshed_at TEXT NOT NULL
);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sku          TEXT NOT NULL,
    qty          INTEGER NOT NULL,
    total_cents  INTEGER NOT NULL,
    status       TEXT NOT NULL,            -- pending | paid | declined | expired | cancelled | refunded
    email        TEXT NOT NULL,
    placed_at    TEXT NOT NULL,
    deadline_at  TEXT NOT NULL,
    paid_at      TEXT,
    refunded_at  TEXT
);

CREATE TABLE gateway_events (
    event_id   TEXT PRIMARY KEY,           -- the provider's own id; the idempotency key
    order_id   INTEGER NOT NULL,
    result     TEXT NOT NULL,              -- paid | declined
    received_at TEXT NOT NULL
);

CREATE TABLE notices (                     -- what a person is told; the shop's only surface for refusals
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    audience  TEXT NOT NULL,               -- customer | operator
    order_id  INTEGER,
    body      TEXT NOT NULL,
    created_at TEXT NOT NULL
);
