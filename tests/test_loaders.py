"""Tests del parsing de ficheros (sin BD), con ficheros temporales."""
import json

import pytest

from app.loaders import cell_rows, wifi_rows


def test_cell_rows_with_header(tmp_path):
    f = tmp_path / "h.csv"
    f.write_text("radio,mcc,net,area,cell,unit,lon,lat,range,samples\n"
                 "GSM,214,7,2816,3573,0,-3.72,40.42,7094,23\n")
    rows = list(cell_rows(str(f)))
    assert len(rows) == 1
    assert rows[0] == ("GSM", "214", "7", "2816", "3573", "-3.72", "40.42", "7094", "23")


def test_cell_rows_without_header_keeps_first_row(tmp_path):
    f = tmp_path / "nh.csv"
    f.write_text("GSM,214,7,2816,3573,0,-3.72,40.42,7094,23\n"
                 "LTE,214,1,2220,26761,0,2.05,41.29,500,5\n")
    rows = list(cell_rows(str(f)))
    assert len(rows) == 2  # la 1a fila NO se pierde


def test_cell_rows_skips_malformed(tmp_path):
    # línea en blanco y fila truncada: se saltan, no rompen la carga (antes: IndexError)
    f = tmp_path / "bad.csv"
    f.write_text("GSM,214,7,2816,3573,0,-3.72,40.42,7094,23\n\nLTE,214,1,2220\n")
    rows = list(cell_rows(str(f)))
    assert len(rows) == 1 and rows[0][0] == "GSM"


def test_wifi_csv_missing_columns_raises(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("foo,bar\n1,2\n")  # sin netid/trilat/trilong
    with pytest.raises(ValueError, match="columnas requeridas"):
        list(wifi_rows(str(f)))


def test_wifi_rows_json(tmp_path):
    f = tmp_path / "w.json"
    f.write_text(json.dumps({"results": [
        {"netid": "aa:bb:cc:dd:ee:ff", "ssid": "x", "trilat": 41.38, "trilong": 2.16},
        {"netid": "no:loc", "ssid": "y", "trilat": None, "trilong": None},
    ]}))
    rows = list(wifi_rows(str(f)))
    assert rows == [("AA:BB:CC:DD:EE:FF", "x", 2.16, 41.38)]  # filtra sin coords, normaliza MAC


def test_wifi_json_skips_results_missing_bssid(tmp_path):
    f = tmp_path / "w.json"
    f.write_text(json.dumps({"results": [
        {"ssid": "no-netid", "trilat": 1.0, "trilong": 2.0},  # falta netid
        {"netid": "aa:bb:cc:dd:ee:ff", "trilat": 1.0, "trilong": 2.0},
    ]}))
    rows = list(wifi_rows(str(f)))
    assert rows == [("AA:BB:CC:DD:EE:FF", None, 2.0, 1.0)]
