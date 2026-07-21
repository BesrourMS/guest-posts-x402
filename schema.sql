-- Run once against your D1 database, e.g.:
--   wrangler d1 execute trovit_guest_posts --file=schema.sql --remote

CREATE TABLE IF NOT EXISTS submissions (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    author          TEXT NOT NULL,
    canonical_url   TEXT,
    status          TEXT NOT NULL DEFAULT 'pending_review',  -- pending_review | approved | rejected
    payer_address   TEXT,
    payment_tx_hash TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions(created_at);
