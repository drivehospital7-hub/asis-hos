"""Tests para verificar_codigos_urgencias.py — migración a SQLAlchemy.

Cubre: Task 3.1 — reemplazar get_procedimiento() por query SQLAlchemy directa.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock, PropertyMock

import pytest


class TestVerificarCodigosUrgenciasSQLAlchemy:
    """Verifica que el script usa SQLAlchemy en vez de procedimientos_db."""

    def test_does_not_import_get_procedimiento(self):
        """El script NO DEBE importar get_procedimiento de procedimientos_db."""
        import app.services.verificar_codigos_urgencias as vcu

        source_file = vcu.__file__
        with open(source_file, encoding="utf-8") as f:
            content = f.read()

        assert "from app.services.procedimientos_db import get_procedimiento" not in content, (
            "get_procedimiento ya no debe importarse desde procedimientos_db"
        )

    def test_imports_sqlalchemy_models(self):
        """El script DEBE importar modelos SQLAlchemy y SessionLocal."""
        import app.services.verificar_codigos_urgencias as vcu

        source_file = vcu.__file__
        with open(source_file, encoding="utf-8") as f:
            content = f.read()

        assert "SessionLocal" in content, (
            "Debe importar SessionLocal de app.database"
        )
        assert "EpsContratado" in content, (
            "Debe importar EpsContratado de app.models"
        )
        assert "Procedimiento" in content, (
            "Debe importar Procedimiento de app.models"
        )

    def test_has_eps_name_to_cod_contrato_mapping(self):
        """Debe existir EPS_NAME_TO_COD_CONTRATO con EMSSANAR_CAPITA → ESS118."""
        import app.services.verificar_codigos_urgencias as vcu

        assert hasattr(vcu, "EPS_NAME_TO_COD_CONTRATO"), (
            "Debe existir EPS_NAME_TO_COD_CONTRATO"
        )
        mapping = vcu.EPS_NAME_TO_COD_CONTRATO
        assert isinstance(mapping, dict)
        assert "EMSSANAR_CAPITA" in mapping, (
            f"Debe incluir EMSSANAR_CAPITA. Keys: {list(mapping.keys())}"
        )
        assert mapping["EMSSANAR_CAPITA"] == "ESS118", (
            f"EMSSANAR_CAPITA debe mapear a ESS118, no a {mapping['EMSSANAR_CAPITA']}"
        )

    def test_verificar_excel_uses_sqlalchemy_not_psycopg2(self):
        """verificar_excel debe usar session.query(...) en vez de get_procedimiento()."""
        import app.services.verificar_codigos_urgencias as vcu

        source_file = vcu.__file__
        with open(source_file, encoding="utf-8") as f:
            content = f.read()

        # No debe llamar get_procedimiento
        assert "get_procedimiento(" not in content.replace(
            "def get_procedimiento", ""
        ), "No debe llamar get_procedimiento()"

        # Debe usar session.query
        assert "session.query" in content or ".query(" in content, (
            "Debe usar SQLAlchemy session.query()"
        )

    def test_eps_db_constant_still_exists(self):
        """EPS_DB = 'EMSSANAR_CAPITA' DEBE seguir existiendo como constante."""
        import app.services.verificar_codigos_urgencias as vcu

        assert hasattr(vcu, "EPS_DB"), "EPS_DB debe seguir existiendo"
        assert vcu.EPS_DB == "EMSSANAR_CAPITA", (
            f"EPS_DB debe ser 'EMSSANAR_CAPITA', no {vcu.EPS_DB}"
        )

    def test_verificar_excel_signature_unchanged(self):
        """La firma de verificar_excel no debe cambiar."""
        import inspect
        from app.services.verificar_codigos_urgencias import verificar_excel

        sig = inspect.signature(verificar_excel)
        params = list(sig.parameters.keys())
        assert params == ["excel_path"], (
            f"Firma esperada: (excel_path). Recibida: {params}"
        )

        # El tipo de retorno debe seguir siendo dict
        return_annotation = sig.return_annotation
        assert return_annotation is dict, (
            f"Retorno esperado: dict. Recibido: {return_annotation}"
        )
