"""Tests for busqueda_pdf.sinonimos_storage — cargar/guardar sinónimos."""

import json

import pytest

from app.services.busqueda_pdf.sinonimos_storage import cargar_sinonimos, guardar_sinonimos, _SYNONYMS_FILE


def test_cargar_sinonimos_sin_archivo(tmp_path, monkeypatch):
    """When file doesn't exist → returns empty dict."""
    inexistente = tmp_path / "no_existe.json"
    monkeypatch.setattr("app.services.busqueda_pdf.sinonimos_storage._SYNONYMS_FILE", inexistente)
    assert cargar_sinonimos() == {}


def test_guardar_y_cargar(tmp_path, monkeypatch):
    """Save then load returns the same data."""
    archivo = tmp_path / "sinonimos.json"
    monkeypatch.setattr("app.services.busqueda_pdf.sinonimos_storage._SYNONYMS_FILE", archivo)

    data = {"Ocupante": ["Acompañante", "Pasajero"], "Conductor": ["Chofer"]}
    guardar_sinonimos(data)
    assert archivo.exists()

    cargado = cargar_sinonimos()
    assert cargado == data


def test_cargar_json_corrupto(tmp_path, monkeypatch):
    """Corrupt JSON file → returns empty dict."""
    archivo = tmp_path / "sinonimos.json"
    archivo.write_text("{mal json", encoding="utf-8")
    monkeypatch.setattr("app.services.busqueda_pdf.sinonimos_storage._SYNONYMS_FILE", archivo)

    assert cargar_sinonimos() == {}


def test_cargar_no_es_dict(tmp_path, monkeypatch):
    """JSON file contains a list instead of dict → returns empty dict."""
    archivo = tmp_path / "sinonimos.json"
    archivo.write_text(json.dumps(["a", "b"]), encoding="utf-8")
    monkeypatch.setattr("app.services.busqueda_pdf.sinonimos_storage._SYNONYMS_FILE", archivo)

    assert cargar_sinonimos() == {}


def test_guardar_vacio(tmp_path, monkeypatch):
    """Saving empty dict works."""
    archivo = tmp_path / "sinonimos.json"
    monkeypatch.setattr("app.services.busqueda_pdf.sinonimos_storage._SYNONYMS_FILE", archivo)

    guardar_sinonimos({})
    assert archivo.exists()
    assert json.loads(archivo.read_text(encoding="utf-8")) == {}
