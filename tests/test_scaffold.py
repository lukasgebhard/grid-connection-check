from httpx import ASGITransport, AsyncClient

from gridcheck.api.app import create_app


async def test_livez_needs_no_database() -> None:
    # ASGITransport skips the lifespan, so the pool is never opened.
    app = create_app("postgresql://unused")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/livez")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
