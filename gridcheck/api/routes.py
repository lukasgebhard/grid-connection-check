from fastapi import APIRouter, HTTPException, Request, Response, status

from gridcheck.api import queries
from gridcheck.api.db import Connection
from gridcheck.api.schemas import ConnectionRequest, ConnectionRequestCreate
from gridcheck.domain.grids import GRID_IDS, connection_points

router = APIRouter()


@router.post(
    "/connection-requests",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ConnectionRequest,
)
async def create_connection_request(
    body: ConnectionRequestCreate,
    conn: Connection,
    request: Request,
    response: Response,
) -> ConnectionRequest:
    """Queue a request for checking. A worker decides it asynchronously."""

    if body.grid_id not in GRID_IDS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown grid {body.grid_id!r}"
        )
    if body.bus_id not in connection_points(body.grid_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"bus {body.bus_id} is not a connection point of grid {body.grid_id!r}",
        )

    created = await queries.insert_request(conn, body)
    response.headers["Location"] = request.app.url_path_for(
        "get_connection_request", request_id=created.request_id
    )
    return created


@router.get("/connection-requests/{request_id}", response_model=ConnectionRequest)
async def get_connection_request(
    request_id: int, conn: Connection
) -> ConnectionRequest:
    found = await queries.get_request(conn, request_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "connection request not found")
    return found


@router.get("/livez")
async def livez() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(conn: Connection) -> dict[str, str]:
    await conn.execute("SELECT 1")
    return {"status": "ok"}
