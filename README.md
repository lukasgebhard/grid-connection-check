# grid-connection-check

Backend service that checks PV connection requests against a low-voltage distribution grid. Work in progress.

## Requirements

- Python 3.14 and [uv](https://docs.astral.sh/uv/)
- Docker (for PostgreSQL and the containerized service)

## Usage

Copy `.env.sample` to `.env` and adjust the database credentials, then start the service:

```sh
docker compose up # database, API and one worker
docker compose up --scale worker=3 # or several workers
```

The API stores each request as `pending`. Workers pick up pending requests from the database, run the load flow and store the verdict. Requests on the same grid are checked one at a time, in submission order; requests on different grids are checked in parallel. A worker stops after its current job on `SIGTERM` or `SIGINT`.

The API listens on <http://localhost:8080>:

| Endpoint | Purpose |
|---|---|
| `POST /connection-requests` | Submit `{grid_id, bus_id, p_kw}`. Returns `202 Accepted`, a `Location` header and the request with `status: "pending"` |
| `GET /connection-requests/{request_id}` | The request with its status and, once decided, its `result` |
| `GET /livez` | Liveness, no database access |
| `GET /readyz` | Readiness: the database is reachable |

Unknown grids and buses that aren't connection points of the grid are rejected with `422`. Interactive API docs are at <http://localhost:8080/docs>.

The database schema is a single init script, `db/schema.sql`. PostgreSQL runs it only when the data volume is empty, so after changing it, recreate the database (this deletes all data):

```sh
docker compose down -v
```

## Development

Everything runs from the repository root; the project is not installed as a package.

```sh
uv sync
docker compose up -d db # the tests need a running database
uv run ruff check --fix .
uv run ruff format .
uv run mypy --strict gridcheck
uv run pytest
```

The tests create a throwaway database per run and drop it afterwards. They connect as the user `tester` (with `CREATEDB`), which `db/test_user.sql` creates in the Compose database. That user cannot connect to the application database.

Install the pre-commit hook so both Ruff checks run on every commit:

```sh
uv tool install pre-commit
uvx pre-commit install
```

CI (`.github/workflows/ci.yml`) runs Ruff, mypy and pytest against a PostgreSQL 18 service container.
