"""Unit tests for valores_no_catalogados (pure functions, no DB)."""

from app.services.transversales.valores_no_catalogados import (
    find_unrecognized_values,
    normalize_value,
)


def test_normalize_mirrors_engine_in():
    assert normalize_value("  Clinico. ") == "CLINICO."
    assert normalize_value("farmacia") == "FARMACIA"
    assert normalize_value(None) == ""
    assert normalize_value(5) == "5"


def test_known_values_not_reported_case_insensitive():
    rows = [
        {"centro_costo": "psicologia"},
        {"centro_costo": "  PSICOLOGIA "},
        {"centro_costo": None},
        {"otro": "x"},
    ]
    rec = {"centro_costo": {"PSICOLOGIA"}}
    assert find_unrecognized_values(rows, rec) == []


def test_unknown_reported_with_count_and_first_seen():
    rows = [
        {"centro_costo": "Nuevo Centro"},
        {"centro_costo": "NUEVO CENTRO"},
        {"centro_costo": "Otro"},
    ]
    rec = {"centro_costo": {"PSICOLOGIA"}}
    rep = find_unrecognized_values(rows, rec)
    assert rep == [
        {"campo": "centro_costo", "valor": "Nuevo Centro", "conteo": 2},
        {"campo": "centro_costo", "valor": "Otro", "conteo": 1},
    ]


def test_max_per_field_caps_output():
    rows = [{"c": f"v{i}"} for i in range(30)]
    rep = find_unrecognized_values(rows, {"c": set()}, max_per_field=5)
    assert len(rep) == 5


def test_tilde_change_is_reported():
    # Engine `in` is accent-sensitive: tilde change must warn.
    rows = [{"centro_costo": "PROMOCION Y PREVENCION"}]
    rec = {"centro_costo": {"PROMOCIÓN Y PREVENCIÓN"}}
    rep = find_unrecognized_values(rows, rec)
    assert len(rep) == 1 and rep[0]["conteo"] == 1
