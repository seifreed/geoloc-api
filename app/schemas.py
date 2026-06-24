"""Modelos de entrada/salida de la API (Pydantic)."""
from pydantic import BaseModel, Field

MAX_BATCH = 1000  # tope de observaciones por petición (evita batches gigantes)
# rango dBm físicamente posible; acota la entrada para que 10^(rssi/10) no desborde
RSSI = Field(default=None, ge=-200, le=50)


class Cell(BaseModel):
    radio: str
    mcc: int
    mnc: int
    area: int
    cid: int
    rssi: float | None = RSSI  # dBm; si se da, pondera por potencia


class WifiObs(BaseModel):
    bssid: str
    rssi: float | None = RSSI


class GeoRequest(BaseModel):
    cells: list[Cell] = Field(default_factory=list, max_length=MAX_BATCH)
    wifi: list[WifiObs] = Field(default_factory=list, max_length=MAX_BATCH)


class GeoResult(BaseModel):
    lat: float
    lon: float
    matched: int
