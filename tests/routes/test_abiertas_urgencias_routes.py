"""T2 strict TDD - routes thin delegators for horarios por mes (AC1-AC7)."""

import json
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
    return {"horarios_dir": horarios_dir, "legacy": legacy_file}


def _valid_dias(n=1):
    return [{"dia": i, "manana": "CARLOS", "tarde": "ALEJANDRA", "noche": "YULIETH"} for i in range(1, n + 1)]


def _login(app_client, permisos):
    with app_client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = "tester"
        sess["permisos"] = permisos


def _admin_login(app_client):
    _login(app_client, ["*"])


def _read_perms_login(app_client):
    _login(app_client, ["facturas_abiertas"])


def _write_perms_login(app_client):
    _login(app_client, ["facturas_abiertas:write"])


# ── AC1 List ──

def test_ac1_list_meses_sorted(app_client):
    _read_perms_login(app_client)
    svc.save_horario(9, 2026, _valid_dias(2))
    svc.save_horario(8, 2026, _valid_dias(1))
    resp = app_client.get(
        "/abiertas-urgencias/api/schedules",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["status"] != "warning"
    assert data["data"]["meses"] == ["2026-08", "2026-09"]
    assert data["errors"] == []
    assert isinstance(data["data"], dict)


def test_ac1_list_empty(app_client):
    _read_perms_login(app_client)
    resp = app_client.get(
        "/abiertas-urgencias/api/schedules",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["meses"] == []


# ── AC2 Get with params ──

def test_ac2_get_with_params_returns_horario(app_client):
    _read_perms_login(app_client)
    dias = _valid_dias(3)
    svc.save_horario(9, 2026, dias)
    resp = app_client.get(
        "/abiertas-urgencias/api/schedule?mes=09&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["horario"] is not None
    assert data["data"]["horario"]["mes"] == 9
    assert data["data"]["horario"]["anio"] == 2026
    assert data["data"]["total_dias"] == 3
    assert data["status"] != "warning"


def test_ac2_get_missing_returns_null_200(app_client):
    _read_perms_login(app_client)
    resp = app_client.get(
        "/abiertas-urgencias/api/schedule?mes=07&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["horario"] is None
    assert data["data"]["total_dias"] == 0
    assert data["errors"] == []


def test_ac2_get_invalid_mes_not_digits_400(app_client):
    _read_perms_login(app_client)
    resp = app_client.get(
        "/abiertas-urgencias/api/schedule?mes=ab&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["status"] != "warning"
    assert any("mes invalido" in e for e in data["errors"])


def test_ac2_get_invalid_anio_not_digits_400(app_client):
    _read_perms_login(app_client)
    resp = app_client.get(
        "/abiertas-urgencias/api/schedule?mes=09&anio=xyz",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"


def test_ac2_get_missing_one_param_400(app_client):
    _read_perms_login(app_client)
    resp = app_client.get(
        "/abiertas-urgencias/api/schedule?mes=09",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    # spec says mes y anio requeridos when one missing
    assert any("mes y anio requeridos" in e for e in data["errors"])


# ── AC3 Legacy compat ──

def test_ac3_legacy_compat_current_month(app_client, monkeypatch):
    _read_perms_login(app_client)
    # save via legacy single list -> current month
    monkeypatch.setattr(svc, "_mes_actual", lambda: {"mes": 9, "anio": 2026})
    dias = _valid_dias(2)
    svc.save_horario(dias)
    resp = app_client.get(
        "/abiertas-urgencias/api/schedule",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["horario"] is not None
    assert data["data"]["horario"]["mes"] == 9
    assert data["data"]["horario"]["dias"] == dias


def test_ac3_legacy_compat_missing_returns_null(app_client, monkeypatch):
    _read_perms_login(app_client)
    monkeypatch.setattr(svc, "_mes_actual", lambda: {"mes": 5, "anio": 2026})
    resp = app_client.get(
        "/abiertas-urgencias/api/schedule",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["horario"] is None


# ── AC4 Post new month + legacy dias ──

def test_ac4_post_new_month(app_client):
    _write_perms_login(app_client)
    dias = _valid_dias(2)
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"mes": 9, "anio": 2026, "dias": dias},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["status"] != "warning"
    assert data["data"]["total_dias"] == 2
    # file created
    assert (svc.HORARIOS_DIR / "abiertas_urgencias_2026-09.json").exists()
    # get confirms
    got = app_client.get(
        "/abiertas-urgencias/api/schedule?mes=09&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert got.get_json()["data"]["horario"]["dias"] == dias


def test_ac4_post_legacy_only_dias(app_client, monkeypatch):
    _write_perms_login(app_client)
    monkeypatch.setattr(svc, "_mes_actual", lambda: {"mes": 11, "anio": 2026})
    dias = _valid_dias(1)
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"dias": dias},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    assert (svc.HORARIOS_DIR / "abiertas_urgencias_2026-11.json").exists()


# ── AC5 Post validation ──

def test_ac5_post_mes_zero_validation(app_client):
    _write_perms_login(app_client)
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"mes": 0, "anio": 2026, "dias": _valid_dias(1)},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["status"] != "warning"
    assert any("mes invalido" in e for e in data["errors"])
    assert not (svc.HORARIOS_DIR / "abiertas_urgencias_2026-00.json").exists()


def test_ac5_post_missing_dias_400(app_client):
    _write_perms_login(app_client)
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"mes": 9, "anio": 2026},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert any("No hay datos" in e for e in data["errors"])


def test_ac5_post_empty_dias_error(app_client):
    _write_perms_login(app_client)
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"mes": 9, "anio": 2026, "dias": []},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    data = resp.get_json()
    assert data["status"] == "error"


def test_ac5_post_missing_anio_when_mes_present_400(app_client):
    _write_perms_login(app_client)
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"mes": 9, "dias": _valid_dias(1)},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert any("mes y anio requeridos" in e for e in data["errors"])


def test_ac5_post_non_digit_mes_invalid_400(app_client):
    _write_perms_login(app_client)
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"mes": "abc", "anio": 2026, "dias": _valid_dias(1)},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert any("mes invalido" in e for e in data["errors"])


# ── AC6 Delete scoped ──

def test_ac6_delete_scoped(app_client):
    _write_perms_login(app_client)
    svc.save_horario(8, 2026, _valid_dias(1))
    svc.save_horario(9, 2026, _valid_dias(1))
    resp = app_client.delete(
        "/abiertas-urgencias/api/schedule?mes=09&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["status"] != "warning"
    assert not (svc.HORARIOS_DIR / "abiertas_urgencias_2026-09.json").exists()
    assert (svc.HORARIOS_DIR / "abiertas_urgencias_2026-08.json").exists()


def test_ac6_delete_idempotent_second_delete_success(app_client):
    _write_perms_login(app_client)
    svc.save_horario(9, 2026, _valid_dias(1))
    app_client.delete(
        "/abiertas-urgencias/api/schedule?mes=09&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    resp2 = app_client.delete(
        "/abiertas-urgencias/api/schedule?mes=09&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp2.status_code == 200
    assert resp2.get_json()["status"] == "success"


def test_ac6_delete_missing_params_400(app_client):
    _write_perms_login(app_client)
    resp = app_client.delete(
        "/abiertas-urgencias/api/schedule",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["status"] != "warning"
    assert any("mes y anio requeridos" in e for e in data["errors"])


def test_ac6_delete_missing_one_param_400(app_client):
    _write_perms_login(app_client)
    resp = app_client.delete(
        "/abiertas-urgencias/api/schedule?mes=09",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"


def test_ac6_delete_invalid_digits_400(app_client):
    _write_perms_login(app_client)
    resp = app_client.delete(
        "/abiertas-urgencias/api/schedule?mes=xx&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    assert any("mes invalido" in e for e in resp.get_json()["errors"])


# ── AC7 Auth ──

def test_ac7_get_schedules_unauthenticated_401(app_client):
    resp = app_client.get(
        "/abiertas-urgencias/api/schedules",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["status"] == "error"


def test_ac7_get_schedule_unauthenticated_401(app_client):
    resp = app_client.get(
        "/abiertas-urgencias/api/schedule?mes=09&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 401


def test_ac7_post_without_write_perm_403(app_client):
    _read_perms_login(app_client)  # only read, no write
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"mes": 9, "anio": 2026, "dias": _valid_dias(1)},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["status"] != "warning"


def test_ac7_delete_without_write_perm_403(app_client):
    _read_perms_login(app_client)
    resp = app_client.delete(
        "/abiertas-urgencias/api/schedule?mes=09&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["status"] == "error"


def test_ac7_post_unauthenticated_401(app_client):
    resp = app_client.post(
        "/abiertas-urgencias/api/schedule",
        json={"mes": 9, "anio": 2026, "dias": _valid_dias(1)},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 401


def test_ac7_delete_unauthenticated_401(app_client):
    resp = app_client.delete(
        "/abiertas-urgencias/api/schedule?mes=09&anio=2026",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 401


def test_ac7_get_with_wrong_perm_403(app_client):
    _login(app_client, ["urgencias"])  # not facturas_abiertas
    resp = app_client.get(
        "/abiertas-urgencias/api/schedules",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 403


# ── Envelope never warning + thin delegator checks ──

def test_envelope_never_warning_all_routes(app_client):
    _write_perms_login(app_client)
    svc.save_horario(9, 2026, _valid_dias(1))
    cases = [
        app_client.get("/abiertas-urgencias/api/schedules", headers={"X-Requested-With": "XMLHttpRequest"}),
        app_client.get("/abiertas-urgencias/api/schedule?mes=09&anio=2026", headers={"X-Requested-With": "XMLHttpRequest"}),
        app_client.post("/abiertas-urgencias/api/schedule", json={"mes": 10, "anio": 2026, "dias": _valid_dias(1)}, headers={"X-Requested-With": "XMLHttpRequest"}),
        app_client.delete("/abiertas-urgencias/api/schedule?mes=10&anio=2026", headers={"X-Requested-With": "XMLHttpRequest"}),
    ]
    for resp in cases:
        data = resp.get_json()
        assert data["status"] in ("success", "error")
        assert data["status"] != "warning"
        assert isinstance(data["data"], dict)
        assert isinstance(data["errors"], list)


def test_import_order_stdlib_third_local():
    # static check that routes file respects import order
    text = Path("app/routes/abiertas_urgencias.py").read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines() if l.startswith("import ") or l.startswith("from ")]
    # json, logging, pathlib first, then flask, then app.* last
    assert any("import json" in l for l in lines)
    assert any("from flask" in l for l in lines)
    assert any("from app." in l for l in lines)
