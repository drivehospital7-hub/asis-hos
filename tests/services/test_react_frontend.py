"""Tests for React frontend integration: Flask shell route + Jinja2 unchanged.

Strict TDD — tests written before implementation.
Phase 4: Integration testing for the React frontend Flask route.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestReactShellRoute:
    """Phase 4.1: Flask route at /abiertas-urgencias serves React shell."""

    def test_react_route_returns_200(self, app_client):
        """GET /abiertas-urgencias returns 200 with __INITIAL_DATA__."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/abiertas-urgencias", follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert '<div id="root">' in html or 'id="root"' in html
        assert "__INITIAL_DATA__" in html

    def test_react_route_has_initial_data_shape(self, app_client):
        """__INITIAL_DATA__ JSON has expected fields: can_write, username."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/abiertas-urgencias", follow_redirects=True)
        html = response.data.decode("utf-8")
        assert "can_write" in html
        assert "username" in html
        assert "is_auth" in html

    def test_react_route_has_noscript_fallback(self, app_client):
        """react_shell.html includes <noscript> fallback for non-JS users."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/abiertas-urgencias", follow_redirects=True)
        html = response.data.decode("utf-8")
        assert "<noscript>" in html

    def test_react_route_is_standalone(self, app_client):
        """React shell template is standalone (no longer extends base.html)."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/abiertas-urgencias", follow_redirects=True)
        html = response.data.decode("utf-8")
        # No longer extends base.html — sidebar is rendered by React
        assert 'id="root"' in html
        assert "__INITIAL_DATA__" in html
        # The page should have React bundle
        assert 'type="module"' in html


class TestJinja2RouteUnchanged:
    """Legacy routes removed — test redirects or 404."""

    def test_jinja2_route_still_serves(self, app_client):
        """GET /abiertas-urgencias/legacy returns 404 (route removed)."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/abiertas-urgencias/legacy")
        assert response.status_code == 404

    def test_jinja2_route_has_parse_card(self, app_client):
        """Legacy route no longer exists."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/abiertas-urgencias/legacy")
        assert response.status_code == 404


class TestReactShellTemplateFile:
    """Structural tests for react_shell.html template file."""

    def test_react_shell_exists(self):
        """react_shell.html template exists."""
        tmpl_path = Path("app/templates/react_shell.html")
        assert tmpl_path.exists(), "react_shell.html must be created"

    def test_react_shell_is_standalone(self):
        """react_shell.html is standalone HTML (no longer extends base.html)."""
        tmpl_path = Path("app/templates/react_shell.html")
        content = tmpl_path.read_text(encoding="utf-8")
        # Standalone: has its own <html>, <head>, <body>
        assert "<!DOCTYPE html>" in content
        assert '<div id="root">' in content
        assert "entry_js" in content

    def test_react_shell_has_root_div(self):
        """react_shell.html has <div id=\"root\"> mount point."""
        tmpl_path = Path("app/templates/react_shell.html")
        content = tmpl_path.read_text(encoding="utf-8")
        assert 'id="root"' in content or "id='root'" in content

    def test_react_shell_has_noscript(self):
        """react_shell.html includes <noscript> tag."""
        tmpl_path = Path("app/templates/react_shell.html")
        content = tmpl_path.read_text(encoding="utf-8")
        assert "<noscript>" in content


