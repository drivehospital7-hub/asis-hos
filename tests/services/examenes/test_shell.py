"""Integration tests for the /examenes shell route (EX-1/EX-21, task 2.1).

Covers: 200 with __INITIAL_DATA__ {username, permisos, can_write,
current_facturador}, can_write gating, admin `*` bypass, HTML redirect for
users without the permission, and session-composed facturador behavior
(composition, username fallback, empty, DB-down invariant — EX-21).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.constants.examenes import DEFAULT_EXAMENES
from app.utils import examenes_store, users_store


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect store IO to tmp so tests never touch app/data."""
    monkeypatch.setattr(examenes_store, "DATA_DIR", tmp_path)


def _authenticate(
    client,
    permisos: list[str],
    username: str = "test",
    primer_nombre: str = "",
    apellido_1: str = "",
) -> None:
    """Establece sesión autenticada con los permisos y campos de nombre dados."""
    with client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = username
        sess["permisos"] = permisos
        sess["primer_nombre"] = primer_nombre
        sess["apellido_1"] = apellido_1


def _extract_initial_data(response) -> dict[str, Any]:
    """Extrae y parsea window.__INITIAL_DATA__ desde el HTML del shell."""
    match = re.search(
        r"window\.__INITIAL_DATA__ = (.*?);\s*</script>",
        response.get_data(as_text=True),
        re.DOTALL,
    )
    assert match is not None, "shell HTML must embed __INITIAL_DATA__"
    return json.loads(match.group(1))


class TestShell200:
    """GET /examenes with the permission → 200 shell + initial data."""

    def test_read_only_shell_initial_data(self, app_client) -> None:
        """Read-only user → 200; can_write False; username fallback (EX-21)."""
        _authenticate(app_client, ["examenes"], username="lectora")

        response = app_client.get("/examenes")

        assert response.status_code == 200
        data = _extract_initial_data(response)
        assert data["username"] == "lectora"
        assert data["permisos"] == ["examenes"]
        assert data["can_write"] is False
        assert data["current_facturador"] == "LECTORA"

    def test_write_shell_can_write_true(self, app_client) -> None:
        """examenes:write user → can_write True (Admin tab + save gating)."""
        _authenticate(app_client, ["examenes:write"])

        response = app_client.get("/examenes")

        assert response.status_code == 200
        data = _extract_initial_data(response)
        assert data["can_write"] is True
        assert "facturadores" not in data

    def test_admin_bypass(self, app_client) -> None:
        """Admin (*) → 200 with can_write True (EX-1 admin scenario)."""
        _authenticate(app_client, ["*"], username="admin")

        response = app_client.get("/examenes")

        assert response.status_code == 200
        data = _extract_initial_data(response)
        assert data["can_write"] is True
        assert data["username"] == "admin"

    def test_shell_renders_page_title(self, app_client) -> None:
        """Shell HTML carries the module title."""
        _authenticate(app_client, ["examenes"])
        html = app_client.get("/examenes").get_data(as_text=True)
        assert "Exámenes" in html

    def test_shell_exposes_default_examenes(self, app_client) -> None:
        """Shell exposes the authoritative catalog defaults for Admin restore
        (EX-16 frontend): DEFAULT_EXAMENES verbatim, 66 entries, not a
        hardcoded client-side copy."""
        _authenticate(app_client, ["examenes:write"])
        data = _extract_initial_data(app_client.get("/examenes"))
        assert data["default_examenes"] == DEFAULT_EXAMENES
        assert len(data["default_examenes"]) == 66


class TestShellDenied:
    """EX-1 denied: HTML request without permission → logout + redirect."""

    def test_user_without_permission_redirects_to_login(self, app_client) -> None:
        """urgencias-only user → 302 redirect to /auth/login (HTML flow)."""
        _authenticate(app_client, ["urgencias"], username="urgencias")

        response = app_client.get("/examenes")

        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("Location", "")

    def test_anonymous_html_request_401(self, app_client) -> None:
        """No session at all → 401 (global middleware), not the shell."""
        response = app_client.get("/examenes")
        assert response.status_code == 401


class TestShellCurrentFacturador:
    """EX-21: current_facturador compuesto desde la sesión, CERO consultas DB."""

    def test_composes_uppercase_name_from_session(self, app_client) -> None:
        """primer_nombre + apellido_1 → UPPERCASE joined name (EX-21 happy)."""
        _authenticate(
            app_client, ["examenes"], primer_nombre="ANGIE ", apellido_1="ARIAS "
        )

        data = _extract_initial_data(app_client.get("/examenes"))

        assert data["current_facturador"] == "ANGIE ARIAS"

    def test_username_fallback_when_names_absent(self, app_client) -> None:
        """Sin campos de nombre → username en mayúsculas (EX-21 fallback)."""
        _authenticate(app_client, ["examenes"], username="lectora")

        data = _extract_initial_data(app_client.get("/examenes"))

        assert data["current_facturador"] == "LECTORA"

    def test_empty_when_no_name_and_no_username(self, app_client) -> None:
        """Sin nombre ni username → "" (el frontend mapea "" → "—")."""
        _authenticate(app_client, ["examenes"], username="")

        data = _extract_initial_data(app_client.get("/examenes"))

        assert data["current_facturador"] == ""

    def test_shell_200_composes_from_session_when_db_down(
        self, app_client, monkeypatch
    ) -> None:
        """DB caída → shell 200; current_facturador sale SOLO de la sesión
        (invariante EX-21, antes test_shell.py:189-201)."""

        def boom():
            raise RuntimeError("db down")

        monkeypatch.setattr(users_store, "SessionLocal", boom)
        _authenticate(app_client, ["examenes"], primer_nombre="ANGIE", apellido_1="ARIAS")

        response = app_client.get("/examenes")

        assert response.status_code == 200
        data = _extract_initial_data(response)
        assert data["current_facturador"] == "ANGIE ARIAS"