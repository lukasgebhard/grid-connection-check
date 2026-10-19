CREATE TYPE request_status AS ENUM ('pending', 'approved', 'rejected', 'failed');

-- One row per grid; the worker locks these rows, so requests on the same grid are
-- checked one at a time. The IDs must match the domain registry.
CREATE TABLE grids (
    grid_id TEXT PRIMARY KEY
);

INSERT INTO grids (grid_id) VALUES
    ('kerber-landnetz-freileitung-1'),
    ('kerber-vorstadtnetz-kabel-1');

-- Connection points (valid bus_id values) are not stored here; the API validates them
-- against the domain registry. Requests are decided in ascending request_id order.
CREATE TABLE connection_requests (
    request_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    grid_id      TEXT           NOT NULL REFERENCES grids,
    bus_id       INTEGER        NOT NULL,
    p_kw         NUMERIC(8, 2)  NOT NULL CHECK (p_kw > 0 AND p_kw <= 1000),
    status       request_status NOT NULL DEFAULT 'pending',
    submitted_at TIMESTAMPTZ    NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    result       JSONB,
    error        TEXT,
    CHECK ((status = 'pending') = (finished_at IS NULL)),
    CHECK ((status IN ('approved', 'rejected')) = (result IS NOT NULL)),
    CHECK ((status = 'failed') = (error IS NOT NULL))
);

-- Partial indexes for the worker's two lookups. They cover only the rows each lookup
-- needs, so they stay small even when most requests are finished.
-- Finds the oldest pending request of a grid (the next job to check):
CREATE INDEX connection_requests_pending_idx
    ON connection_requests (grid_id, request_id) WHERE status = 'pending';
-- Finds all approved requests of a grid (they are part of every check on that grid):
CREATE INDEX connection_requests_approved_idx
    ON connection_requests (grid_id) WHERE status = 'approved';
