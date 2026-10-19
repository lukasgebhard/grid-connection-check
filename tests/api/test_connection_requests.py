import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

rural_grid = "kerber-landnetz-freileitung-1"


async def test_create_returns_202_with_location_and_pending_request(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/connection-requests",
        json={"grid_id": rural_grid, "bus_id": 14, "p_kw": 30},
    )

    assert response.status_code == 202
    body = response.json()
    assert response.headers["Location"] == f"/connection-requests/{body['request_id']}"
    assert body["grid_id"] == rural_grid
    assert body["bus_id"] == 14
    assert body["p_kw"] == 30
    assert body["status"] == "pending"
    assert body["submitted_at"] is not None
    assert body["finished_at"] is None
    assert body["result"] is None
    assert body["error"] is None


async def test_get_returns_the_created_request(client: AsyncClient) -> None:
    created = await client.post(
        "/connection-requests",
        json={"grid_id": rural_grid, "bus_id": 14, "p_kw": 12.5},
    )

    response = await client.get(created.headers["Location"])

    assert response.status_code == 200
    assert response.json() == created.json()


async def test_get_returns_the_result_as_an_object(
    client: AsyncClient, conn: AsyncConnection
) -> None:
    created = await client.post(
        "/connection-requests",
        json={"grid_id": rural_grid, "bus_id": 14, "p_kw": 30},
    )
    # Decide the request the way the worker will.
    await conn.execute(
        "UPDATE connection_requests"
        " SET status = 'approved', finished_at = now(), result = %s"
        " WHERE request_id = %s",
        (Jsonb({"verdict": "approved"}), created.json()["request_id"]),
    )

    response = await client.get(created.headers["Location"])

    assert response.json()["status"] == "approved"
    assert response.json()["result"] == {"verdict": "approved"}


async def test_unknown_request_is_404(client: AsyncClient) -> None:
    response = await client.get("/connection-requests/999999999")
    assert response.status_code == 404


async def test_unknown_grid_is_422(client: AsyncClient) -> None:
    response = await client.post(
        "/connection-requests",
        json={"grid_id": "no-such-grid", "bus_id": 14, "p_kw": 30},
    )
    assert response.status_code == 422
    assert "unknown grid" in response.json()["detail"]


@pytest.mark.parametrize("bus_id", [0, 1, 9999])  # MV side, LV busbar, no such bus
async def test_bus_that_is_not_a_connection_point_is_422(
    client: AsyncClient, bus_id: int
) -> None:
    response = await client.post(
        "/connection-requests",
        json={"grid_id": rural_grid, "bus_id": bus_id, "p_kw": 30},
    )
    assert response.status_code == 422
    assert "not a connection point" in response.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [
        {"bus_id": 14, "p_kw": 30},  # grid_id missing
        {"grid_id": rural_grid, "bus_id": "far end", "p_kw": 30},
        {"grid_id": rural_grid, "bus_id": 14, "p_kw": 0},
        {"grid_id": rural_grid, "bus_id": 14, "p_kw": -5},
        {"grid_id": rural_grid, "bus_id": 14, "p_kw": 1000.01},
        {"grid_id": rural_grid, "bus_id": 14, "p_kw": 30.125},  # finer than 0.01 kW
    ],
)
async def test_invalid_body_is_422(
    client: AsyncClient, body: dict[str, object]
) -> None:
    response = await client.post("/connection-requests", json=body)
    assert response.status_code == 422
