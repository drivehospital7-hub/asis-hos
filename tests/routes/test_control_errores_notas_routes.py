"""T3: rutas de notas — lectura crea/borra notas propias; común exige write (S1/S6/S9)."""
from unittest.mock import patch

import app.routes.control_errores as routes


def _login(client, permisos, username="lector1"):
    with client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = username
        sess["permisos"] = permisos


def test_lectura_post_comun_requiere_write(app_client):
    """Lectura POST sin es_nota → 403 sin tocar el servicio."""
    _login(app_client, ["control_urgencias"])
    with patch.object(routes, "add_error") as mock_add:
        resp = app_client.post("/api/control-errores", json={"factura": "F1"})
    assert resp.status_code == 403
    assert resp.get_json()["status"] == "error"
    mock_add.assert_not_called()


def test_lectura_post_nota_llega_al_servicio(app_client):
    """Lectura POST con es_nota → pasa al servicio (propiedad la decide él)."""
    _login(app_client, ["control_urgencias"])
    with patch.object(
        routes, "add_error", return_value={"status": "success", "data": {}, "errors": []}
    ) as mock_add:
        resp = app_client.post(
            "/api/control-errores", json={"es_nota": True, "factura": "F1"}
        )
    assert resp.status_code == 200
    mock_add.assert_called_once()


def test_lectura_delete_llega_al_servicio(app_client):
    """Lectura DELETE → pasa al servicio (dueño/admin lo decide él, S6)."""
    _login(app_client, ["control_urgencias"])
    with patch.object(
        routes,
        "delete_error",
        return_value={"status": "success", "data": {}, "errors": []},
    ) as mock_del:
        resp = app_client.delete("/api/control-errores/abc123")
    assert resp.status_code == 200
    mock_del.assert_called_once()
