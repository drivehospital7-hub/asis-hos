"""RED integration tests for GET /api/import/cache-list & cache-alerts (PR1)."""
from unittest.mock import patch


def _admin_session(app_client):
    with app_client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = "admin"
        sess["permisos"] = ["*"]


def _non_admin_session(app_client):
    with app_client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = "user"
        sess["permisos"] = ["urgencias"]


class TestCacheListGuard:
    def test_admin_200_envelope(self, app_client):
        _admin_session(app_client)
        fake_cache = {"angela": {"gender": "female", "probability": 0.99, "count": 10}}
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            resp = app_client.get(
                "/api/import/cache-list",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert data["errors"] == []
        assert data["status"] != "warning"

    def test_non_admin_403(self, app_client):
        _non_admin_session(app_client)
        resp = app_client.get(
            "/api/import/cache-list",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert data["data"] == {}
        assert len(data["errors"]) > 0

    def test_invalid_gender_400(self, app_client):
        _admin_session(app_client)
        fake_cache = {"angela": {"gender": "female", "probability": 0.99, "count": 10}}
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            resp = app_client.get(
                "/api/import/cache-list?gender=X",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"
        assert data["status"] != "warning"
        assert any("genero invalido" in e.lower() for e in data["errors"])

    def test_unauthenticated_401(self, app_client):
        resp = app_client.get(
            "/api/import/cache-list",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        # before_request returns 401 for unauthenticated JSON request
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "error"


class TestCacheAlertsGuard:
    def test_admin_200_envelope(self, app_client):
        _admin_session(app_client)
        import json as _json

        raw = {"angela": {"gender": "female", "probability": 0.9, "count": 1}}
        with patch("app.services.genderize_service.CACHE_FILE") as mf:
            mf.read_text.return_value = _json.dumps(raw)
            resp = app_client.get(
                "/api/import/cache-alerts",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "collisions" in data["data"]
        assert data["errors"] == []

    def test_non_admin_403(self, app_client):
        _non_admin_session(app_client)
        resp = app_client.get(
            "/api/import/cache-alerts",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "error"

    def test_never_warning(self, app_client):
        _admin_session(app_client)
        import json as _json

        raw = {"angela": {"gender": "female", "probability": 0.9, "count": 1}}
        with patch("app.services.genderize_service.CACHE_FILE") as mf:
            mf.read_text.return_value = _json.dumps(raw)
            resp = app_client.get(
                "/api/import/cache-alerts",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        assert resp.get_json()["status"] != "warning"
