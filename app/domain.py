"""Lógica de negocio pura de geolocalización. Sin I/O: 100% testeable."""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float


def signal_weight(rssi: float | None, samples: int | None) -> float:
    """Peso de una observación en el centroide.

    Con RSSI (dBm) usa potencia lineal relativa (10^(rssi/10)): más señal pesa más.
    Sin RSSI cae al nº de muestras (celdas) o 1 (WiFi).
    """
    if rssi is not None:
        # ponytail: centroide ponderado por potencia, no multilateración real
        # (resolver círculos). Subir a least-squares si se necesita <500 m.
        return 10 ** (rssi / 10.0)
    return max(samples or 1, 1)


def weighted_centroid(weighted_points: list[tuple[Point, float]]) -> Point:
    """Centroide ponderado de (punto, peso). Lanza ValueError si no hay puntos."""
    if not weighted_points:
        raise ValueError("no points to average")
    total = sum(w for _, w in weighted_points)
    lat = sum(p.lat * w for p, w in weighted_points) / total
    lon = sum(p.lon * w for p, w in weighted_points) / total
    return Point(lat, lon)


def bounding_box(center: Point, radius_m: float) -> tuple[float, float, float, float]:
    """Caja (min_lat, min_lon, max_lat, max_lon) de ±radius_m alrededor de center.

    ponytail: aproximación en grados, válida para unos pocos km.
    """
    dlat = radius_m / 111320.0
    # clamp del coseno: evita div/0 y que dlon explote cerca de los polos
    cos_lat = max(math.cos(math.radians(center.lat)), 0.01)
    dlon = radius_m / (111320.0 * cos_lat)
    return (center.lat - dlat, center.lon - dlon, center.lat + dlat, center.lon + dlon)
