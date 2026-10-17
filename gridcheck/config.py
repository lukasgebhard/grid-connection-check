"""All constants and settings in one place."""

import os

from psycopg.conninfo import make_conninfo

# The database runs as the Compose service `db`; only the credentials are configurable.
DB_HOST = "db"
DB_PORT = 5432
DB_NAME = "gridcheck"


def db_uri() -> str:
    """Build the connection string from the env variables DB_USER and DB_PASSWORD."""
    return make_conninfo(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
