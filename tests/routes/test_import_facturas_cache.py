"""RED integration tests for GET /api/import/cache-list & cache-alerts (PR1) + cache-corregir R7/R8 (PR3)."""
import json
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


# ── R7/R8: POST /api/import/cache-corregir — guards + edit persistence (PR3) ──


class TestCacheCorregirGuards:
    def test_non_admin_403_corregir(self, app_client):
        _non_admin_session(app_client)
        resp = app_client.post(
            "/api/import/cache-corregir",
            json={"nombre_normalizado": "angela", "genero": "M"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "error"
        assert resp.get_json()["status"] != "warning"

    def test_unauth_401_corregir(self, app_client):
        resp = app_client.post(
            "/api/import/cache-corregir",
            json={"nombre_normalizado": "angela", "genero": "M"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "error"

    def test_invalid_gender_400(self, app_client, tmp_path):
        _admin_session(app_client)
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps({"angela": {"gender": "female", "probability": 0.99, "count": 1}}), encoding="utf-8")
        with patch("app.services.genderize_service.CACHE_FILE", cache_file):
            resp = app_client.post(
                "/api/import/cache-corregir",
                json={"nombre_normalizado": "angela", "genero": "X"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "error"
        assert resp.get_json()["status"] != "warning"

    def test_not_found_404(self, app_client, tmp_path):
        _admin_session(app_client)
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps({"angela": {"gender": "female", "probability": 0.99, "count": 1}}), encoding="utf-8")
        with patch("app.services.genderize_service.CACHE_FILE", cache_file):
            resp = app_client.post(
                "/api/import/cache-corregir",
                json={"nombre_normalizado": "noexiste", "genero": "M"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"


class TestCacheCorregirEditPersistence:
    """R7: edit angela female->M persists; last-wins no corrupt; banner envelope."""

    def test_edit_persists_angela_female_to_M(self, app_client, tmp_path):
        _admin_session(app_client)
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps({"angela": {"gender": "female", "probability": 0.99, "count": 10}}), encoding="utf-8")
        with patch("app.services.genderize_service.CACHE_FILE", cache_file):
            resp = app_client.post(
                "/api/import/cache-corregir",
                json={"nombre_normalizado": "angela", "genero": "M"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["status"] == "success"
            assert resp.get_json()["status"] != "warning"
            # next GET reflects M/male
            resp2 = app_client.get("/api/import/cache-list?search=angela", headers={"X-Requested-With": "XMLHttpRequest"})
            assert resp2.status_code == 200
            data = resp2.get_json()
            assert data["data"]["total"] == 1
            assert data["data"]["items"][0]["gender"] == "male"
            assert data["data"]["items"][0]["gender_short"] == "M"
            # file still valid JSON, no corrupt
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
            assert raw["angela"]["gender"] == "male"

    def test_last_wins_no_corrupt(self, app_client, tmp_path):
        _admin_session(app_client)
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps({"angela": {"gender": "female", "probability": 0.99, "count": 10}}), encoding="utf-8")
        with patch("app.services.genderize_service.CACHE_FILE", cache_file):
            app_client.post("/api/import/cache-corregir", json={"nombre_normalizado": "angela", "genero": "F"}, headers={"X-Requested-With": "XMLHttpRequest"})
            app_client.post("/api/import/cache-corregir", json={"nombre_normalizado": "angela", "genero": "M"}, headers={"X-Requested-With": "XMLHttpRequest"})
            resp = app_client.get("/api/import/cache-list?search=angela", headers={"X-Requested-With": "XMLHttpRequest"})
            assert resp.get_json()["data"]["items"][0]["gender"] == "male"
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
            assert raw["angela"]["gender"] == "male"

    def test_edit_with_short_codes_FMLU_and_refetch(self, app_client, tmp_path):
        _admin_session(app_client)
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps({"jose": {"gender": "male", "probability": 0.9, "count": 5}}), encoding="utf-8")
        with patch("app.services.genderize_service.CACHE_FILE", cache_file):
            for code, expected in [("F", "female"), ("L", "lastname"), ("U", "undefined")]:
                resp = app_client.post("/api/import/cache-corregir", json={"nombre_normalizado": "jose", "genero": code}, headers={"X-Requested-With": "XMLHttpRequest"})
                assert resp.status_code == 200
                assert json.loads(cache_file.read_text(encoding="utf-8"))["jose"]["gender"] == expected
