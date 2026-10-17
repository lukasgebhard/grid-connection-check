# Architecture decision records (ADR)

Each ADR states the decision, the assumptions it rests on, and its consequences.
If an assumption stops holding, revisit the record.

## ADR-000 Integration tests against a throwaway database

**Decision.** Tests run against a real PostgreSQL, without mocks.
Each test run creates a fresh database from `db/schema.sql` and drops it afterwards.
Each test runs inside a transaction that is rolled back at the end.

**Assumptions.**

- Hand-written SQL can only be verified against a real database.
- Tests have their own connection settings and never have access to the app's database.

**Consequences.**

- Tests cannot damage real data, and every run also checks that the schema builds from scratch.
- Tests are isolated without any cleanup.
- Running the tests requires a PostgreSQL server on which the test user may create databases.

## ADR-001 Plain SQL with psycopg, no ORM

**Decision.** The database is accessed with psycopg 3 and hand-written SQL.
No ORM, no query builder, no migration tool; the schema is one init script.

**Assumptions.**

- The data model is small: two tables and a handful of queries.
- The job queue relies on exact locking and transaction semantics, which must be visible in the code.
- Every database is built from scratch, so there is no data to migrate.

**Consequences.**

- Queries run exactly as written and can be pasted into `psql`.
- Only the tests against a real database (ADR-000) catch SQL errors.
- API and worker each have their own small query module.
