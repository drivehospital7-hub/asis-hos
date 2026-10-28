"""La columna flujo de /api/notas-hoja es solo-lectura y refleja nota_flujo."""

from __future__ import annotations


class TestNotasHojaFlujo:
    def test_list_incluye_flujo(self, app_client):
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        resp = app_client.get("/api/notas-hoja")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["data"]) > 0
        for item in data["data"]:
            assert item["flujo"] in ("capita", "evento"), item

    def test_capita_en_nombre_da_capita(self, app_client):
        import json
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        resp = app_client.post(
            "/api/notas-hoja",
            data=json.dumps({"nota": "PRUEBA CAPITA T1"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        nid = resp.get_json()["data"]["id"]
        try:
            resp = app_client.get("/api/notas-hoja")
            by_nota = {x["nota"]: x["flujo"] for x in resp.get_json()["data"]}
            assert by_nota["PRUEBA CAPITA T1"] == "capita"
            assert by_nota.get("EMSSANAR SUBSIDIADO", "evento") == "evento"
        finally:
            app_client.delete(f"/api/notas-hoja/{nid}")

    def test_flujo_coincide_con_helper(self, app_client):
        from app.constants.headers import nota_flujo
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        resp = app_client.get("/api/notas-hoja")
        for item in resp.get_json()["data"]:
            assert item["flujo"] == nota_flujo(item["nota"])
