"""Verify packaged frontend delivery keeps the API and docs reachable."""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from emporio_music_backend import paths
from emporio_music_backend.api.app import create_app


def test_frontend_routes_leave_api_and_docs_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frontend_directory = tmp_path / "apps" / "frontend" / "dist"
    assets_directory = frontend_directory / "assets"
    assets_directory.mkdir(parents=True)
    (frontend_directory / "index.html").write_text(
        "<html><body>frontend smoke</body></html>", encoding="utf-8"
    )
    (assets_directory / "app.js").write_text("frontend asset", encoding="utf-8")
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)

    app = create_app()
    route_paths = {getattr(route, "path", None) for route in app.routes}
    assert "/" in route_paths
    assert "/assets" in route_paths

    async def check_routes() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/docs")).status_code == 200
            missing_api_route = await client.get("/api/not-a-route")
            assert missing_api_route.status_code == 404

            schema = await client.get("/openapi.json")
            assert schema.status_code == 200
            assert "/api/chat" in schema.json()["paths"]

    asyncio.run(check_routes())
