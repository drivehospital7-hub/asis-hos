"""Integration tests for /busqueda-pdf/ API endpoints."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["username"] = "test"
            sess["permisos"] = ["busqueda_pdf"]
        yield c


@pytest.fixture
def pdf_base(tmp_path: Path) -> Path:
    base = tmp_path / "PDF_BASE"
    base.mkdir()
    return base


def _crear_pdf_minimo(ruta: Path, texto: str = ""):
    """Create a minimal valid PDF using fitz."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    if texto:
        page.insert_text((50, 100), texto, fontsize=11)
    doc.save(str(ruta))
    doc.close()


def test_buscar_endpoint(client, pdf_base, monkeypatch):
    """POST /busqueda-pdf/buscar with valid inputs returns results."""
    from app.constants.busqueda_pdf import PDF_BASE_PATH
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", str(pdf_base))

    pdf_path = pdf_base / "informe.pdf"
    _crear_pdf_minimo(pdf_path, texto="El Peatón fue atropellado por una Buseta.")

    ruta = str(pdf_base)
    response = client.post(
        "/busqueda-pdf/buscar",
        data=json.dumps({
            "ruta": ruta,
            "condicion": "Conductor",
            "transporte": "Automóvil",
        }),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert len(data["data"]["resultados"]) >= 1
    assert data["data"]["resumen"]["pdfs_procesados"] >= 1
    assert data["data"]["resumen"]["pdfs_con_hallazgos"] >= 1


def test_listar_directorios(client, pdf_base, monkeypatch):
    """GET /busqueda-pdf/listar-directorios returns subdir listing."""
    from app.constants.busqueda_pdf import PDF_BASE_PATH
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", str(pdf_base))

    subdir = pdf_base / "subcarpeta"
    subdir.mkdir()

    pdf_file = pdf_base / "documento.pdf"
    pdf_file.write_text("dummy")

    ruta = str(pdf_base)
    response = client.get(f"/busqueda-pdf/listar-directorios?ruta={ruta}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert len(data["data"]["directorios"]) == 1
    assert data["data"]["directorios"][0]["nombre"] == "subcarpeta"
    assert "documento.pdf" in data["data"]["pdfs"]


def test_listar_directorios_path_traversal(client, pdf_base, monkeypatch):
    """Path with '..' returns 400."""
    from app.constants.busqueda_pdf import PDF_BASE_PATH
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", str(pdf_base))

    response = client.get("/busqueda-pdf/listar-directorios?ruta=D:\\..\\Windows")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_listar_directorios_invalid_path(client, pdf_base, monkeypatch):
    """Nonexistent path returns 400."""
    from app.constants.busqueda_pdf import PDF_BASE_PATH
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", str(pdf_base))

    response = client.get("/busqueda-pdf/listar-directorios?ruta=D:\\no_existe")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_buscar_ruta_vacia(client, pdf_base, monkeypatch):
    """POST with empty ruta returns 400."""
    from app.constants.busqueda_pdf import PDF_BASE_PATH
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", str(pdf_base))

    response = client.post(
        "/busqueda-pdf/buscar",
        data=json.dumps({"ruta": "", "condicion": "Conductor", "transporte": "Automóvil"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_listar_directorios_ruta_fuera_base(client, pdf_base, monkeypatch):
    """Path outside PDF_BASE_PATH returns 400 in restricted mode."""
    # Restricted mode: bases explicitly set to pdf_base
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATHS", [str(pdf_base)])
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", str(pdf_base))

    outside = str(pdf_base.parent / "outside_dir")
    response = client.get(f"/busqueda-pdf/listar-directorios?ruta={outside}")
    assert response.status_code == 400


def test_listar_directorios_modo_abierto_permite_cualquier_ruta_absoluta(client, pdf_base, tmp_path, monkeypatch):
    """Open mode (empty bases) allows any absolute path that exists."""
    # Open mode: no base restriction
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATHS", [])
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", "")

    outside = tmp_path / "outside_open"
    outside.mkdir()
    (outside / "doc.pdf").write_text("dummy")

    response = client.get(f"/busqueda-pdf/listar-directorios?ruta={outside}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"


def test_listar_directorios_modo_abierto_bloquea_ruta_relativa(client, pdf_base, monkeypatch):
    """Open mode still blocks relative paths."""
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATHS", [])
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", "")

    response = client.get("/busqueda-pdf/listar-directorios?ruta=relativa/ruta")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_listar_directorios_modo_abierto_unc_mock(client, pdf_base, monkeypatch):
    """Open mode allows UNC-like absolute paths when isdir mocked."""
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATHS", [])
    monkeypatch.setattr("app.constants.busqueda_pdf.PDF_BASE_PATH", "")

    unc_path = "\\\\192.168.0.124\\facturacion"
    # Mock isdir to simulate reachable share
    monkeypatch.setattr("os.path.isdir", lambda p: p == os.path.normpath(unc_path))
    monkeypatch.setattr("os.listdir", lambda p: [])

    response = client.get(f"/busqueda-pdf/listar-directorios?ruta={unc_path}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"


def test_get_sinonimos_vacio(client, monkeypatch):
    """GET /busqueda-pdf/sinonimos returns empty dict when no saved synonyms."""
    monkeypatch.setattr(
        "app.routes.busqueda_pdf.cargar_sinonimos",
        lambda: {},
    )
    response = client.get("/busqueda-pdf/sinonimos")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["data"]["sinonimos"] == {}


def test_post_sinonimos_guarda(client, monkeypatch):
    """POST /busqueda-pdf/sinonimos saves and returns the synonyms."""
    saved = []

    def mock_guardar(s):
        saved.append(s)

    monkeypatch.setattr("app.routes.busqueda_pdf.guardar_sinonimos", mock_guardar)

    sinonimos = {"Ocupante": ["Acompañante", "Pasajero"], "Conductor": ["Chofer"]}
    response = client.post(
        "/busqueda-pdf/sinonimos",
        data=json.dumps({"sinonimos": sinonimos}),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["data"]["sinonimos"] == sinonimos
    assert saved[0] == sinonimos


def test_post_sinonimos_sin_campo(client):
    """POST without 'sinonimos' field returns 400."""
    response = client.post(
        "/busqueda-pdf/sinonimos",
        data=json.dumps({"otro": "valor"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_post_sinonimos_no_dict(client):
    """POST with non-dict 'sinonimos' returns 400."""
    response = client.post(
        "/busqueda-pdf/sinonimos",
        data=json.dumps({"sinonimos": "no soy dict"}),
        content_type="application/json",
    )
    assert response.status_code == 400
