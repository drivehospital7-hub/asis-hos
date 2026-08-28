"""UP-3/UP-4 visibility tests: sidebar + dashboard per permiso (task 5.3).

Covers:
- Sidebar: `ALL_NAV` exposes the "Exámenes" entry gated by `permiso:
  "examenes"` (structural read of the React source — the sidebar is TSX and
  has no backend route to exercise).
- Dashboard: `_filter_areas` + the /dashboard route show the card only for
  `examenes` / `examenes:write` users; unrelated permisos (odontologia) see
  neither sidebar entry nor card.
- Usuarios UI wiring (UP-1/UP-2): the permission checkboxes and mutual
  exclusion pairs exist in the React source (structural read).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.constants.base import _filter_areas

FRONTEND_ROOT = Path("frontend/src")


def _read_frontend(relative: str) -> str:
    path = FRONTEND_ROOT / relative
    assert path.exists(), f"frontend file missing: {path}"
    return path.read_text(encoding="utf-8")


def _extract_initial_data(html: str) -> dict:
    """Parse window.__INITIAL_DATA__ JSON (tojson escapes non-ASCII)."""
    match = re.search(r"window\.__INITIAL_DATA__\s*=\s*({.*?});", html, re.DOTALL)
    if not match:
        return {}
    return json.loads(match.group(1))


def _authenticate(client, permisos: list[str], username: str = "test") -> None:
    with client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = username
        sess["permisos"] = permisos


class TestSidebarVisibility:
    """UP-3: ALL_NAV entry `{label:"Exámenes", href:"/examenes", permiso:"examenes"}`."""

    def test_all_nav_has_examenes_entry(self) -> None:
        sidebar = _read_frontend("components/app-sidebar.tsx")
        assert 'href: "/examenes"' in sidebar
        assert 'permiso: "examenes"' in sidebar
        assert 'label: "Exámenes"' in sidebar

    def test_sidebar_entry_is_permission_gated(self) -> None:
        """The entry sits inside ALL_NAV (filtered by expandedPermisos), so a
        user without `examenes`/`examenes:write` never sees it (UP-3 hidden)."""
        sidebar = _read_frontend("components/app-sidebar.tsx")
        assert "ALL_NAV" in sidebar
        assert 'permiso: "examenes"' in sidebar


class TestDashboardVisibility:
    """UP-4: DASHBOARD_AREAS card + _filter_areas per permiso."""

    def test_filter_areas_examenes_read(self) -> None:
        result = _filter_areas(["examenes"])
        assert [a["href"] for a in result] == ["/examenes"]
        assert result[0]["title"] == "Exámenes"

    def test_filter_areas_examenes_write_expands_to_card(self) -> None:
        result = _filter_areas(["examenes:write"])
        assert [a["href"] for a in result] == ["/examenes"]

    def test_filter_areas_unrelated_permiso_hides_card(self) -> None:
        result = _filter_areas(["odontologia"])
        assert all(a["href"] != "/examenes" for a in result)

    def test_dashboard_route_examenes_sees_card(self, app_client) -> None:
        _authenticate(app_client, ["examenes"])
        resp = app_client.get("/dashboard", follow_redirects=True)
        data = _extract_initial_data(resp.get_data(as_text=True))
        areas = data.get("areas", [])
        titles = [a["title"] for a in areas]
        assert "Exámenes" in titles
        assert any(a["href"] == "/examenes" for a in areas)

    def test_dashboard_route_odontologia_only_hides_card(self, app_client) -> None:
        _authenticate(app_client, ["odontologia"])
        resp = app_client.get("/dashboard", follow_redirects=True)
        data = _extract_initial_data(resp.get_data(as_text=True))
        titles = [a["title"] for a in data.get("areas", [])]
        assert "Exámenes" not in titles


class TestUsuariosUiWiring:
    """UP-1/UP-2: usuarios page lists the pair + mutual exclusion (frontend)."""

    def test_all_permisos_lists_examenes_pair(self) -> None:
        usuarios = _read_frontend("pages/usuarios/page.tsx")
        assert 'value: "examenes"' in usuarios
        assert 'value: "examenes:write"' in usuarios
        assert "Exámenes (lectura)" in usuarios
        assert "Exámenes (modificar)" in usuarios

    def test_permiso_pairs_include_examenes(self) -> None:
        usuarios = _read_frontend("pages/usuarios/page.tsx")
        assert '"examenes": "examenes:write"' in usuarios
        assert '"examenes:write": "examenes"' in usuarios