"""Tests de la capa de presentación (rutas FastAPI) sin BD: el repositorio se mockea."""
from fastapi.testclient import TestClient

from app import repository, security
from app.config import Settings
from app.main import app

client = TestClient(app)
CELL_PARAMS = {"radio": "GSM", "mcc": 214, "mnc": 7, "area": 1, "cid": 2}


def test_health(monkeypatch):
    monkeypatch.setattr(repository, "ping", lambda: None)
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_security_headers_present(monkeypatch):
    monkeypatch.setattr(repository, "ping", lambda: None)
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"


def test_cell_found(monkeypatch):
    monkeypatch.setattr(repository, "find_cell",
                        lambda *a: {"lon": -3.7, "lat": 40.4, "range": 100, "samples": 5})
    r = client.get("/cell", params=CELL_PARAMS)
    assert r.status_code == 200 and r.json()["lat"] == 40.4


def test_cell_not_found(monkeypatch):
    monkeypatch.setattr(repository, "find_cell", lambda *a: None)
    assert client.get("/cell", params=CELL_PARAMS).status_code == 404


def test_nearest_bad_kind():
    # kind es un Literal -> FastAPI lo valida y devuelve 422
    assert client.get("/nearest", params={"lat": 40, "lon": -3, "kind": "foo"}).status_code == 422


def test_nearest_rejects_out_of_range_and_oversized(monkeypatch):
    monkeypatch.setattr(repository, "nearest", lambda *a: [])
    assert client.get("/nearest", params={"lat": 999, "lon": -3}).status_code == 422  # lat OOR
    assert client.get("/nearest", params={"lat": 40, "lon": -3, "limit": 99999}).status_code == 422
    assert client.get("/nearest", params={"lat": 40, "lon": -3, "radius": 1e9}).status_code == 422


def test_geolocate_rejects_oversized_batch():
    big = {"cells": [CELL_PARAMS] * 1001, "wifi": []}
    assert client.post("/geolocate", json=big).status_code == 422


def test_geolocate_rejects_out_of_range_rssi():
    # rssi enorme provocaba OverflowError (500); ahora se rechaza con 422
    bad = {"cells": [{**CELL_PARAMS, "rssi": 100000}], "wifi": []}
    assert client.post("/geolocate", json=bad).status_code == 422


def test_rejects_oversized_request_body():
    # body > 1 MB se rechaza con 413 antes de cargarse en memoria (anti-DoS)
    oversized = "x" * (1_048_576 + 10)
    r = client.post("/geolocate", content=oversized,
                    headers={"content-type": "application/json"})
    assert r.status_code == 413


def test_body_limit_counts_chunked_bytes():
    # sin Content-Length (chunked): el límite se aplica contando bytes recibidos
    import asyncio

    from app.middleware import BodySizeLimitMiddleware

    async def downstream(scope, receive, send):  # no debería alcanzarse
        raise AssertionError("la app no debería recibir un body sobredimensionado")

    chunks = [
        {"type": "http.request", "body": b"x" * 600_000, "more_body": True},
        {"type": "http.request", "body": b"x" * 600_000, "more_body": False},
    ]
    sent = []

    async def receive():
        return chunks.pop(0)

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "headers": []}  # sin content-length → fuerza el conteo
    asyncio.run(BodySizeLimitMiddleware(downstream)(scope, receive, send))
    assert sent[0]["status"] == 413


def test_geolocate_weights_match(monkeypatch):
    hit = {("GSM", 214, 7, 1, 2): {"lat": 40.0, "lon": -3.0, "samples": 5}}
    monkeypatch.setattr(repository, "find_cells", lambda keys: hit)
    monkeypatch.setattr(repository, "find_wifis", lambda b: {})
    r = client.post("/geolocate", json={"cells": [{**CELL_PARAMS, "rssi": -50}], "wifi": []})
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] == 1 and body["lat"] == 40.0


def test_geolocate_no_match(monkeypatch):
    monkeypatch.setattr(repository, "find_cells", lambda keys: {})
    monkeypatch.setattr(repository, "find_wifis", lambda b: {})
    r = client.post("/geolocate", json={"cells": [CELL_PARAMS]})
    assert r.status_code == 404


def test_api_key_enforced(monkeypatch):
    monkeypatch.setattr(security, "settings", Settings(api_key="secret"))
    monkeypatch.setattr(repository, "find_cell",
                        lambda *a: {"lon": 0, "lat": 0, "range": 0, "samples": 1})
    assert client.get("/cell", params=CELL_PARAMS).status_code == 401
    ok = client.get("/cell", params=CELL_PARAMS, headers={"X-API-Key": "secret"})
    assert ok.status_code == 200
