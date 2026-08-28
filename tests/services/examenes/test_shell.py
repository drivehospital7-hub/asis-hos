"""Integration tests for the /examenes shell route (EX-1/EX-8, task 2.1).

Covers: 200 with __INITIAL_DATA__ {username, permisos, can_write,
facturadores}, can_write gating, admin `*` bypass, HTML redirect for users
without the permission, and facturador DB/fallback behavior.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash

from app.constants.examenes import DEFAULT_EXAMENES, FACTURADORES_FALLBACK
from app.database import Base
from app.utils import examenes_store, users_store
import app.models  # noqa: F401


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect store IO to tmp so tests never touch app/data."""
    monkeypatch.setattr(examenes_store, "DATA_DIR", tmp_path)


def _authenticate(client, permisos: list[str], username: str = "test") -> None:
    """Establece sesión autenticada con los permisos dados."""
    with client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = username
        sess["permisos"] = permisos


def _extract_initial_data(response) -> dict[str, Any]:
    """Extrae y parsea window.__INITIAL_DATA__ desde el HTML del shell."""
    match = re.search(
        r"window\.__INITIAL_DATA__ = (.*?);\s*</script>",
        response.get_data(as_text=True),
        re.DOTALL,
    )
    assert match is not None, "shell HTML must embed __INITIAL_DATA__"
    return json.loads(match.group(1))


def _patch_db_with_facturador(monkeypatch: pytest.MonkeyPatch, users: list[dict]) -> None:
    """Sobrescribe SessionLocal con un engine sembrado (override del autouse)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        for u in users:
            db.add(users_store.User(**u))
        db.commit()
    finally:
        db.close()
    monkeypatch.setattr(users_store, "SessionLocal", Session)


class TestShell200:
    """GET /examenes with the permission → 200 shell + initial data."""

    def test_read_only_shell_initial_data(self, app_client) -> None:
        """Read-only user → 200; can_write False; fallback facturadores."""
        _authenticate(app_client, ["examenes"], username="lectora")

        response = app_client.get("/examenes")

        assert response.status_code == 200
        data = _extract_initial_data(response)
        assert data["username"] == "lectora"
        assert data["permisos"] == ["examenes"]
        assert data["can_write"] is False
        assert data["facturadores"] == FACTURADORES_FALLBACK

    def test_write_shell_can_write_true(self, app_client) -> None:
        """examenes:write user → can_write True (Admin tab + save gating)."""
        _authenticate(app_client, ["examenes:write"])

        response = app_client.get("/examenes")

        assert response.status_code == 200
        data = _extract_initial_data(response)
        assert data["can_write"] is True
        assert data["facturadores"] == FACTURADORES_FALLBACK

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


class TestShellFacturadores:
    """EX-8: DB facturadores win; hardcoded list is only the fallback."""

    def test_db_facturadores_used_when_present(self, app_client, monkeypatch) -> None:
        """DB has facturadores → shell exposes their composed names."""
        _patch_db_with_facturador(
            monkeypatch,
            [
                {
                    "username": "admin",
                    "password_hash": generate_password_hash("admin123"),
                    "rol": "admin",
                    "permisos": ["*"],
                    "primer_nombre": "",
                    "segundo_nombre": "",
                    "apellido_1": "",
                    "apellido_2": "",
                },
                {
                    "username": "angie",
                    "password_hash": generate_password_hash("pass123"),
                    "rol": "facturador",
                    "permisos": ["examenes"],
                    "primer_nombre": "ANGIE ",
                    "segundo_nombre": "",
                    "apellido_1": "ARIAS ",
                    "apellido_2": "",
                },
            ],
        )
        _authenticate(app_client, ["examenes"])

        response = app_client.get("/examenes")

        assert response.status_code == 200
        data = _extract_initial_data(response)
        assert data["facturadores"] == ["ANGIE ARIAS"]

    def test_fallback_when_db_has_no_facturadores(self, app_client) -> None:
        """No facturador users in DB (autouse seed) → FACTURADORES_FALLBACK."""
        _authenticate(app_client, ["examenes"])

        data = _extract_initial_data(app_client.get("/examenes"))

        assert data["facturadores"] == FACTURADORES_FALLBACK

    def test_fallback_when_db_down(self, app_client, monkeypatch) -> None:
        """DB unavailable → shell still renders with fallback (never 500)."""
        def boom():
            raise RuntimeError("db down")

        monkeypatch.setattr(users_store, "SessionLocal", boom)
        _authenticate(app_client, ["examenes"])

        response = app_client.get("/examenes")

        assert response.status_code == 200
        data = _extract_initial_data(response)
        assert data["facturadores"] == FACTURADORES_FALLBACK