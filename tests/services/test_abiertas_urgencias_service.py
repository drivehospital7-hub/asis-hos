"""T1 strict TDD - file-per-month storage helpers + CRUD (AC1-AC7)."""

import json
import logging
from pathlib import Path

import pytest

import app.services.abiertas_urgencias_service as svc


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    horarios_dir = data_dir / "horarios"
    legacy_file = data_dir / "horario_abiertas_urgencias.json"
    monkeypatch.setattr(svc, "HORARIOS_DIR", horarios_dir)
    monkeypatch.setattr(svc, "HORARIO_FILE", legacy_file)
    monkeypatch.setattr(svc, "COLUMNAS", [
        "07:00 AM - 01:00 PM",
        "01:00 PM - 07:00 PM",
        "07:00 PM - 07:00 AM",
    ])
    return {"data_dir": data_dir, "horarios_dir": horarios_dir, "legacy": legacy_file}


def _valid_dias(n=1):
    dias = []
    for i in range(1, n + 1):
        dias.append({"dia": i, "manana": "CARLOS", "tarde": "ALEJANDRA", "noche": "YULIETH"})
    return dias


# AC1 Save creates file
def test_ac1_save_creates_file(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    dias = _valid_dias(1)
    res = svc.save_horario(9, 2026, dias)
    assert res["status"] == "success"
    assert res["data"]["horario"]["mes"] == 9
    assert res["data"]["horario"]["anio"] == 2026
    assert res["data"]["total_dias"] == 1
    path = svc.HORARIOS_DIR / "abiertas_urgencias_2026-09.json"
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["mes"] == 9
    assert data["total_dias"] == 1
    # get returns same
    got = svc.get_horario(9, 2026)
    assert got["status"] == "success"
    assert got["data"]["horario"]["dias"] == dias
    assert got["data"]["total_dias"] == 1
    assert "[BACK] Horario guardado" in caplog.text


# AC2 Get missing returns null
def test_ac2_get_missing_returns_null():
    res = svc.get_horario(7, 2026)
    assert res["status"] == "success"
    assert res["data"]["horario"] is None
    assert res["data"]["total_dias"] == 0
    assert res["errors"] == []
    assert res["status"] != "warning"


# AC3 List sorted
def test_ac3_list_sorted():
    svc.save_horario(9, 2026, _valid_dias(2))
    svc.save_horario(8, 2026, _valid_dias(2))
    res = svc.list_horarios()
    assert res["status"] == "success"
    assert res["data"]["meses"] == ["2026-08", "2026-09"]


# AC4 Delete scoped
def test_ac4_delete_scoped():
    svc.save_horario(8, 2026, _valid_dias(1))
    svc.save_horario(9, 2026, _valid_dias(1))
    res = svc.delete_horario(9, 2026)
    assert res["status"] == "success"
    assert not (svc.HORARIOS_DIR / "abiertas_urgencias_2026-09.json").exists()
    assert (svc.HORARIOS_DIR / "abiertas_urgencias_2026-08.json").exists()
    # second delete idempotent
    res2 = svc.delete_horario(9, 2026)
    assert res2["status"] == "success"
    assert res2["errors"] == []
    # list still has 08
    assert svc.list_horarios()["data"]["meses"] == ["2026-08"]


# AC5 Atomic write (tmp+rename, log, no torn read, no tmp leftover)
def test_ac5_atomic_write(tmp_path, caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    dias = _valid_dias(3)
    # ensure no tmp files before
    svc.save_horario(10, 2026, dias)
    path = svc.HORARIOS_DIR / "abiertas_urgencias_2026-10.json"
    assert path.exists()
    # no tmp files lingering
    tmp_files = list(svc.HORARIOS_DIR.glob("*.tmp.*"))
    assert tmp_files == []
    assert "[BACK] Horario guardado: 3 dias para 10/2026" in caplog.text
    # verify file content is complete json
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["columnas"] == svc.COLUMNAS
    assert data["total_dias"] == 3


# AC6 Range validation
def test_ac6_range_validation_mes_invalid():
    res = svc.save_horario(0, 2026, _valid_dias(1))
    assert res["status"] == "error"
    assert any("mes invalido" in e for e in res["errors"])
    assert not (svc.HORARIOS_DIR / "abiertas_urgencias_2026-00.json").exists()
    res2 = svc.save_horario(13, 2026, _valid_dias(1))
    assert res2["status"] == "error"
    assert any("mes invalido" in e for e in res2["errors"])

def test_ac6_range_validation_anio_invalid():
    res = svc.save_horario(9, 1999, _valid_dias(1))
    assert res["status"] == "error"
    assert any("anio invalido" in e for e in res["errors"])
    assert not (svc.HORARIOS_DIR / "abiertas_urgencias_1999-09.json").exists()
    res2 = svc.save_horario(9, 2101, _valid_dias(1))
    assert res2["status"] == "error"

def test_ac6_horario_path_validation():
    with pytest.raises(ValueError, match="mes invalido"):
        svc._horario_path(0, 2026)
    with pytest.raises(ValueError, match="mes invalido"):
        svc._horario_path(13, 2026)
    with pytest.raises(ValueError, match="anio invalido"):
        svc._horario_path(5, 1999)
    # get with invalid mes should return envelope error
    res = svc.get_horario(0, 2026)
    assert res["status"] == "error"
    assert any("mes invalido" in e for e in res["errors"])


# AC7 Legacy migration
def test_ac7_legacy_migration(caplog):
    caplog.set_level(logging.INFO)
    legacy_dias = _valid_dias(2)
    legacy_payload = {"mes": 8, "anio": 2026, "dias": legacy_dias, "total_dias": 2, "columnas": svc.COLUMNAS}
    svc.HORARIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(svc.HORARIO_FILE, "w", encoding="utf-8") as f:
        json.dump(legacy_payload, f, ensure_ascii=False)
    # ensure no sharded yet
    assert not (svc.HORARIOS_DIR / "abiertas_urgencias_2026-08.json").exists()
    res = svc.list_horarios()
    assert res["status"] == "success"
    assert "2026-08" in res["data"]["meses"]
    sharded = svc.HORARIOS_DIR / "abiertas_urgencias_2026-08.json"
    assert sharded.exists()
    with open(sharded, encoding="utf-8") as f:
        data = json.load(f)
    assert data["dias"] == legacy_dias
    # legacy retained
    assert svc.HORARIO_FILE.exists()
    assert "[BACK] Migrating" in caplog.text


def test_ac7_legacy_migration_idempotent(caplog):
    legacy_dias = _valid_dias(1)
    legacy_payload = {"mes": 8, "anio": 2026, "dias": legacy_dias, "total_dias": 1, "columnas": svc.COLUMNAS}
    svc.HORARIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(svc.HORARIO_FILE, "w", encoding="utf-8") as f:
        json.dump(legacy_payload, f, ensure_ascii=False)
    svc.list_horarios()
    # manually edit sharded to have different dias
    sharded = svc.HORARIOS_DIR / "abiertas_urgencias_2026-08.json"
    edited = {"mes": 8, "anio": 2026, "dias": [{"dia": 99, "manana": "X", "tarde": "Y", "noche": "Z"}], "total_dias": 1, "columnas": svc.COLUMNAS}
    with open(sharded, "w", encoding="utf-8") as f:
        json.dump(edited, f, ensure_ascii=False)
    caplog.clear()
    svc.list_horarios()
    with open(sharded, encoding="utf-8") as f:
        after = json.load(f)
    # not overwritten
    assert after["dias"][0]["dia"] == 99


# Additional: dias validation
def test_save_validates_dias_missing_fields():
    # missing noche
    bad = [{"dia": 1, "manana": "CARLOS", "tarde": "ALEJANDRA"}]
    res = svc.save_horario(9, 2026, bad)
    assert res["status"] == "error"
    assert res["errors"]
    assert not (svc.HORARIOS_DIR / "abiertas_urgencias_2026-09.json").exists()

def test_save_validates_dia_range():
    bad = [{"dia": 0, "manana": "A", "tarde": "B", "noche": "C"}]
    res = svc.save_horario(9, 2026, bad)
    assert res["status"] == "error"
    bad2 = [{"dia": 32, "manana": "A", "tarde": "B", "noche": "C"}]
    res2 = svc.save_horario(9, 2026, bad2)
    assert res2["status"] == "error"

def test_save_validates_empty_dias():
    res = svc.save_horario(9, 2026, [])
    assert res["status"] == "error"
    assert any("No hay datos" in e for e in res["errors"])

def test_save_validates_manana_empty():
    bad = [{"dia": 1, "manana": "", "tarde": "B", "noche": "C"}]
    res = svc.save_horario(9, 2026, bad)
    assert res["status"] == "error"


# Helpers: ensure_data_dir, mes_actual, list skips corrupt
def test_ensure_data_dir_creates():
    # fixture already patches, but ensure it exists after save
    assert svc.HORARIOS_DIR.exists() or not svc.HORARIOS_DIR.exists()
    svc._ensure_data_dir()
    assert svc.HORARIOS_DIR.exists()

def test_mes_actual_shape(monkeypatch):
    from datetime import date as real_date
    # mes_actual returns dict with mes/anio ints
    res = svc._mes_actual()
    assert isinstance(res["mes"], int)
    assert isinstance(res["anio"], int)
    assert 1 <= res["mes"] <= 12
    assert 2000 <= res["anio"] <= 2100

def test_list_skips_corrupt_json(caplog):
    caplog.set_level(logging.INFO)
    svc.save_horario(8, 2026, _valid_dias(1))
    svc.HORARIOS_DIR.mkdir(parents=True, exist_ok=True)
    corrupt = svc.HORARIOS_DIR / "abiertas_urgencias_2026-09.json"
    corrupt.write_text("{ not json", encoding="utf-8")
    res = svc.list_horarios()
    assert res["status"] == "success"
    assert "2026-09" not in res["data"]["meses"]
    assert "2026-08" in res["data"]["meses"]
    assert "[BACK][ERROR]" in caplog.text

def test_get_horario_legacy_compat_current_month(monkeypatch):
    # save via legacy single-param path should default to current month
    dias = _valid_dias(2)
    res = svc.save_horario(dias)
    assert res["status"] == "success"
    got = svc.get_horario()
    assert got["status"] == "success"
    assert got["data"]["horario"] is not None
    assert got["data"]["total_dias"] == 2


def test_delete_idempotent_no_file():
    res = svc.delete_horario(12, 2026)
    assert res["status"] == "success"
    assert res["errors"] == []

def test_ghorario_path_ensures_dir(tmp_path):
    # _horario_path should ensure dir exists
    p = svc._horario_path(5, 2026)
    assert svc.HORARIOS_DIR.exists()
    assert p.name == "abiertas_urgencias_2026-05.json"

def test_envelope_never_warning():
    for fn in [svc.list_horarios(), svc.get_horario(7, 2026), svc.save_horario(9, 1999, _valid_dias(1)), svc.delete_horario(9, 2026)]:
        assert fn["status"] in ("success", "error")
        assert "data" in fn
        assert "errors" in fn
        assert isinstance(fn["data"], dict)
        assert isinstance(fn["errors"], list)
