"""Integration tests for /api/examenes and /api/listado (EX-2/EX-3/EX-19).

Covers: 401 anonymous JSON, 403 read-only POST with file unchanged, envelope
shape (data.examenes / data.listado nesting), 400 non-array bodies, and
POST→GET round-trips with fields+order intact.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.utils import examenes_store

CATALOG = [
    {"cod": "903859", "nom": "Potasio En Suero U Otros Fluidos", "neps": "X", "mall": "X", "emss": "X"},
    {"cod": "904921", "nom": "Tiroxina Libre", "neps": "AUTH", "mall": "X", "emss": ""},
]

PREFACTURAS = [
    {
        "id": "pf-1720000000000-abc",
        "paciente": "Paciente Uno",
        "cedula": "1001",
        "facturador": "ANGIE ARIAS",
        "hora": "01/01/2026 08:00",
        "items": [
            {
                "cod": "903859",
                "nom": "Potasio En Suero U Otros Fluidos",
                "neps": "X",
                "mall": "X",
                "emss": "X",
                "cantidad": 2,
            }
        ],
    },
    {
        "id": "pf-1720000000001-xyz",
        "paciente": "Paciente Dos",
        "cedula": "1002",
        "facturador": "CATALEYA TAPIA",
        "hora": "02/01/2026 09:30",
        "items": [
            # legacy 5-field item — no cantidad key, must stay valid (EX-21/EX-28)
            {"cod": "904921", "nom": "Tiroxina Libre", "neps": "AUTH", "mall": "X", "emss": ""}
        ],
    },
]


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect store IO to tmp so tests never touch app/data."""
    monkeypatch.setattr(examenes_store, "DATA_DIR", tmp_path)


def _authenticate(client, permisos: list[str], username: str = "test") -> None:
    """Establece sesión autenticada con los permisos dados."""
    with client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = username
        sess["permisos"] = permisos


