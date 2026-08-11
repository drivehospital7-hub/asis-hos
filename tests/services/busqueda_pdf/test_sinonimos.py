"""Tests for busqueda_pdf.sononimos — merge_sinonimos()."""

from app.services.busqueda_pdf.sinonimos import merge_sinonimos


def test_merge_sinonimos_none():
    """Custom sinonimos is None → only defaults returned."""
    result = merge_sinonimos(None)
    assert "Ocupante" in result
    assert "Acompañante" in result["Ocupante"]
    assert "Pasajero" in result["Ocupante"]
    assert len(result) == 1


def test_merge_sinonimos_empty():
    """Custom sinonimos is empty dict → only defaults returned."""
    result = merge_sinonimos({})
    assert result == {"Ocupante": ["Acompañante", "Pasajero"]}


def test_merge_sinonimos_partial():
    """Custom adds a new key not in defaults — merged."""
    result = merge_sinonimos({"Conductor": ["Chofer"]})
    assert "Ocupante" in result  # defaults preserved
    assert "Conductor" in result  # new key added
    assert result["Conductor"] == ["Chofer"]
    assert "Acompañante" in result["Ocupante"]


def test_merge_sinonimos_override():
    """Custom replaces a key that exists in defaults."""
    result = merge_sinonimos({"Ocupante": ["Custom"]})
    assert result["Ocupante"] == ["Custom"]
    assert "Pasajero" not in result["Ocupante"]
