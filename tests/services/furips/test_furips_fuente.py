"""Tests fuente FURIPS (odd furips-fuente, T7).

Patron: SQLite hermetico donde se puede; DB dev solo-lectura donde el
codigo lo exige (orquestador/exporter usan get_session interno).
FURIPS nunca persiste (persist=False fijo), asi que no hay writes.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_mapa_102_headers_unicos():
    from app.constants import FURIPS_HEADERS
    assert len(FURIPS_HEADERS) == 102
    assert len(set(FURIPS_HEADERS.values())) == 102


def test_required_headers_alias_factura():
    from app.constants import FURIPS_FACTURA_KEY, required_headers_for
    req = required_headers_for("furips")
    assert len(req) == 103  # 102 + alias numero_factura
    assert req["numero_factura"] == req[FURIPS_FACTURA_KEY]
    assert FURIPS_FACTURA_KEY == "c03_numero_de_factura"


def test_header_row_furips_es_2():
    # En Excel se ve en fila 3, pero Polars no materializa la fila 2 vacia.
    from app.constants import SOURCE_HEADER_ROWS
    assert SOURCE_HEADER_ROWS["furips"] == 2
    assert SOURCE_HEADER_ROWS["facturacion"] == 1


def test_vocabulario_incluye_furips():
    from app.constants import AREA_FURIPS, REGLA_DOMINIOS_VALIDOS
    from app.services.reglas.rule_service import _validate_dominios
    assert AREA_FURIPS == "furips"
    assert _validate_dominios(["furips"]) == ["furips"]
    assert "furips" in REGLA_DOMINIOS_VALIDOS


def _sqlite_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models import Regla
    import app.models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _add_rule(session, nombre, dominio):
    from app.models import Regla
    session.add(Regla(
        nombre=nombre, dominio=dominio, estado="active", version=1,
        prioridad=10, severidad="error", activo=True, grupo_error="G",
    ))
    session.commit()


def test_resolve_furips_excluye_transversal():
    from app.services.engine.rule_resolver import RuleResolver
    s = _sqlite_session()
    try:
        _add_rule(s, "r_trans", "transversal")
        _add_rule(s, "r_furips", "furips")
        got = RuleResolver().resolve("furips", s, include_transversal=False)
        assert [r.nombre for r in got] == ["r_furips"]
    finally:
        s.close()


def test_resolve_default_sigue_incluyendo_transversal():
    from app.services.engine.rule_resolver import RuleResolver
    s = _sqlite_session()
    try:
        _add_rule(s, "r_trans", "transversal")
        _add_rule(s, "r_odonto", "odontologia")
        got = RuleResolver().resolve("odontologia", s)
        assert sorted(r.nombre for r in got) == ["r_odonto", "r_trans"]
    finally:
        s.close()


def test_orquestador_furips_sin_reglas_vacio():
    """DB dev solo-lectura: hoy no hay reglas furips -> cero hallazgos."""
    from app.constants import FURIPS_HEADERS
    from app.services.furips.detect_all import detect_all_problems_furips
    idx = {k: i for i, k in enumerate(FURIPS_HEADERS)}
    idx["numero_factura"] = idx["c03_numero_de_factura"]
    rows = [{"c03_numero_de_factura": "F1", "numero_factura": "F1"}]
    res, resp = detect_all_problems_furips(None, idx, rows=rows)
    assert res["area"] == "furips"
    assert res["problemas"]["normalizados"] == []
    assert res["reglas_sin_datos"] == []
    assert resp == {}


def _write_xlsx(path: Path, headers: list[str], rows: list[list]):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([])  # fila 1: titulo (el best-match debe saltearla)
    ws.append([])  # fila 2: vacia
    ws.append(headers)  # fila 3: headers reales
    for r in rows:
        ws.append(r)
    wb.save(path)


def test_exporter_furips_fixture_102_headers():
    """Pipeline completo con fixture sintetico de 102 columnas."""
    from app.constants import FURIPS_HEADERS, AREA_FURIPS
    from app.services.exporter import detect_problems_only
    from app.utils.input_data import input_data_directory
    headers = list(FURIPS_HEADERS.values())
    i_fact = headers.index(FURIPS_HEADERS["c03_numero_de_factura"])
    rows = []
    for n in range(3):
        r = [""] * len(headers)
        r[i_fact] = f"FEV900{n}"
        rows.append(r)
    target = Path(str(input_data_directory())) / "furips_t7_fixture.xlsx"
    _write_xlsx(target, headers, rows)
    try:
        res, code = detect_problems_only(
            filename=target.name, area=AREA_FURIPS,
        )
    finally:
        target.unlink(missing_ok=True)
    assert code == 200
    assert res["status"] == "success"
    assert res["data"]["problemas"]["missing_columns"] == []


def test_anexo_map_y_apply():
    """Anexo: drop de invalidos, match por factura, display-only."""
    import shutil
    import openpyxl
    from app.services.exporter import _apply_anexo, _build_anexo_map
    from app.utils.input_data import input_data_directory, temp_upload_directory
    target = Path(str(input_data_directory())) / "furips_t7_principal.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Número Factura", "Entidad Cobrar"])
    ws.append(["F1", "EPS X"])
    ws.append(["F2", "EPS Y"])
    wb.save(target)
    tmpdir = Path(str(temp_upload_directory()))
    tmpdir.mkdir(parents=True, exist_ok=True)
    tmp = tmpdir / "furips_t7_principal.xlsx"
    shutil.copy(target, tmp)
    try:
        m = _build_anexo_map(
            str(tmp.resolve()),
            ["entidad_cobrar", "campo_inexistente"],
        )
    finally:
        tmp.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
    assert set(m) == {"F1", "F2"}
    assert m["F1"] == [{"campo": "Entidad Cobrar", "valor": "EPS X"}]
    det = {"problemas": {"normalizados": [{"factura": "F1"}, {"factura": "ZZ"}]}}
    _apply_anexo(det, m)
    assert det["problemas"]["normalizados"][0]["anexo"] == m["F1"]
    assert "anexo" not in det["problemas"]["normalizados"][1]
