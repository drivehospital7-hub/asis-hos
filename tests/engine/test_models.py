"""Unit tests for rule engine SQLAlchemy models.

Verifies table names, columns, relationships, and to_dict() per design spec.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Integer, String, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

from app.database import Base


class TestReglaModel:
    """Tests for Regla model (tablename: reglas)."""

    def test_tablename(self):
        from app.models import Regla
        assert Regla.__tablename__ == "reglas"

    def test_has_required_columns(self):
        from app.models import Regla
        cols = {c.name: c.type for c in Regla.__table__.columns}
        assert "id" in cols
        assert "rule_base_id" in cols
        assert "nombre" in cols
        assert "descripcion" in cols
        assert "dominio" in cols
        assert "estado" in cols
        assert "version" in cols
        assert "prioridad" in cols
        assert "parametros" in cols
        assert "parametros_default" in cols
        assert "severidad" in cols
        assert "activo" in cols
        assert "creado_en" in cols
        assert "actualizado_en" in cols

    def test_nombre_is_not_unique(self):
        """Unique constraint moved to (nombre, version) composite."""
        from app.models import Regla
        nombre_col = Regla.__table__.columns["nombre"]
        assert nombre_col.unique is not True

    def test_has_rule_base_id(self):
        """Rule has rule_base_id column for version grouping."""
        from app.models import Regla
        assert "rule_base_id" in Regla.__table__.columns

    def test_has_nombre_version_unique_constraint(self):
        """Regla has composite unique on (nombre, version)."""
        from app.models import Regla
        constraints = Regla.__table__.constraints
        uq_names = {c.name for c in constraints if hasattr(c, 'columns') and 'nombre' in c.columns}
        has_constraint = any(
            {'nombre', 'version'}.issubset(set(c.columns.keys()))
            for c in constraints if hasattr(c, 'columns')
        )
        assert has_constraint, "Expected composite unique (nombre, version)"

    def test_estado_default_draft(self):
        from app.models import Regla
        estado_col = Regla.__table__.columns["estado"]
        assert estado_col.default.arg == "draft"

    def test_severidad_default_error(self):
        from app.models import Regla
        severidad_col = Regla.__table__.columns["severidad"]
        assert severidad_col.default.arg == "error"

    def test_activo_default_true(self):
        from app.models import Regla
        activo_col = Regla.__table__.columns["activo"]
        assert activo_col.default.arg is True

    def test_prioridad_default_100(self):
        from app.models import Regla
        prioridad_col = Regla.__table__.columns["prioridad"]
        assert prioridad_col.default.arg == 100

    def test_version_default_1(self):
        from app.models import Regla
        version_col = Regla.__table__.columns["version"]
        assert version_col.default.arg == 1

    def test_to_dict_returns_expected_keys(self):
        from app.models import Regla
        regla = Regla(
            id=1,
            nombre="valores_decimales",
            descripcion="Detecta decimales",
            dominio="odontologia",
            estado="active",
            version=1,
            prioridad=10,
            severidad="error",
            activo=True,
        )
        d = regla.to_dict()
        assert d["id"] == 1
        assert d["nombre"] == "valores_decimales"
        assert d["dominio"] == "odontologia"
        assert d["estado"] == "active"
        assert d["version"] == 1


class TestCondicionModel:
    """Tests for Condicion model (tablename: condiciones)."""

    def test_tablename(self):
        from app.models import Condicion
        assert Condicion.__tablename__ == "condiciones"

    def test_has_required_columns(self):
        from app.models import Condicion
        cols = {c.name for c in Condicion.__table__.columns}
        assert "id" in cols
        assert "regla_id" in cols
        assert "padre_id" in cols
        assert "tipo" in cols
        assert "operador" in cols
        assert "fuente_datos" in cols
        assert "valor_esperado" in cols
        assert "orden" in cols

    def test_orden_default_0(self):
        from app.models import Condicion
        orden_col = Condicion.__table__.columns["orden"]
        assert orden_col.default.arg == 0

    def test_tipo_not_null(self):
        from app.models import Condicion
        tipo_col = Condicion.__table__.columns["tipo"]
        assert tipo_col.nullable is False

    def test_to_dict_returns_expected_keys(self):
        from app.models import Condicion
        cond = Condicion(
            id=1,
            regla_id=1,
            padre_id=None,
            tipo="atomic",
            operador="eq",
            fuente_datos="invoice.vlr_subsidiado",
            valor_esperado=None,
            orden=0,
        )
        d = cond.to_dict()
        assert d["id"] == 1
        assert d["tipo"] == "atomic"
        assert d["operador"] == "eq"


class TestExcepcionModel:
    """Tests for Excepcion model (tablename: excepciones)."""

    def test_tablename(self):
        from app.models import Excepcion
        assert Excepcion.__tablename__ == "excepciones"

    def test_has_required_columns(self):
        from app.models import Excepcion
        cols = {c.name for c in Excepcion.__table__.columns}
        assert "id" in cols
        assert "regla_id" in cols
        assert "tipo_efecto" in cols
        assert "condicion_json" in cols
        assert "parametros_override" in cols
        assert "activo" in cols
        assert "creado_en" in cols
        assert "expira_en" in cols

    def test_activo_default_true(self):
        from app.models import Excepcion
        activo_col = Excepcion.__table__.columns["activo"]
        assert activo_col.default.arg is True

    def test_to_dict_returns_expected_keys(self):
        from app.models import Excepcion
        exc = Excepcion(
            id=1,
            regla_id=1,
            tipo_efecto="skip",
            condicion_json={"convenio": "PyP"},
            activo=True,
        )
        d = exc.to_dict()
        assert d["id"] == 1
        assert d["tipo_efecto"] == "skip"


class TestResultadoAuditoriaModel:
    """Tests for ResultadoAuditoria model (tablename: resultados_auditoria)."""

    def test_tablename(self):
        from app.models import ResultadoAuditoria
        assert ResultadoAuditoria.__tablename__ == "resultados_auditoria"

    def test_has_required_columns(self):
        from app.models import ResultadoAuditoria
        cols = {c.name for c in ResultadoAuditoria.__table__.columns}
        assert "id" in cols
        assert "evidencia_id" in cols
        assert "regla_id" in cols
        assert "regla_version" in cols
        assert "factura" in cols
        assert "param_config_id" in cols
        assert "resultado" in cols
        assert "severidad" in cols
        assert "mensaje" in cols
        assert "detalles" in cols
        assert "creado_en" in cols

    def test_to_dict_returns_expected_keys(self):
        from app.models import ResultadoAuditoria
        res = ResultadoAuditoria(
            id=1,
            evidencia_id=42,
            regla_id=1,
            regla_version=1,
            factura="F001",
            resultado="FAIL",
            severidad="error",
        )
        d = res.to_dict()
        assert d["id"] == 1
        assert d["resultado"] == "FAIL"


class TestEvidenciaModel:
    """Tests for Evidencia model (tablename: evidencias)."""

    def test_tablename(self):
        from app.models import Evidencia
        assert Evidencia.__tablename__ == "evidencias"

    def test_has_required_columns(self):
        from app.models import Evidencia
        cols = {c.name for c in Evidencia.__table__.columns}
        assert "id" in cols
        assert "regla_id" in cols
        assert "regla_version" in cols
        assert "dominio" in cols
        assert "factura" in cols
        assert "param_config_id" in cols
        assert "outcome" in cols
        assert "arbol_evaluado" in cols
        assert "snapshot_fila" in cols
        assert "snapshot_referencia" in cols
        assert "error_mensaje" in cols
        assert "creado_en" in cols

    def test_to_dict_returns_expected_keys(self):
        from app.models import Evidencia
        ev = Evidencia(
            id=1,
            regla_id=1,
            regla_version=1,
            dominio="odontologia",
            factura="F001",
            outcome="MATCH",
            arbol_evaluado=[],
            snapshot_fila={},
        )
        d = ev.to_dict()
        assert d["id"] == 1
        assert d["outcome"] == "MATCH"


class TestModelRegistrationInBase:
    """Verify all 5 engine models are registered in Base.metadata."""

    def test_all_engine_models_in_base_metadata(self):
        from app import models as _  # noqa: F401 — force import registration
        table_names = set(Base.metadata.tables.keys())
        assert "reglas" in table_names
        assert "condiciones" in table_names
        assert "excepciones" in table_names
        assert "resultados_auditoria" in table_names
        assert "evidencias" in table_names
