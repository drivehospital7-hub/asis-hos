"""Tests para la migración de procedimientos_db a la vista v_procedimientos.

Cubre: Task 1.1 (vista SQL) y Task 1.2 (reescritura de queries).
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ─── Task 1.1: Vista SQL v_procedimientos ────────────────────────────────


class TestVistaSQLMigration:
    """Verifica que el archivo de migración SQL contiene la vista correcta."""

    @pytest.fixture
    def sql_path(self) -> Path:
        return Path(__file__).parent.parent.parent / "migrations" / "003_create_v_procedimientos.sql"

    def test_migration_file_exists(self, sql_path: Path):
        """El archivo de migración DEBE existir."""
        assert sql_path.exists(), f"No se encontró {sql_path}"

    def test_contains_create_or_replace_view(self, sql_path: Path):
        """DEBE usar CREATE OR REPLACE VIEW para idempotencia."""
        content = sql_path.read_text(encoding="utf-8")
        assert "CREATE OR REPLACE VIEW v_procedimientos" in content, (
            "La vista DEBE usar CREATE OR REPLACE VIEW"
        )

    def test_contains_distinct_on(self, sql_path: Path):
        """DEBE usar DISTINCT ON (eps, codigo_cups) para deduplicar."""
        content = sql_path.read_text(encoding="utf-8")
        assert "DISTINCT ON" in content, "Debe usar DISTINCT ON para deduplicación"
        assert "eps" in content.lower() and "cups" in content.lower(), (
            "DISTINCT ON debe incluir eps y cups"
        )

    def test_contains_five_table_join(self, sql_path: Path):
        """DEBE hacer JOIN de las 5 tablas de la cadena."""
        content = sql_path.read_text(encoding="utf-8")
        tables = ["eps_contratado", "eps_nota", "nota_hoja", "notas_tecnicas", "procedimiento"]
        joined_tables = []
        for table in tables:
            # Buscar la tabla como tabla referenciada (FROM o JOIN)
            if re.search(rf"\b{table}\b", content, re.IGNORECASE):
                joined_tables.append(table)
        assert len(joined_tables) == 5, (
            f"Faltan tablas en el JOIN. Encontradas: {joined_tables}"
        )

    def test_has_row_number_id(self, sql_path: Path):
        """DEBE generar id con ROW_NUMBER()."""
        content = sql_path.read_text(encoding="utf-8")
        assert "ROW_NUMBER()" in content, "Debe usar ROW_NUMBER() para generar id"

    def test_order_by_tariff_desc(self, sql_path: Path):
        """DEBE ordenar por tariff DESC para prevalencia de tarifa más alta."""
        content = sql_path.read_text(encoding="utf-8")
        assert "tariff" in content.lower(), "Debe referenciar columna tariff"
        assert "DESC" in content, "Debe ordenar descending para tarifa más alta"


# ─── Task 1.2: procedimientos_db.py usa v_procedimientos ──────────────────


class TestProcedimientosDBQueriesTargetView:
    """Verifica que las queries de procedimientos_db usan v_procedimientos."""

    @pytest.fixture
    def mock_conn(self):
        """Mock de conexión psycopg2."""
        with patch("psycopg2.connect") as mock_connect:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            yield {
                "connect": mock_connect,
                "conn": mock_connection,
                "cursor": mock_cursor,
            }

    def _extract_sql_from_execute(self, mock_cursor: MagicMock) -> str:
        """Extrae el SQL ejecutado del mock del cursor."""
        calls = mock_cursor.execute.call_args_list
        if not calls:
            return ""
        return calls[0][0][0]  # Primer arg del primer call

    def test_get_procedimiento_queries_view_not_table(self, mock_conn):
        """get_procedimiento DEBE consultar v_procedimientos."""
        from app.services.procedimientos_db import get_procedimiento

        mock_conn["cursor"].fetchone.return_value = None

        get_procedimiento("EMSSANAR", "890201")

        sql = self._extract_sql_from_execute(mock_conn["cursor"])
        assert "v_procedimientos" in sql, (
            f"Query debe apuntar a v_procedimientos. SQL: {sql[:100]}"
        )
        assert "FROM procedimientos" not in sql.replace("v_procedimientos", ""), (
            "No debe referenciar la tabla 'procedimientos' directamente"
        )

    def test_get_all_by_codigo_queries_view(self, mock_conn):
        """get_all_by_codigo DEBE consultar v_procedimientos."""
        from app.services.procedimientos_db import get_all_by_codigo

        mock_conn["cursor"].fetchall.return_value = []

        get_all_by_codigo("890201")

        sql = self._extract_sql_from_execute(mock_conn["cursor"])
        assert "v_procedimientos" in sql, (
            f"get_all_by_codigo debe usar v_procedimientos. SQL: {sql[:100]}"
        )

    def test_get_all_by_eps_queries_view(self, mock_conn):
        """get_all_by_eps DEBE consultar v_procedimientos."""
        from app.services.procedimientos_db import get_all_by_eps

        mock_conn["cursor"].fetchall.return_value = []

        get_all_by_eps("EMSSANAR")

        sql = self._extract_sql_from_execute(mock_conn["cursor"])
        assert "v_procedimientos" in sql, (
            f"get_all_by_eps debe usar v_procedimientos. SQL: {sql[:100]}"
        )

    def test_get_eps_disponibles_queries_view(self, mock_conn):
        """get_eps_disponibles DEBE consultar v_procedimientos."""
        from app.services.procedimientos_db import get_eps_disponibles

        mock_conn["cursor"].fetchall.return_value = []

        get_eps_disponibles()

        sql = self._extract_sql_from_execute(mock_conn["cursor"])
        assert "v_procedimientos" in sql, (
            f"get_eps_disponibles debe usar v_procedimientos. SQL: {sql[:100]}"
        )


class TestProcedimientosDbMapping:
    """Verifica que el mapeo de filas a Procedimiento funciona con vista."""

    @pytest.fixture
    def mock_row_data(self):
        """Datos simulados de una fila de v_procedimientos."""
        return {
            "id": 42,
            "eps": "EMSSANAR",
            "codigo_cups": "890201",
            "descripcion": "EXODONIA",
            "tarifa": 45000.00,
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def mock_conn_with_row(self, mock_row_data):
        """Mock de psycopg2 que retorna una fila."""
        with patch("psycopg2.connect") as mock_connect:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = mock_row_data
            mock_cursor.fetchall.return_value = [mock_row_data]
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            yield {
                "connect": mock_connect,
                "conn": mock_connection,
                "cursor": mock_cursor,
            }

    def test_get_procedimiento_maps_id_to_str(self, mock_conn_with_row):
        """El id de la vista es INTEGER; el servicio DEBE convertirlo a str."""
        from app.services.procedimientos_db import get_procedimiento

        result = get_procedimiento("EMSSANAR", "890201")

        assert result is not None
        assert isinstance(result.id, str), f"id debe ser str, es {type(result.id)}"
        assert result.id == "42", f"id debe ser '42', es {result.id}"

    def test_get_procedimiento_maps_tarifa_to_float(self, mock_conn_with_row):
        """El campo tarifa DEBE convertirse a float."""
        from app.services.procedimientos_db import get_procedimiento

        result = get_procedimiento("EMSSANAR", "890201")

        assert result is not None
        assert isinstance(result.tarifa, float), f"tarifa debe ser float, es {type(result.tarifa)}"
        assert result.tarifa == 45000.00

    def test_verificar_tarifa_uses_get_procedimiento(self):
        """verificar_tarifa DEBE delegar en get_procedimiento y comparar."""
        from app.services.procedimientos_db import verificar_tarifa

        with patch("app.services.procedimientos_db.get_procedimiento") as mock_get:
            from dataclasses import dataclass

            @dataclass
            class FakeProc:
                id: str
                eps: str
                codigo_cups: str
                descripcion: str | None
                tarifa: float | None
                created_at: str | None = None
                updated_at: str | None = None

            mock_get.return_value = FakeProc(
                id="1", eps="EMSSANAR", codigo_cups="890201",
                descripcion="EXODONIA", tarifa=45000.00,
            )

            # Dentro de tolerancia
            ok, msg = verificar_tarifa("EMSSANAR", "890201", 45000.50, tolerancia=0.01)
            assert ok is False, f"45000.50 vs 45000.00 diff=0.50 > 0.01 debería ser False"
            assert "diff" in msg.lower()

            # Fuera de tolerancia
            ok2, msg2 = verificar_tarifa("EMSSANAR", "890201", 45000.00, tolerancia=0.01)
            assert ok2 is True, f"45000.00 vs 45000.00 diff=0 <= 0.01 debería ser True"

    def test_get_procedimiento_returns_none_when_not_found(self):
        """Si no hay fila, DEBE retornar None."""
        from app.services.procedimientos_db import get_procedimiento

        with patch("psycopg2.connect") as mock_connect:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection

            result = get_procedimiento("EMSSANAR", "999999")

        assert result is None

    def test_verificar_codigo_returns_false_when_not_found(self):
        """verificar_codigo DEBE retornar (False, mensaje) si no existe."""
        from app.services.procedimientos_db import verificar_codigo

        with patch("app.services.procedimientos_db.get_procedimiento", return_value=None):
            exists, msg = verificar_codigo("EMSSANAR", "999999")
            assert exists is False
            assert "no encontrado" in msg.lower()

    def test_verificar_codigo_returns_true_with_descripcion(self):
        """verificar_codigo DEBE retornar True con descripción si existe."""
        from app.services.procedimientos_db import verificar_codigo
        from dataclasses import dataclass

        @dataclass
        class FakeProc:
            id: str = "1"
            eps: str = "EMSSANAR"
            codigo_cups: str = "890201"
            descripcion: str | None = "EXODONIA"
            tarifa: float | None = 45000.00
            created_at: str | None = None
            updated_at: str | None = None

        with patch("app.services.procedimientos_db.get_procedimiento", return_value=FakeProc()):
            exists, msg = verificar_codigo("EMSSANAR", "890201")
            assert exists is True
            assert "890201" in msg
            assert "EXODONIA" in msg
