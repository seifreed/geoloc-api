"""Capa de presentación: API REST. Cablea dominio + repositorio, sin lógica propia."""
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query

from . import repository
from .domain import Point, signal_weight, weighted_centroid
from .middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from .schemas import GeoRequest, GeoResult
from .security import require_key

app = FastAPI(title="GeoLoc API", description="Cell / WiFi / A-GNSS lookup")
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
protected = [Depends(require_key)]


@app.get("/health")
def health() -> dict:
    repository.ping()
    return {"ok": True}


@app.get("/cell", dependencies=protected, responses={404: {"description": "cell not found"}})
def cell(radio: str, mcc: int, mnc: int, area: int, cid: int) -> dict:
    row = repository.find_cell(radio, mcc, mnc, area, cid)
    if not row:
        raise HTTPException(404, "cell not found")
    return row


@app.get("/wifi", dependencies=protected, responses={404: {"description": "bssid not found"}})
def wifi(bssid: str) -> dict:
    row = repository.find_wifi(bssid)
    if not row:
        raise HTTPException(404, "bssid not found")
    return row


@app.get("/nearest", dependencies=protected)
def nearest(lat: float = Query(ge=-90, le=90),
            lon: float = Query(ge=-180, le=180),
            kind: Literal["cell", "wifi"] = "cell",
            radius: float = Query(2000, gt=0, le=50000),
            limit: int = Query(5, ge=1, le=100)) -> list[dict]:
    return repository.nearest(kind, Point(lat, lon), radius, limit)


@app.post("/geolocate", dependencies=protected, response_model=GeoResult,
          responses={404: {"description": "no matches"}, 413: {"description": "body too large"}})
def geolocate(req: GeoRequest) -> GeoResult:
    cell_rows = repository.find_cells(
        [(ce.radio, ce.mcc, ce.mnc, ce.area, ce.cid) for ce in req.cells]
    )
    wifi_rows = repository.find_wifis([ap.bssid for ap in req.wifi])

    points: list[tuple[Point, float]] = []
    for ce in req.cells:
        row = cell_rows.get((ce.radio.upper(), ce.mcc, ce.mnc, ce.area, ce.cid))
        if row:
            points.append((Point(row["lat"], row["lon"]), signal_weight(ce.rssi, row["samples"])))
    for ap in req.wifi:
        row = wifi_rows.get(ap.bssid.upper())
        if row:
            points.append((Point(row["lat"], row["lon"]), signal_weight(ap.rssi, None)))

    try:
        c = weighted_centroid(points)
    except ValueError:
        raise HTTPException(404, "no matches for given cells/wifi")
    return GeoResult(lat=c.lat, lon=c.lon, matched=len(points))
