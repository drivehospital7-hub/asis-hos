"""Unit tests for eps_cups_contratado evaluator (hermetic SQLite)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import EpsContratado, EpsNota, NotaHoja, NotasTecnicas, Procedimiento
import app.models  # noqa: F401
from app.services.engine.context import EvaluationContext
from app.services.engine.evaluators import get_evaluator


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    # EPS + hoja + procedimiento + cruces
    eps = EpsContratado(cod_contrato="ESS118", eps="PRUEBAS COVID", regimen="Subsidiado")
    hoja = NotaHoja(nota="EMSSANAR CAPITA")
    proc = Procedimiento(cups="890201", procedimiento="Consulta", ide=1)
    proc_fuera = Procedimiento(cups="999999", procedimiento="Otro", ide=2)
    s.add_all([eps, hoja, proc, proc_fuera])
    s.flush()
    s.add(EpsNota(id_nota_hoja=hoja.id, id_eps_contratado=eps.id))
    s.add(NotasTecnicas(id_procedimiento=proc.id, id_nota_hoja=hoja.id, tariff=0))
    s.commit()
    try:
        yield s
    finally:
        s.close()


def _ctx(session, row):
    return EvaluationContext(invoice_data=row, session=session)


def test_contratado_por_cod_contrato(session):
    ev = get_evaluator("eps_cups_contratado")
    assert ev is not None
    ctx = _ctx(session, {"codigo_entidad_cobrar": "ESS118", "codigo": "890201"})
    assert ev.evaluate({}, "890201", None, ctx) is True


def test_nombre_solo_no_contrata(session):
    """El nombre no participa: solo codigo_entidad_cobrar matchea."""
    ev = get_evaluator("eps_cups_contratado")
    ctx = _ctx(session, {"entidad_cobrar": "pruebas covid", "codigo": "890201"})
    assert ev.evaluate({}, "890201", None, ctx) is False


def test_nombre_en_columna_codigo_no_contrata(session):
    ev = get_evaluator("eps_cups_contratado")
    ctx = _ctx(session, {"codigo_entidad_cobrar": "pruebas covid", "codigo": "890201"})
    assert ev.evaluate({}, "890201", None, ctx) is False


def test_no_contratado_otro_codigo(session):
    ev = get_evaluator("eps_cups_contratado")
    ctx = _ctx(session, {"codigo_entidad_cobrar": "ESS118", "codigo": "999999"})
    assert ev.evaluate({}, "999999", None, ctx) is False


def test_no_contratado_otra_eps(session):
    ev = get_evaluator("eps_cups_contratado")
    ctx = _ctx(session, {"codigo_entidad_cobrar": "EPS999", "codigo": "890201"})
    assert ev.evaluate({}, "890201", None, ctx) is False


def test_nombre_en_columna_codigo_no_contrata(session):
    """Politica estricta: aunque el texto exista como nombre en base,
    en la columna de codigo solo vale el codigo."""
    ev = get_evaluator("eps_cups_contratado")
    ctx = EvaluationContext(
        invoice_data={
            "codigo_entidad_cobrar": "pruebas covid",
            "entidad_cobrar": "otra razon social",
            "codigo": "890201",
        },
        session=session,
    )
    assert ev.evaluate({}, "890201", None, ctx) is False


def test_sin_codigo_o_entidad_no_matchea(session):
    ev = get_evaluator("eps_cups_contratado")
    assert ev.evaluate({}, None, None, _ctx(session, {"codigo_entidad_cobrar": "ESS118"})) is False
    assert ev.evaluate({}, "890201", None, _ctx(session, {})) is False
    assert ev.evaluate({}, "890201", None, None) is False


def test_eps_tiene_nota_true(session):
    ev = get_evaluator("eps_tiene_nota")
    assert ev is not None
    ctx = _ctx(session, {})
    assert ev.evaluate({}, "ESS118", None, ctx) is True


def test_eps_tiene_nota_false_sin_vinculo(session):
    from app.models import EpsContratado
    session.add(EpsContratado(cod_contrato="EPS999", eps="Sin Nota", regimen="Subsidiado"))
    session.commit()
    ev = get_evaluator("eps_tiene_nota")
    ctx = _ctx(session, {})
    assert ev.evaluate({}, "EPS999", None, ctx) is False


def test_eps_tiene_nota_vacio_no(session):
    ev = get_evaluator("eps_tiene_nota")
    ctx = _ctx(session, {})
    assert ev.evaluate({}, "", None, ctx) is False
    assert ev.evaluate({}, None, None, ctx) is False


def _session_flujo():
    import sqlite3  # noqa
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models import EpsContratado, EpsNota, NotaHoja, NotasTecnicas, Procedimiento
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    eps = EpsContratado(cod_contrato="ESS118", eps="E", regimen="S")
    ncap = NotaHoja(nota="EMSSANAR CAPITA")
    neve = NotaHoja(nota="EMSSANAR SUBSIDIADO")
    p = Procedimiento(cups="890201", procedimiento="C", ide=1)
    s.add_all([eps, ncap, neve, p])
    s.flush()
    s.add(EpsNota(id_nota_hoja=ncap.id, id_eps_contratado=eps.id))
    s.add(EpsNota(id_nota_hoja=neve.id, id_eps_contratado=eps.id))
    s.add(NotasTecnicas(id_procedimiento=p.id, id_nota_hoja=ncap.id, tariff=0))
    s.commit()
    return s


def test_flujo_capita_vs_evento_en_par():
    from app.services.engine.context import EvaluationContext
    s = _session_flujo()
    try:
        ev = get_evaluator("eps_cups_contratado")
        base = {"codigo_entidad_cobrar": "ESS118", "codigo": "890201"}
        assert ev.evaluate({}, "890201", "capita", EvaluationContext(invoice_data=dict(base), session=s)) is True
        assert ev.evaluate({}, "890201", "evento", EvaluationContext(invoice_data=dict(base), session=s)) is False
        assert ev.evaluate({}, "890201", None, EvaluationContext(invoice_data=dict(base), session=s)) is True
    finally:
        s.close()


def test_flujo_en_tiene_nota():
    from app.services.engine.context import EvaluationContext
    s = _session_flujo()
    try:
        ev = get_evaluator("eps_tiene_nota")
        assert ev.evaluate({}, "ESS118", "capita", EvaluationContext(invoice_data={}, session=s)) is True
        assert ev.evaluate({}, "ESS118", "evento", EvaluationContext(invoice_data={}, session=s)) is True
        assert ev.evaluate({}, "OTRA", "capita", EvaluationContext(invoice_data={}, session=s)) is False
        # EPS solo-capita no tiene nota de evento
        from app.models import EpsContratado, EpsNota
        eps2 = EpsContratado(cod_contrato="SOLOCAP", eps="X", regimen="S")
        s.add(eps2)
        s.flush()
        hoja = s.query(NotaHoja).filter_by(nota="EMSSANAR CAPITA").first()
        s.add(EpsNota(id_nota_hoja=hoja.id, id_eps_contratado=eps2.id))
        s.commit()
        assert ev.evaluate({}, "SOLOCAP", "capita", EvaluationContext(invoice_data={}, session=s)) is True
        assert ev.evaluate({}, "SOLOCAP", "evento", EvaluationContext(invoice_data={}, session=s)) is False
    finally:
        s.close()