def _write_listado(tmp_path: Path, data: list) -> None:
    (tmp_path / "listado.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestAnonymous401:
    """EX-1/EX-2: no session → 401 error envelope for JSON/XHR requests."""

    def test_anonymous_get_catalog_401(self, app_client) -> None:
        """GET /api/examenes without session → 401 {status:error, errors:['No autenticado']}."""
        response = app_client.get(
            "/api/examenes", headers={"X-Requested-With": "XMLHttpRequest"}
        )

        assert response.status_code == 401
        body = response.get_json()
        assert body["status"] == "error"
        assert body["data"] == {}
        assert body["errors"] == ["No autenticado"]

    def test_anonymous_post_listado_401(self, app_client) -> None:
        """POST /api/listado without session (JSON) → 401 envelope."""
        response = app_client.post("/api/listado", json=PREFACTURAS)

        assert response.status_code == 401
        body = response.get_json()
        assert body["status"] == "error"
        assert body["data"] == {}
        assert body["errors"] == ["No autenticado"]


class TestReadOnlyGating:
    """EX-2: read-only user can GET; writes → 403 with file unchanged."""

    def test_read_only_get_catalog_envelope(self, app_client, tmp_path: Path) -> None:
        """GET /api/examenes → 200, data.examenes holds the catalog array."""
        (tmp_path / "examenes.json").write_text(
            json.dumps(CATALOG, ensure_ascii=False), encoding="utf-8"
        )
        _authenticate(app_client, ["examenes"])

        response = app_client.get("/api/examenes")

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "success"
        assert body["errors"] == []
        assert body["data"]["examenes"] == CATALOG

    def test_read_only_get_listado_envelope(self, app_client, tmp_path: Path) -> None:
        """GET /api/listado → 200, data.listado holds the array."""
        _write_listado(tmp_path, PREFACTURAS)
        _authenticate(app_client, ["examenes"])

        response = app_client.get("/api/listado")

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "success"
        assert body["data"]["listado"] == PREFACTURAS

    def test_read_only_post_listado_403_file_unchanged(
        self, app_client, tmp_path: Path
    ) -> None:
        """POST /api/listado by read-only → 403 envelope, file unchanged (EX-2)."""
        _write_listado(tmp_path, PREFACTURAS)
        _authenticate(app_client, ["examenes"])

        response = app_client.post("/api/listado", json=[{"id": "pf-evil"}])

        assert response.status_code == 403
        body = response.get_json()
        assert body["status"] == "error"
        assert body["data"] == {}
        assert body["errors"] == ["Permiso denegado"]
        on_disk = json.loads((tmp_path / "listado.json").read_text(encoding="utf-8"))
        assert on_disk == PREFACTURAS

    def test_read_only_post_catalog_403(self, app_client) -> None:
        """POST /api/examenes by read-only → 403 envelope."""
        _authenticate(app_client, ["examenes"])

        response = app_client.post("/api/examenes", json=CATALOG)

        assert response.status_code == 403
        assert response.get_json()["status"] == "error"


class TestWriteOps:
    """EX-2/EX-3: write user persists arrays; returns success envelope."""

    def test_write_post_listado_persists(self, app_client, tmp_path: Path) -> None:
        """POST /api/listado (array) → 200 success envelope + persisted file."""
        _authenticate(app_client, ["examenes:write"])

        response = app_client.post("/api/listado", json=PREFACTURAS)

        assert response.status_code == 200
        body = response.get_json()
        assert body == {"status": "success", "data": {}, "errors": []}
        assert json.loads((tmp_path / "listado.json").read_text(encoding="utf-8")) == PREFACTURAS

    def test_write_post_catalog_persists(self, app_client, tmp_path: Path) -> None:
        """POST /api/examenes (array) → 200 success envelope + persisted file."""
        _authenticate(app_client, ["examenes:write"])

        response = app_client.post("/api/examenes", json=CATALOG)

        assert response.status_code == 200
        assert response.get_json() == {"status": "success", "data": {}, "errors": []}
        assert json.loads((tmp_path / "examenes.json").read_text(encoding="utf-8")) == CATALOG


class TestRoundTrip:
    """EX-3 round-trip: GET returns exactly what was posted (fields+order)."""

    def test_listado_round_trip(self, app_client, tmp_path: Path) -> None:
        _authenticate(app_client, ["examenes:write"])
        assert app_client.post("/api/listado", json=PREFACTURAS).status_code == 200

        response = app_client.get("/api/listado")

        assert response.status_code == 200
        assert response.get_json()["data"]["listado"] == PREFACTURAS

    def test_cantidad_persists_round_trip_legacy_valid(self, app_client, tmp_path: Path) -> None:
        """EX-28: item cantidad persists POST→GET; legacy 5-field items valid."""
        _authenticate(app_client, ["examenes:write"])
        assert app_client.post("/api/listado", json=PREFACTURAS).status_code == 200

        response = app_client.get("/api/listado")

        assert response.status_code == 200
        listado = response.get_json()["data"]["listado"]
        assert listado[0]["items"][0]["cantidad"] == 2
        # legacy item is returned verbatim: cantidad key stays ABSENT
        assert "cantidad" not in listado[1]["items"][0]

    def test_catalog_round_trip(self, app_client, tmp_path: Path) -> None:
        _authenticate(app_client, ["examenes:write"])
        assert app_client.post("/api/examenes", json=CATALOG).status_code == 200

        response = app_client.get("/api/examenes")

        assert response.status_code == 200
        assert response.get_json()["data"]["examenes"] == CATALOG


class TestInvalidBody400:
    """EX-3 deviation: non-array POST bodies → 400 envelope, file unchanged."""

    def test_listado_object_body_400(self, app_client, tmp_path: Path) -> None:
        _write_listado(tmp_path, PREFACTURAS)
        _authenticate(app_client, ["examenes:write"])

        response = app_client.post("/api/listado", json={"id": "not-an-array"})

        assert response.status_code == 400
        body = response.get_json()
        assert body["status"] == "error"
        assert body["data"] == {}
        assert isinstance(body["errors"], list)
        assert body["errors"]
        assert json.loads((tmp_path / "listado.json").read_text(encoding="utf-8")) == PREFACTURAS

    def test_catalog_object_body_400(self, app_client, tmp_path: Path) -> None:
        _authenticate(app_client, ["examenes:write"])

        response = app_client.post("/api/examenes", json={"cod": "x"})

        assert response.status_code == 400
        assert response.get_json()["status"] == "error"
        assert not (tmp_path / "examenes.json").exists()

    def test_listado_malformed_json_400(self, app_client, tmp_path: Path) -> None:
        """Unparseable JSON body → 400 envelope, file unchanged."""
        _write_listado(tmp_path, PREFACTURAS)
        _authenticate(app_client, ["examenes:write"])

        response = app_client.post(
            "/api/listado",
            data="{not json",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.get_json()["status"] == "error"
        assert json.loads((tmp_path / "listado.json").read_text(encoding="utf-8")) == PREFACTURAS


EXTRA = {
    "id": "pf-99",
    "paciente": "Paciente Nuevo",
    "cedula": "1099",
    "facturador": "ANGIE ARIAS",
    "hora": "03/01/2026 10:00",
    "items": [
        {"cod": "903859", "nom": "Potasio En Suero U Otros Fluidos", "neps": "X", "mall": "X", "emss": "X"}
    ],
}


class TestOptimisticConcurrency:
    """R4-001: base_hash opcional → 409 sin escribir si el estado cambió."""

    def test_sequential_same_base_second_write_409(self, app_client, tmp_path: Path) -> None:
        """Dos POSTs con el mismo base_hash: el segundo → 409 sin pisar el primero."""
        _write_listado(tmp_path, PREFACTURAS)
        _authenticate(app_client, ["examenes:write"])
        base = examenes_store.file_hash("listado.json")
        primera = PREFACTURAS + [EXTRA]
        segunda = PREFACTURAS + [EXTRA, {**EXTRA, "id": "pf-100"}]

        assert (
            app_client.post("/api/listado", json={"data": primera, "base_hash": base}).status_code
            == 200
        )
        res = app_client.post("/api/listado", json={"data": segunda, "base_hash": base})

        assert res.status_code == 409
        assert json.loads((tmp_path / "listado.json").read_text(encoding="utf-8")) == primera

    def test_matching_base_hash_200_and_persisted(self, app_client, tmp_path: Path) -> None:
        _write_listado(tmp_path, PREFACTURAS)
        _authenticate(app_client, ["examenes:write"])
        base = examenes_store.file_hash("listado.json")
        nueva = PREFACTURAS + [EXTRA]

        res = app_client.post("/api/listado", json={"data": nueva, "base_hash": base})

        assert res.status_code == 200
        assert res.get_json() == {"status": "success", "data": {}, "errors": []}
        assert json.loads((tmp_path / "listado.json").read_text(encoding="utf-8")) == nueva

    def test_stale_base_hash_409_file_unchanged(self, app_client, tmp_path: Path) -> None:
        _write_listado(tmp_path, PREFACTURAS)
        _authenticate(app_client, ["examenes:write"])

        res = app_client.post("/api/listado", json={"data": [EXTRA], "base_hash": "0" * 64})

        assert res.status_code == 409
        body = res.get_json()
        assert body["status"] == "error" and body["data"] == {} and body["errors"]
        assert json.loads((tmp_path / "listado.json").read_text(encoding="utf-8")) == PREFACTURAS

    def test_stale_base_hash_catalog_409(self, app_client, tmp_path: Path) -> None:
        (tmp_path / "examenes.json").write_text(json.dumps(CATALOG, ensure_ascii=False), encoding="utf-8")
        _authenticate(app_client, ["examenes:write"])

        res = app_client.post("/api/examenes", json={"data": CATALOG, "base_hash": "0" * 64})

        assert res.status_code == 409 and res.get_json()["status"] == "error"
        assert json.loads((tmp_path / "examenes.json").read_text(encoding="utf-8")) == CATALOG

    def test_absent_base_hash_legacy_replace(self, app_client, tmp_path: Path) -> None:
        _write_listado(tmp_path, PREFACTURAS)
        _authenticate(app_client, ["examenes:write"])

        res = app_client.post("/api/listado", json=[EXTRA])

        assert res.status_code == 200
        assert res.get_json()["status"] == "success"
        assert json.loads((tmp_path / "listado.json").read_text(encoding="utf-8")) == [EXTRA]