"""Tests: "Panel principal" sidebar link visible for ALL authenticated users.

Strict TDD — test written BEFORE implementation.
Phase 3.1: Non-admin users MUST see "Panel principal" in the Jinja2 sidebar.
"""

from __future__ import annotations


class TestSidebarPanelPrincipal:
    """Sidebar renders "Panel principal" link for all authenticated users.

    The /dashboard route already works for all authenticated users — this is
    purely a navigation visibility change in the Jinja2 sidebar.

    We use /control-errores (a Jinja2 route confirmed in test_react_frontend.py)
    to verify sidebar HTML content via base.html.
    """

    PANEL_MARKER = 'display:none;">Panel principal</span>'

    def test_non_admin_sees_panel_principal(self, app_client):
        """Non-admin user with control_urgencias → "Panel principal" link renders.

        The user HAS the permiso for /control-errores, so Flask serves the Jinja2
        template directly (not a redirect). The sidebar from base.html is included.
        """
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "auditor_user"

        resp = app_client.get("/control-errores")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert self.PANEL_MARKER in html, (
            "Expected 'Panel principal' sidebar link for non-admin auth user. "
            "Check base.html else branch — home.home_react must be added before _ep_map."
        )

    def test_admin_still_sees_panel_principal(self, app_client):
        """Admin user with * permiso still sees 'Panel principal' (regression)."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        resp = app_client.get("/control-errores")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert self.PANEL_MARKER in html, (
            "Admin should still see 'Panel principal' sidebar link."
        )

    def test_unauthenticated_does_not_see_panel_principal(self, app_client):
        """Unauthenticated user → no sidebar marker rendered at all."""
        resp = app_client.get("/")
        html = resp.data.decode("utf-8")
        assert self.PANEL_MARKER not in html, (
            "Unauthenticated users should NOT see 'Panel principal' in sidebar."
        )
