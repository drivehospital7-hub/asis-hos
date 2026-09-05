"""Tests para scripts/reset_db.py.

Strict TDD: RED → GREEN → REFACTOR.
Este archivo se escribe PRIMERO (RED) con tests que fallan porque
el módulo scripts/reset_db.py aún no existe.
"""

import pytest


class TestDropTableOrder:
    """Verifica que el orden de DROP TABLE respeta dependencias de FKs.

    El orden debe ser inverso al de las FK: tablas con FKs primero,
    tablas referenciadas después. Con CASCADE el orden no es crítico
    técnicamente, pero debe ser explícito para logging y auditoría.
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Importa el módulo bajo test (fallará hasta que exista)."""
        from scripts.reset_db import DROP_TABLE_ORDER  # noqa: F811
        self.order = DROP_TABLE_ORDER

    def test_tiene_exactamente_7_tablas(self):
        """Debe listar las 7 tablas (5 funcionales + 2 cleanup)."""
        assert len(self.order) == 7

    def test_no_tiene_duplicados(self):
        """Cada tabla debe aparecer exactamente una vez."""
        assert len(self.order) == len(set(self.order))

    def test_todas_son_strings(self):
        """Cada entrada debe ser un string."""
        for name in self.order:
            assert isinstance(name, str), f"{name!r} no es string"

    def test_orden_eps_nota_primero(self):
        """eps_nota debe ser primero (tiene FK a eps_contratado y nota_hoja)."""
        assert self.order[0] == "eps_nota"

    def test_orden_users_ultimo(self):
        """users debe ser último (sin FKs)."""
        assert self.order[-1] == "users"

    def test_orden_completo_esperado(self):
        """Verifica el orden completo explícitamente."""
        assert self.order == [
            "eps_nota",
            "notas_tecnicas",
            "eps_contratado",
            "procedimiento",
            "nota_hoja",
            "user_areas",
            "users",
        ]

    def test_notas_tecnicas_antes_de_procedimiento(self):
        """notas_tecnicas (tiene FK a procedimiento) debe ir antes."""
        assert (
            self.order.index("notas_tecnicas")
            < self.order.index("procedimiento")
        )

    def test_eps_nota_antes_de_eps_contratado(self):
        """eps_nota (tiene FK a eps_contratado) debe ir antes."""
        assert (
            self.order.index("eps_nota")
            < self.order.index("eps_contratado")
        )


class TestResetDbMain:
    """Tests para la función main() del script."""

    def test_main_imports_sin_error(self):
        """El módulo debe poder importarse sin ejecutar main()."""
        import scripts.reset_db  # noqa: F401
        assert True

    def test_main_es_callable(self):
        """main() debe ser una función."""
        from scripts.reset_db import main
        assert callable(main)
