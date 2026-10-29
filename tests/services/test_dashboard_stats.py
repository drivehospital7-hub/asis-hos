"""KPIs del dashboard: calculo, filtro por mes y envelope."""

from __future__ import annotations

from datetime import datetime

import pytest


def _errores(monkeypatch, items):
    from app.services import dashboard_stats as ds

    monkeypatch.setattr(ds, "listar_errores", lambda *a, **k: items)


def test_cuenta_solo_el_mes_actual(monkeypatch):
    from app.services.dashboard_stats import get_dashboard_stats

    _errores(monkeypatch, [
        {"creado_en": "2026-10-01 09:00:00", "estado": "S"},
        {"creado_en": "2026-10-20 09:00:00", "estado": "N"},
        {"creado_en": "2026-09-30 09:00:00", "estado": "S"},  # otro mes
    ])
    r = get_dashboard_stats(now=datetime(2026, 10, 25))
    assert r["status"] == "success"
    valores = {k["label"]: k["value"] for k in r["data"]["kpis"]}
    assert valores["Novedades del mes"] == "2"
    assert valores["Pendientes"] == "1"
    assert valores["Resueltas este mes"] == "1"
    assert valores["Tasa de resolución"] == "50%"


def test_mes_vacio_da_ceros(monkeypatch):
    from app.services.dashboard_stats import get_dashboard_stats

    _errores(monkeypatch, [])
    r = get_dashboard_stats(now=datetime(2026, 10, 25))
    valores = {k["label"]: k["value"] for k in r["data"]["kpis"]}
    assert valores["Novedades del mes"] == "0"
    assert valores["Tasa de resolución"] == "0%"


def test_label_mes_en_espanol(monkeypatch):
    from app.services.dashboard_stats import get_dashboard_stats

    _errores(monkeypatch, [])
    r = get_dashboard_stats(now=datetime(2026, 10, 25))
    assert r["data"]["month_label"] == "Octubre 2026"


def test_error_devuelve_envelope_error(monkeypatch):
    from app.services import dashboard_stats as ds

    def boom(*a, **k):
        raise RuntimeError("fallo lectura")

    monkeypatch.setattr(ds, "listar_errores", boom)
    r = ds.get_dashboard_stats(now=datetime(2026, 10, 25))
    assert r["status"] == "error"
    assert r["errors"] and "fallo lectura" in r["errors"][0]
    assert r["data"] == {}