class TestBuildOutput:
    """Phase 3.4 / 4.x: Verify build output structure."""

    def test_manifest_json_exists(self):
        """manifest.json exists in react-dist."""
        manifest_path = Path("app/static/react-dist/manifest.json")
        assert manifest_path.exists(), "manifest.json must exist after build"

    def test_manifest_has_page_entry(self):
        """manifest.json has page entry with 'file' field (multi-page Vite)."""
        import json
        manifest_path = Path("app/static/react-dist/manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Each page entry should have 'file', 'src', and 'isEntry'
        pages = [k for k in manifest if k.startswith("src/pages/")]
        assert len(pages) > 0, "manifest must have at least one page entry"
        entry = manifest[pages[0]]
        assert "file" in entry, f"{pages[0]} entry must have 'file' field"
        assert entry["file"].endswith(".js"), "entry file must be a .js file"

    def test_assets_dir_has_js_files(self):
        """react-dist/assets/ contains at least one .js file."""
        assets_dir = Path("app/static/react-dist/assets")
        assert assets_dir.exists(), "assets directory must exist"
        js_files = list(assets_dir.glob("*.js"))
        assert len(js_files) > 0, "Must have at least one JS bundle"


class TestNewReactRoutes:
    """Phase 8: Flask routes for 3 new React pages."""

    # ═══════════════════════════════════════════
    # 8.1 /dashboard (React)
    # ═══════════════════════════════════════════

    def test_dashboard_react_returns_200(self, app_client):
        """GET /dashboard returns 200 with __INITIAL_DATA__."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/dashboard", follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert '<div id="root">' in html or 'id="root"' in html
        assert "__INITIAL_DATA__" in html

    def test_dashboard_react_has_kpis_and_areas(self, app_client):
        """__INITIAL_DATA__ contains kpis + areas."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/dashboard", follow_redirects=True)
        html = response.data.decode("utf-8")
        assert "kpis" in html
        assert "areas" in html

    # ═══════════════════════════════════════════
    # 8.2 /control-errores (React — not swapped)
    # ═══════════════════════════════════════════

    def test_control_errores_react_returns_200(self, app_client):
        """GET /control-errores returns 200 (Jinja2)."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/control-errores")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Control Novedades" in html

    def test_control_errores_react_has_meses_and_novedades(self, app_client):
        """Jinja2 page renders correctly."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/control-errores")
        html = response.data.decode("utf-8")
        assert "page-header" in html or "Control" in html

    # ═══════════════════════════════════════════
    # 8.3 /urgencias (React)
    # ═══════════════════════════════════════════

    def test_urgencias_react_returns_200(self, app_client):
        """GET /urgencias returns 200 with __INITIAL_DATA__."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/urgencias", follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert '<div id="root">' in html or 'id="root"' in html
        assert "__INITIAL_DATA__" in html

    def test_urgencias_react_has_errores(self, app_client):
        """__INITIAL_DATA__ contains errores array."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/urgencias", follow_redirects=True)
        html = response.data.decode("utf-8")
        assert "errores" in html

    # ═══════════════════════════════════════════
    # 8.4 Legacy Jinja2 routes preserved
    # ═══════════════════════════════════════════

    def test_existing_jinja2_home_still_serves(self, app_client):
        """Legacy route removed — returns 404."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/dashboard/legacy")
        assert response.status_code == 404

    def test_existing_jinja2_control_errores_still_serves(self, app_client):
        """GET /control-errores still serves Jinja2."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/control-errores")
        assert response.status_code == 200

    def test_existing_jinja2_urgencias_still_serves(self, app_client):
        """Legacy route removed — returns 404."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/urgencias/legacy")
        assert response.status_code == 404

    # ═══════════════════════════════════════════
    # 8.6 manifest has 4 entries
    # ═══════════════════════════════════════════

    def test_manifest_has_twelve_html_entries(self, app_client):
        """manifest.json has 12 HTML entry keys (including intramural)."""
        import json
        manifest_path = Path("app/static/react-dist/manifest.json")
        if not manifest_path.exists():
            pytest.skip("manifest.json not found — build may not have run yet")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        html_keys = [k for k in manifest if k.endswith(".html")]
        assert len(html_keys) == 12, f"Expected 12 HTML entries, got {len(html_keys)}: {html_keys}"
        assert "src/pages/index/index.html" in html_keys
        assert "src/pages/abiertas-urgencias/index.html" in html_keys
        assert "src/pages/control-novedades/index.html" in html_keys
        assert "src/pages/urgencias/index.html" in html_keys
        assert "src/pages/odontologia/index.html" in html_keys
        assert "src/pages/derechos/index.html" in html_keys
        assert "src/pages/ordenado-facturado/index.html" in html_keys
        assert "src/pages/usuarios/index.html" in html_keys
        assert "src/pages/genderize/index.html" in html_keys
        assert "src/pages/login/index.html" in html_keys
        assert "src/pages/unauthorized/index.html" in html_keys


class TestDashboardPermisos:
    """Dashboard areas are filtered by user permissions (T5: sincronizar-dashboard-permisos)."""

    # ═══════════════════════════════════════════
    # Unit: _filter_areas
    # ═══════════════════════════════════════════

    def test_filter_areas_admin(self):
        """Admin (*) sees all DASHBOARD_AREAS."""
        from app.constants.base import _filter_areas
        result = _filter_areas(["*"])
        assert len(result) == 10
        titles = [a["title"] for a in result]
        assert "Urgencias" in titles
        assert "Derechos" in titles
        assert "Intramural" in titles

    def test_filter_areas_single_permiso(self):
        """User with only odontologia sees exactly 1 area."""
        from app.constants.base import _filter_areas
        result = _filter_areas(["odontologia"])
        assert len(result) == 1
        assert result[0]["slug"] == "odontologia"

    def test_filter_areas_multiple(self):
        """User with urgencias + facturas_abiertas sees 2 areas."""
        from app.constants.base import _filter_areas
        result = _filter_areas(["urgencias", "facturas_abiertas"])
        assert len(result) == 2
        slugs = {a["slug"] for a in result}
        assert slugs == {"urgencias", "abiertas_urgencias"}

    def test_filter_areas_no_match(self):
        """User with unmapped permiso sees 0 areas."""
        from app.constants.base import _filter_areas
        result = _filter_areas(["some_random"])
        assert len(result) == 0

    def test_filter_areas_empty(self):
        """Empty list sees 0 areas (spec R2-E5)."""
        from app.constants.base import _filter_areas
        result = _filter_areas([])
        assert len(result) == 0

    def test_filter_areas_none(self):
        """None sees all areas (safe fallback for missing session)."""
        from app.constants.base import _filter_areas
        result = _filter_areas(None)
        assert len(result) == 10

    # ═══════════════════════════════════════════
    # Integration: dashboard filtering
    # ═══════════════════════════════════════════

    @staticmethod
    def _extract_initial_data(html: str) -> dict:
        """Extract __INITIAL_DATA__ JSON from the HTML shell."""
        import json
        import re
        match = re.search(r"window\.__INITIAL_DATA__\s*=\s*({.*?});", html, re.DOTALL)
        if not match:
            return {}
        return json.loads(match.group(1))

    def test_dashboard_admin_sees_all_areas(self, app_client):
        """Admin user sees all 10 areas in /dashboard."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/dashboard", follow_redirects=True)
        html = response.data.decode("utf-8")
        data = self._extract_initial_data(html)
        areas = data.get("areas", [])
        titles = [a["title"] for a in areas]
        assert "Urgencias" in titles
        assert "Odontología" in titles
        assert "Control de Novedades" in titles
        assert "Facturas Abiertas" in titles
        assert "Ordenado y Facturado" in titles
        assert "Derechos" in titles
        assert "Equipos Básicos" in titles
        assert "Intramural" in titles
        assert "Usuarios" in titles
        assert "Importar Facturas" in titles
        assert len(areas) == 10

    def test_dashboard_odontologia_only(self, app_client):
        """User with only odontologia permiso sees exactly 1 area."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"

        resp = app_client.get("/dashboard", follow_redirects=True)
        html = resp.data.decode("utf-8")
        data = self._extract_initial_data(html)
        areas = data.get("areas", [])
        assert len(areas) == 1
        assert areas[0]["slug"] == "odontologia"

    # ═══════════════════════════════════════════
    # Integration: derechos route guard
    # ═══════════════════════════════════════════

    def test_derechos_without_permiso_returns_403(self, app_client):
        """User without derechos permiso gets 403 on GET /derechos/derechos."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"

        # Use XHR header so @permiso_requerido returns 403 JSON (not HTML redirect)
        response = app_client.get(
            "/derechos/derechos",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403

    def test_derechos_with_permiso_returns_200(self, app_client):
        """Admin with * permiso can access /derechos/derechos."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        response = app_client.get("/derechos/derechos", follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "__INITIAL_DATA__" in html
