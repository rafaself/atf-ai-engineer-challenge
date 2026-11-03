"""Verify packaged frontend delivery keeps the API and docs reachable."""

import asyncio
from pathlib import Path

import pytest
from emporio_music_api import paths as api_paths
from emporio_music_api.app import create_app
from httpx import ASGITransport, AsyncClient


def test_frontend_content_serves_without_hiding_api_or_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frontend_directory = tmp_path / "frontend-dist"
    assets_directory = frontend_directory / "assets"
    assets_directory.mkdir(parents=True)
    (frontend_directory / "index.html").write_text(
        "<html><body>frontend smoke</body></html>", encoding="utf-8"
    )
    (assets_directory / "app.js").write_text("frontend asset", encoding="utf-8")
    monkeypatch.setattr(api_paths, "FRONTEND_DIRECTORY", frontend_directory)

    app = create_app()

    async def check_routes() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            frontend = await client.get("/")
            assert frontend.status_code == 200
            assert frontend.text == "<html><body>frontend smoke</body></html>"

            asset = await client.get("/assets/app.js")
            assert asset.status_code == 200
            assert asset.text == "frontend asset"

            assert (await client.get("/docs")).status_code == 200
            missing_api_route = await client.get("/api/not-a-route")
            assert missing_api_route.status_code == 404

            schema = await client.get("/openapi.json")
            assert schema.status_code == 200
            assert "/api/chat" in schema.json()["paths"]

    asyncio.run(check_routes())
