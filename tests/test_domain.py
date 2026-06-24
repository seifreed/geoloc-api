"""Tests de la lógica de negocio pura (sin BD)."""
import pytest

from app.domain import Point, bounding_box, signal_weight, weighted_centroid


def test_signal_weight_stronger_rssi_weighs_more():
    assert signal_weight(-50, None) > signal_weight(-90, None)


def test_signal_weight_falls_back_to_samples():
    assert signal_weight(None, 10) == 10
    assert signal_weight(None, 0) == 1
    assert signal_weight(None, None) == 1


def test_weighted_centroid_pulls_toward_heavier_point():
    pts = [(Point(40.0, -3.0), signal_weight(-50, None)),
           (Point(41.0, -3.0), signal_weight(-90, None))]
    c = weighted_centroid(pts)
    assert c.lat < 40.01  # arrastrado a la celda de señal fuerte


def test_weighted_centroid_equal_weights_is_mean():
    c = weighted_centroid([(Point(0.0, 0.0), 1), (Point(2.0, 4.0), 1)])
    assert c.lat == 1.0 and c.lon == 2.0


def test_weighted_centroid_empty_raises():
    with pytest.raises(ValueError):
        weighted_centroid([])


def test_bounding_box_contains_center_and_grows_with_radius():
    center = Point(40.0, -3.0)
    min_lat, min_lon, max_lat, max_lon = bounding_box(center, 1000)
    assert min_lat < center.lat < max_lat
    assert min_lon < center.lon < max_lon
    # más radio => caja más ancha
    wider = bounding_box(center, 5000)
    assert wider[0] < min_lat and wider[2] > max_lat


def test_bounding_box_near_pole_stays_bounded():
    # en el polo el coseno tiende a 0; dlon no debe explotar (regresión del guard buggy)
    min_lat, min_lon, max_lat, max_lon = bounding_box(Point(90.0, 0.0), 2000)
    assert (max_lon - min_lon) < 10  # antes daba ~7e8 grados
