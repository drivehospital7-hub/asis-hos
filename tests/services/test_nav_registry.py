"""Tests: registro canonico de navegacion + GET /api/nav + refactor base.html.

Task 2 de odd/tasks/sidebar-unico.md. Contrato:

- Toda key del registro ⊆ ALLOWED_PERMISOS (salvo ``*`` y ``None``).
- Todo endpoint del registro existe en ``app.url_map`` y viceversa no aplica
  (el registro cubre la union de ambos sidebars + huerfanos, no todas las rutas).
- ``GET /api/nav``: anonimo → ``[]``; 1 permiso → su modulo + home;
  admin → todos. Envelope ``{status, data.modulos, errors}``.
- ``base.html`` renderiza sin ``KeyError`` con usuario sample (labels visibles
  segun permisos, sin listas hardcodeadas ``nav_items``/``_ep_map``).
"""

from __future__ import annotations

from pathlib import Path


class TestNavRegistry:
    def test_keys_subset_allowed_permisos(self):
        from app.constants.base import ALLOWED_PERMISOS
        from app.constants.navigation import NAV_MODULES

        for m in NAV_MODULES:
            key = m["key"]
            assert key is None or key == "*" or key in ALLOWED_PERMISOS, (
                f"key {key!r} de {m['label']!r} no esta en ALLOWED_PERMISOS"
            )

    def test_schema_completo(self):
        from app.constants.navigation import NAV_MODULES

        for m in NAV_MODULES:
            assert set(m) == {"key", "label", "href", "icon", "endpoint"}, m
            assert m["label"] and m["href"].startswith("/") and m["icon"]
            assert "." in m["endpoint"], m

    def test_endpoints_existen(self, app_client):
        from app.constants.navigation import NAV_MODULES

        app = app_client.application
        registrados = {r.endpoint for r in app.url_map.iter_rules()}
        for m in NAV_MODULES:
            assert m["endpoint"] in registrados, (
                f"endpoint {m['endpoint']!r} ({m['label']}) no existe en url_map"
            )

    def test_expandir_write_a_base(self):
        from app.constants.navigation import expandir

        assert expandir(["control_urgencias:write"]) == {
            "control_urgencias:write",
            "control_urgencias",
        }
        assert expandir([]) == set()
        assert expandir(None) == set()

    def test_modulos_para_anonimo_vacio(self):
        from app.constants.navigation import modulos_para

        assert modulos_para([], autenticado=False) == []
        assert modulos_para(None, autenticado=False) == []

    def test_modulos_para_sin_permisos_autenticado_solo_home(self):
        from app.constants.navigation import modulos_para

        mods = modulos_para([], autenticado=True)
        assert [m["label"] for m in mods] == ["Panel principal"]


class TestNavApi:
    def _get(self, app_client, permisos=None, username=None, auth=True):
        with app_client.session_transaction() as sess:
            sess.clear()
            if auth:
                sess["ce_authenticated"] = True
                sess["username"] = username or "user_test"
                sess["permisos"] = permisos or []
        return app_client.get("/api/nav")

    def test_anonimo_lista_vacia(self, fresh_client):
        resp = fresh_client.get("/api/nav")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "success"
        assert body["data"] == {"modulos": []}
        assert body["errors"] == []

    def test_un_permiso_solo_su_modulo_mas_home(self, app_client):
        resp = self._get(app_client, permisos=["control_urgencias"])
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "success" and body["errors"] == []
        labels = [m["label"] for m in body["data"]["modulos"]]
        assert labels == ["Panel principal", "Control de Novedades"]
        for m in body["data"]["modulos"]:
            assert set(m) == {"label", "href", "icon"}

    def test_write_expande_a_base(self, app_client):
        resp = self._get(app_client, permisos=["examenes:write"])
        labels = [m["label"] for m in resp.get_json()["data"]["modulos"]]
        assert labels == ["Panel principal", "Exámenes"]

    def test_admin_ve_todos(self, app_client):
        from app.constants.navigation import NAV_MODULES

        resp = self._get(app_client, permisos=["*"], username="admin")
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["modulos"]) == len(NAV_MODULES)


class TestBaseSidebar:
    PANEL_MARKER = 'display:none;">Panel principal</span>'

    def _login(self, app_client, permisos, username="auditor_user"):
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = permisos
            sess["username"] = username

    def test_render_sin_keyerror_usuario_sample(self, app_client):
        self._login(app_client, ["control_urgencias"])
        resp = app_client.get("/control-novedades")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert self.PANEL_MARKER in html
        assert "Control de Novedades" in html
        # Sin listas hardcodeadas en el HTML renderizado ni rastro de ellas
        assert "_ep_map" not in html and "nav_items" not in html

    def test_admin_ve_huerfanos(self, app_client):
        self._login(app_client, ["*"], username="admin")
        resp = app_client.get("/control-novedades")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        for label in ("Admin Reglas", "Importar Facturas", "Catálogos", "Usuarios"):
            assert label in html, f"admin deberia ver {label!r} en sidebar"

    def test_no_hardcode_en_template(self):
        src = Path("app/templates/base.html").read_text(encoding="utf-8")
        assert "nav_items" not in src and "_ep_map" not in src
        assert "for item in nav_modules" in src
