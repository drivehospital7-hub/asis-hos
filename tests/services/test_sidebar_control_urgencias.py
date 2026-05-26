"""Integration tests: "Control de Novedades" sidebar link for urgencias users.

Strict TDD: Test written BEFORE the fix. On the buggy code (control_errores_react),
this test will FAIL because nav_items.get('control_errores.control_errores_react')
returns None, so the sidebar link is never rendered.
After the fix (control_errores_page), it will PASS (GREEN).
"""

from __future__ import annotations


class TestSidebarControlUrgencias:
    """Sidebar renders "Control de Novedades" link for users with control_urgencias."""

    SIDEBAR_MARKER = 'display:none;">Control de Novedades</span>'

    def test_control_urgencias_user_sees_novedades_link(self, app_client):
        """User with control_urgencias permiso → sidebar link renders."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias_user"

        resp = app_client.get("/control-errores")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert self.SIDEBAR_MARKER in html, (
            "Expected 'Control de Novedades' sidebar link for control_urgencias user. "
            "Check endpoint_map in base.html line 84."
        )

    def test_non_urgencias_user_does_not_see_novedades_sidebar(self, app_client):
        """User WITHOUT control_urgencias → sidebar link NOT rendered."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odonto_user"

        resp = app_client.get("/control-errores", follow_redirects=True)
        # User is redirected to home (no control_urgencias permiso).
        # Home page (React shell) should NOT contain the sidebar marker.
        html = resp.data.decode("utf-8")
        assert self.SIDEBAR_MARKER not in html, (
            "Sidebar 'Control de Novedades' should NOT appear for users without control_urgencias"
        )

    def test_control_urgencias_write_does_not_duplicate_link(self, app_client):
        """User with both control_urgencias and control_urgencias:write → link appears ONCE only.

        Regression test for the duplication bug: the old template iterated over
        each raw permiso in session_permisos, so 'control_urgencias' and
        'control_urgencias:write' would each render the same nav item.
        """
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias", "control_urgencias:write"]
            sess["username"] = "auditor_user"

        resp = app_client.get("/control-errores")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        count = html.count(self.SIDEBAR_MARKER)
        assert count == 1, (
            f"Expected exactly 1 'Control de Novedades' sidebar link, found {count}. "
            "The template must deduplicate when user has both X and X:write."
        )
