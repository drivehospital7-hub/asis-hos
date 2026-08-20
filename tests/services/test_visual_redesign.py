"""Tests for visual redesign: templates, layout, breadcrumbs, sidebar, mock data.

Strict TDD — tests written before implementation.
CSS class assertions are NEVER valid per strict-tdd.md rules.
We test STRUCTURE and CONTENT, not visual style.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# =============================================================================
# Phase 0 — CSS extraction (structural tests)
# =============================================================================


class TestCSSExtraction:
    """Verify legacy CSS files exist after extraction."""

    def test_legacy_control_errores_css_exists(self):
        """Phase 0.1: legacy/control_errores.css extracted from inline <style>."""
        css_path = Path("app/static/css/legacy/control_errores.css")
        assert css_path.exists(), "control_errores.css must be extracted"
        content = css_path.read_text(encoding="utf-8")
        # Must contain at least the key CSS rules from the original inline
        assert ".page-header" in content
        assert ".stats-grid" in content
        assert ".table" in content
        assert ".badge--pending" in content or ".badge" in content
        assert ".carga-modal" in content


# =============================================================================
# Phase 1 — Foundation: main.css, CDN, sidebar, breadcrumbs
# =============================================================================


class TestMainCSS:
    """Phase 1.1: main.css with oklch tokens."""

    def test_main_css_exists(self):
        """main.css must exist with @theme or :root tokens."""
        css_path = Path("app/static/css/main.css")
        assert css_path.exists(), "main.css must be created"
        content = css_path.read_text(encoding="utf-8")
        # Must contain oklch color tokens
        assert "oklch" in content or "@theme" in content, "Must define oklch color tokens"
        # Must define primary color
        assert "primary" in content, "Must define --primary token"
        # Must define semantic badge colors
        assert "danger" in content.lower() or "warning" in content.lower(), "Must define semantic colors"


class TestMockData:
    """Phase 1.7: mock_data.py for development."""

    def test_mock_data_importable(self):
        """get_mock_data must be importable."""
        from app.services.mock_data import get_mock_data  # noqa: F811
        assert callable(get_mock_data)

    def test_mock_data_returns_dict(self):
        """get_mock_data returns a dict."""
        from app.services.mock_data import get_mock_data
        result = get_mock_data("home")
        assert isinstance(result, dict)

    def test_mock_data_home_has_kpis(self):
        """home mock data includes KPIs dict with total, pendientes, resueltas."""
        from app.services.mock_data import get_mock_data
        result = get_mock_data("home")
        assert "kpis" in result
        kpis = result["kpis"]
        assert isinstance(kpis, dict)
        assert "total" in kpis
        assert "pendientes" in kpis
        assert "resueltas" in kpis

    def test_mock_data_control_errores_has_errors(self):
        """control_errores mock data includes errores list."""
        from app.services.mock_data import get_mock_data
        result = get_mock_data("control_errores")
        assert "errores" in result
        assert isinstance(result["errores"], list)

    def test_mock_data_control_errores_error_has_fields(self):
        """Each error has required fields: id, tipo_error, estado, responsable, observacion."""
        from app.services.mock_data import get_mock_data
        result = get_mock_data("control_errores")
        errores = result["errores"]
        assert len(errores) > 0, "Must have at least one mock error"
        required_fields = {"id", "tipo_error", "estado", "responsable", "observacion", "factura"}
        for error in errores:
            missing = required_fields - set(error.keys())
            assert not missing, f"Mock error missing fields: {missing}"

    def test_mock_data_abiertas_has_schedule(self):
        """abiertas_urgencias mock data includes schedule."""
        from app.services.mock_data import get_mock_data
        result = get_mock_data("abiertas_urgencias")
        assert "schedule" in result or "turnos" in result or "horario" in result


# =============================================================================
# Phase 1 — Integration tests (Flask test client)
# =============================================================================


class TestTemplateRendering:
    """Verify templates render without errors and have expected structure."""

    def test_home_page_renders_unauthenticated(self, app_client):
        """Dashboard returns 401 when not authenticated (middleware)."""
        response = app_client.get("/dashboard")
        assert response.status_code == 401
        html = response.data.decode("utf-8")
        # Must render unauthorized page
        assert "Acceso" in html or "Restringido" in html

    def test_home_page_renders_with_auth(self, app_client):
        """Dashboard page renders with 200 when authenticated."""
        # First login to get session
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/dashboard")
        assert response.status_code in (200, 302)  # 302 for redirect if already auth'd
        if response.status_code == 200:
            html = response.data.decode("utf-8")
            # React dashboard: check for React mount point
            assert 'id="root"' in html or "__INITIAL_DATA__" in html

    def test_login_page_renders(self, app_client):
        """Login page renders with 200."""
        response = app_client.get("/auth/login")
        assert response.status_code == 200
        html = response.data.decode("utf-8")

        # Must render the React mount point
        assert 'id="root"' in html or "__INITIAL_DATA__" in html

    def test_unauthorized_page_renders(self, app_client):
        """Unauthorized page renders with 401 and has content."""
        response = app_client.get("/some-restricted-page")
        # Should either redirect to login or return unauthorized
        assert response.status_code in (302, 401)
        if response.status_code == 401:
            html = response.data.decode("utf-8")
            assert "Acceso" in html or "Restringido" in html or "Inicio" in html

    def test_base_template_has_lucide_scripts(self):
        """base.html includes Lucide CDN."""
        base_path = Path("app/templates/base.html")
        content = base_path.read_text(encoding="utf-8")
        assert "lucide" in content.lower(), "Base template must include Lucide CDN"

    def test_base_template_has_tailwind_cdn(self):
        """base.html includes Tailwind CDN."""
        base_path = Path("app/templates/base.html")
        content = base_path.read_text(encoding="utf-8")
        assert "tailwind" in content.lower(), "Base template must include Tailwind CDN"

    def test_base_template_has_google_fonts(self):
        """base.html includes Google Fonts (Sora + Manrope)."""
        base_path = Path("app/templates/base.html")
        content = base_path.read_text(encoding="utf-8")
        assert "fonts.googleapis.com" in content, "Base template must include Google Fonts"
        assert "Sora" in content, "Base template must include Sora font"
        assert "Manrope" in content, "Base template must include Manrope font"

    def test_base_template_has_sidebar(self):
        """base.html has sidebar structure."""
        base_path = Path("app/templates/base.html")
        content = base_path.read_text(encoding="utf-8")
        assert "sidebar" in content.lower() or "Sidebar" in content, "Base template must have sidebar"
        assert "toggleSidebar" in content or "sidebar-collapsed" in content, "Sidebar must have toggle mechanism"

    def test_base_template_has_breadcrumbs_block(self):
        """base.html has breadcrumbs section."""
        base_path = Path("app/templates/base.html")
        content = base_path.read_text(encoding="utf-8")
        assert "breadcrumb" in content.lower(), "Base template must have breadcrumbs"

    def test_base_template_has_header_with_title(self):
        """base.html has header with hospital title."""
        base_path = Path("app/templates/base.html")
        content = base_path.read_text(encoding="utf-8")
        assert "Hospital" in content or "HOR" in content, "Header must show hospital name"


# =============================================================================
# Phase 3 — Control Errores
# =============================================================================


class TestControlErroresTemplate:
    """Phase 3: Control Errores template structure."""

    def test_control_errores_extends_base(self):
        """control_errores.html extends base.html."""
        ctrl_path = Path("app/templates/control_errores.html")
        content = ctrl_path.read_text(encoding="utf-8")
        assert 'extends "base.html"' in content or "extends 'base.html'" in content

    def test_control_errores_has_table(self):
        """control_errores.html has the errors table."""
        ctrl_path = Path("app/templates/control_errores.html")
        content = ctrl_path.read_text(encoding="utf-8")
        assert "erroresTable" in content or "table" in content

    def test_control_errores_has_stats_cards(self):
        """control_errores.html has stat indicators."""
        ctrl_path = Path("app/templates/control_errores.html")
        content = ctrl_path.read_text(encoding="utf-8")
        assert "stat" in content.lower() or "Total" in content

    def test_control_errores_facturador_editor_hoists_size_before_left(self):
        """R12/R13: facturador editor hoists width/height locals BEFORE left is assigned.

        The editor must keep its exact size (Math.max(260, rect.width) x
        Math.max(90, rect.height)) while opening to the LEFT of the trigger
        button. Width/height are hoisted into locals so `left` can reuse
        `editorWidth` for the mirror position.
        """
        ctrl_path = Path("app/templates/control_errores.html")
        content = ctrl_path.read_text(encoding="utf-8")
        assert "const editorWidth = Math.max(260, rect.width);" in content
        assert "const editorHeight = Math.max(90, rect.height);" in content
        assert "editor.style.width = editorWidth + 'px';" in content
        assert "editor.style.height = editorHeight + 'px';" in content
        assert "const editorLeft = btnRect.left - editorWidth - 8;" in content

    def test_control_errores_facturador_editor_left_formula_with_fallback(self):
        """R12 + fallback: editor opens LEFT with 8px gap, falls back RIGHT near left edge.

        The old unconditional right-side line (``btnRect.left + btnRect.width + 8 + 'px'``)
        must be gone, replaced by the mirror-with-fallback ternary that keeps the
        editor fully on screen when the button sits near the left viewport edge.
        """
        ctrl_path = Path("app/templates/control_errores.html")
        content = ctrl_path.read_text(encoding="utf-8")
        assert "editor.style.left = (editorLeft < 8 ? btnRect.left + btnRect.width + 8 : editorLeft) + 'px';" in content
        assert "editor.style.left = btnRect.left + btnRect.width + 8 + 'px';" not in content

    def test_control_errores_search_placeholder_excludes_responsable(self):
        """Search placeholder says descripcion or ID, not responsable."""
        ctrl_path = Path("app/templates/control_errores.html")
        content = ctrl_path.read_text(encoding="utf-8")
        assert "Buscar por descripción o ID..." in content
        assert "Buscar por descripción, responsable o ID..." not in content

    def test_control_errores_search_query_persisted_and_applied(self):
        """Search query is persisted and re-applied by renderFilteredByMonth.

        The polling re-render (renderFilteredByMonth) must keep the search text
        the user typed, so the filter is not lost between polls.
        """
        ctrl_path = Path("app/templates/control_errores.html")
        content = ctrl_path.read_text(encoding="utf-8")
        assert "let searchQuery = '';" in content
        assert "searchQuery = query;" in content
        assert "renderFilteredByMonth" in content
        assert "searchQuery" in content
        assert "includes(searchQuery)" in content


# =============================================================================
# Phase 5 — Remaining templates
# =============================================================================


class TestRemainingTemplates:
    """Phase 5: remaining templates inherit base."""

    @pytest.mark.parametrize("template_name", [
        "unauthorized.html",
    ])
    def test_template_extends_base(self, template_name):
        """Template extends base.html."""
        tmpl_path = Path(f"app/templates/{template_name}")
        content = tmpl_path.read_text(encoding="utf-8")
        assert 'extends "base.html"' in content or "extends 'base.html'" in content

    def test_unauthorized_has_icon_and_message(self):
        """unauthorized.html has access denied message."""
        tmpl_path = Path("app/templates/unauthorized.html")
        content = tmpl_path.read_text(encoding="utf-8")
        assert "Acceso" in content or "Restringido" in content or "ShieldAlert" in content


# =============================================================================
# Phase 6 — Cleanup: legacy files removed
# =============================================================================


class TestCleanup:
    """Phase 6: base.css and components.css removed."""

    def test_base_css_removed(self):
        """base.css must be deleted (replaced by Tailwind)."""
        assert not Path("app/static/css/base.css").exists(), "base.css must be deleted"

    def test_components_css_removed(self):
        """components.css must be deleted (replaced by Tailwind utilities)."""
        assert not Path("app/static/css/components.css").exists(), "components.css must be deleted"


