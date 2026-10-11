from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
async def single_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    (tmp_path / "index.html").write_text('<div id="root"></div>')
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    monkeypatch.setattr(get_settings(), "web_dir", str(tmp_path))
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


async def test_serves_the_web_app_and_its_client_side_routes(single_container: AsyncClient) -> None:
    for path in ("/", "/orders/ORD-123", "/admin/products"):
        response = await single_container.get(path)
        assert response.status_code == 200, path
        assert '<div id="root">' in response.text, path
    assert "console.log" in (await single_container.get("/assets/app.js")).text


async def test_api_routes_win_and_unknown_api_paths_stay_404(single_container: AsyncClient) -> None:
    assert (await single_container.get("/health")).json() == {"status": "ok"}
    assert (await single_container.get("/api/v1/no-such-thing")).status_code == 404
