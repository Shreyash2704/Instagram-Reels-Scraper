from fastapi.testclient import TestClient

from app.main import app


def test_proxy_rejects_non_allowlisted_host() -> None:
    client = TestClient(app)
    r = client.get(
        "/proxy/cdn-image",
        params={"url": "https://example.com/image.png"},
    )
    assert r.status_code == 400


def test_proxy_rejects_non_http_scheme() -> None:
    client = TestClient(app)
    r = client.get(
        "/proxy/cdn-image",
        params={"url": "ftp://scontent-den2-1.cdninstagram.com/x.jpg"},
    )
    assert r.status_code == 400
