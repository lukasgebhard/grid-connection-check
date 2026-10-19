# Architecture decision records (ADR)

Each ADR states the decision, the assumptions it rests on, and its consequences.
If an assumption stops holding, revisit the record.

## ADR-001 Plain SQL with psycopg, no ORM

**Decision.** The database is accessed with psycopg 3 and hand-written SQL.
No ORM, no query builder, no migration tool; the schema is one init script.

**Assumptions.**

- The data model is small: two tables and a handful of queries.
- The job queue relies on exact locking and transaction semantics, which must be visible in the code.
- Every database is built from scratch, so there is no data to migrate.

**Consequences.**

- Queries run exactly as written and can be pasted into `psql`.
- Only the tests against a real database (ADR-002) catch SQL errors.
- API and worker each have their own small query module.

## ADR-002 Integration tests against a throwaway database

**Decision.** Tests run against a real PostgreSQL, without mocks.
Each test run creates a fresh database from the schema and drops it afterwards.
Tests commit for real; each test that needs the database starts from an empty request table.

**Assumptions.**

- Hand-written SQL can only be verified against a real database.
- Tests have their own connection settings and never have access to the app's database.
- The worker must see committed data and really commit or roll back its own transactions,
  so rolling back after each test is not an option for worker tests.

**Consequences.**

- Tests cannot damage real data, and every run also checks that the schema builds from scratch.
- API and worker are tested with the same transaction behaviour as in production.
- After a failing test, its data remains in the database for inspection.
- Tests that use the database can't run in parallel against the same database.
- Running the tests requires a PostgreSQL server on which the test user may create databases.

## ADR-003 A single worst case and simplified criteria

**Decision.** Each request is checked in one static snapshot: no load, and all approved plus
the requested PV systems at full output. The request is rejected if the voltage, the voltage
rise caused by generation, or the loading of a line or the transformer exceeds its limit
anywhere in the grid, or if the load flow doesn't converge.

**Assumptions.**

- For PV, the critical situation is high generation with low consumption. No load at all
  bounds it from the safe side.
- The same limits apply to all elements.

**Consequences.**

- The check is conservative: it can reject requests that a time-series analysis, reactive
  power control or curtailment would allow.
- Every verdict is reproducible and explainable: the result lists every violation with
  element, value and limit, not just the first one.
- Each check runs two load flows (with and without generation).
- The remaining simplifications are listed in the README under limitations.

## ADR-004 PostgreSQL as the job queue

**Decision.** There is no message broker. A submitted request is a row with status `pending`,
and that row is the job. Workers poll the database and claim work with
`SELECT … FOR UPDATE SKIP LOCKED` on the row of a grid that has pending requests.

**Assumptions.**

- Request volume is low: a check takes tens of milliseconds, and requests arrive far less often.
- A delay of up to one polling interval (1 s) before a check starts is acceptable.
- The request has to be stored in the database anyway, together with its result.

**Consequences.**

- One service less to run, monitor and secure.
- Submitting is a single `INSERT`. There is no second system to keep consistent with the
  database, so no outbox or dual-write problem.
- Claiming a job and storing its verdict happen in the same database transaction (ADR-005).
- Idle workers send one cheap query per second each.
- Throughput is bounded by the database, which is far beyond what this use case needs.

## ADR-005 The job transaction stays open during the load flow

**Decision.** A worker claims the grid, reads the requests, runs the load flow and writes the
verdict in one database transaction. Nothing is committed before the verdict, so there is no
visible `running` status.

**Assumptions.**

- A check takes well under a second, so holding a row lock and an open transaction for that
  long costs nothing.
- When a worker process or its connection dies, PostgreSQL rolls back its transaction and
  releases its locks.

**Consequences.**

- Crash safety without extra machinery: if a worker dies mid-job, its request is still
  `pending`, its grid is unlocked, and another worker picks it up. There are no leases,
  heartbeats or cleanup jobs.
- Clients can't tell a waiting request from one being checked; both are `pending`.
- A hung worker would block its grid. A session timeout for idle transactions (60 s) ends
  its session and releases the lock.
- A request that kills the worker every time (a poison pill) is retried forever and blocks
  its grid, because it stays the oldest pending request. Counting attempts would require a
  commit outside the job transaction. A check that merely raises an exception is not a
  poison pill: it is stored as `failed`.

## ADR-006 Async API, synchronous worker

**Decision.** The API is asynchronous (FastAPI with an async connection pool).
The worker is plain synchronous code that handles one job at a time; it scales by running
more worker processes.

**Assumptions.**

- The API only runs short queries, so its work is waiting on I/O. Async handles many
  concurrent clients with few resources.
- The worker's work is CPU-bound (the load flow). Async doesn't speed that up, and Python
  threads wouldn't run it in parallel either.
- The worker's correctness depends on where its transaction starts and ends, which is
  easiest to see in straight-line code.

**Consequences.**

- API and worker use the async and the sync psycopg interface; each has its own query module.
- Worker capacity is set by the number of processes (`docker compose up --scale worker=3`),
  each with one database connection.
- The API also loads the grid models, to validate connection points before a request is stored.

## ADR-007 One request at a time per grid, grids in parallel

**Decision.** A worker locks the row of a grid for the whole job and checks only the oldest
pending request of that grid. Other workers skip locked grids and take another one.

**Assumptions.**

- Whether a request is approved depends on all requests approved before it on the same grid.
  If two requests on one grid were checked at the same time, neither would see the other,
  and both could be approved although together they overload the grid.
  Locking each request instead of the grid would allow exactly this.
- Requests on different grids don't affect each other: each low-voltage grid has its own
  transformer, and the upstream grid is assumed to be stiff.
- "First come, first served" is the fair order within a grid.

**Consequences.**

- No grid is ever overbooked by concurrent checks, and each grid decides its requests in
  submission order.
- Parallelism is bounded by the number of grids with pending requests; additional workers idle.
- Within one grid, checks run one after another, each taking tens of milliseconds.
- Across grids there is no fairness: workers always take the first free grid in alphabetical
  order, so with fewer workers than busy grids, a long backlog on one grid delays the grids
  sorted after it.
