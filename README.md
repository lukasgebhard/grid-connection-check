# grid-connection-check

Backend service that checks PV connection requests against a low-voltage distribution grid. Work in progress.

## Requirements

- Python 3.14 and [uv](https://docs.astral.sh/uv/)
- Docker (for PostgreSQL and the containerized service)

## Usage

Copy `.env.sample` to `.env` and adjust the database credentials, then start the service:

```sh
docker compose up
```

The API listens on <http://localhost:8080>. Health endpoints: `GET /livez` (liveness), `GET /readyz` (database reachable).

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
