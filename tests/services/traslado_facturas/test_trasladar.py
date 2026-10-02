"""Tests for traslado: move/copy service extension + traslado_facturas routes."""

from __future__ import annotations

from pathlib import Path

import pytest

import app.routes.monitoreo_carpetas as monitoreo_route
import app.routes.traslado_facturas as traslado_route
from app.services.monitoreo_carpetas.move_service import execute_move


class _MockWatcher:
    """Minimal watcher double: records resync calls, no threads."""

    def __init__(self, roots: list[str]) -> None:
        self._roots = list(roots)
        self.calls: list[tuple[str, str]] = []

    def get_roots(self) -> list[str]:
        return list(self._roots)

    def remove_subtree(self, path: str) -> None:
        self.calls.append(("remove", path))

    def update_subtree(self, path: str) -> None:
        self.calls.append(("update", path))


def _make_tree(tmp_path: Path) -> tuple[Path, Path, list[str]]:
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    for name in ("FEV001", "FEV002"):
        (src / name).mkdir(parents=True)
        (src / name / "dummy.txt").write_text("f")
    dest.mkdir(parents=True)
    return src, dest, [str(src / "FEV001"), str(src / "FEV002")]


class TestExecuteCopy:
    def test_copy_keeps_source(self, tmp_path: Path) -> None:
        src, dest, sources = _make_tree(tmp_path)
        watcher = _MockWatcher([str(tmp_path)])
        moved, failed = execute_move(sources, str(dest), watcher, operation="copy")
        assert failed == []
        assert len(moved) == 2
        for name in ("FEV001", "FEV002"):
            assert (src / name).exists()
            assert (dest / name / "dummy.txt").read_text() == "f"

    def test_copy_no_remove_only_update(self, tmp_path: Path) -> None:
        src, dest, sources = _make_tree(tmp_path)
        watcher = _MockWatcher([str(tmp_path)])
        execute_move([sources[0]], str(dest), watcher, operation="copy")
        kinds = [kind for kind, _ in watcher.calls]
        assert "remove" not in kinds
        assert "update" in kinds

    def test_copy_collision_fails(self, tmp_path: Path) -> None:
        src, dest, sources = _make_tree(tmp_path)
        (dest / "FEV001").mkdir()
        watcher = _MockWatcher([str(tmp_path)])
        moved, failed = execute_move([sources[0]], str(dest), watcher, operation="copy")
        assert moved == []
        assert len(failed) == 1
        assert (src / "FEV001").exists()

    def test_default_operation_preserves_move(self, tmp_path: Path) -> None:
        src, dest, sources = _make_tree(tmp_path)
        watcher = _MockWatcher([str(tmp_path)])
        moved, failed = execute_move([sources[0]], str(dest), watcher)
        assert failed == []
        assert len(moved) == 1
        assert not (src / "FEV001").exists()
        assert (dest / "FEV001").exists()


@pytest.fixture(autouse=True)
def _isolate_watchers():
    """Reset the global route watcher around each test in this module."""
    try:
        monitoreo_route._watcher.reset()
    except Exception:
        pass
    yield
    try:
        monitoreo_route._watcher.reset()
    except Exception:
        pass


def _auth(app_client, permisos) -> None:
    with app_client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = "test"
        sess["permisos"] = permisos


def _roots(monkeypatch, roots: list[str]) -> None:
    monkeypatch.setattr(
        traslado_route, "get_roots", lambda: (list(roots), "env", None)
    )


class TestTrasladoRoutes:
    def test_shell_requires_perm(self, app_client) -> None:
        _auth(app_client, ["derechos"])
        resp = app_client.get(
            "/traslado-facturas/",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_shell_ok(self, app_client) -> None:
        _auth(app_client, ["monitoreo_carpetas"])
        resp = app_client.get("/traslado-facturas/")
        assert resp.status_code == 200

    def test_buscar_sin_cache_cubierta_guia_a_verificar(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        """Raíz cubierta sin cache → error que guía a Verificar (sin scan)."""
        _auth(app_client, ["monitoreo_carpetas"])
        _roots(monkeypatch, [str(tmp_path)])
        monitoreo_route._watcher._roots = [str(tmp_path)]
        assert monitoreo_route._watcher.get_result() is None
        resp = app_client.post(
            "/traslado-facturas/buscar", json={"codigos": "FEV001"}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "error"
        assert any("Verificar" in err for err in data["errors"])

    def test_buscar_sin_cache_no_cubierta_escanea_en_sync(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        """Raíz no cubierta sin cache → detect_all fresco, no error."""
        _auth(app_client, ["monitoreo_carpetas"])
        _roots(monkeypatch, [str(tmp_path)])
        assert monitoreo_route._watcher.get_result() is None
        resp = app_client.post(
            "/traslado-facturas/buscar", json={"codigos": "FEV001"}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["no_encontradas"] == ["FEV001"]

    def test_trasladar_operacion_invalida_422(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        _auth(app_client, ["*"])
        _roots(monkeypatch, [str(tmp_path)])
        resp = app_client.post(
            "/traslado-facturas/trasladar",
            json={"sources": [], "dest_dir": str(tmp_path), "operation": "erase"},
        )
        assert resp.status_code == 422

    def test_trasladar_copy_ok(self, app_client, monkeypatch, tmp_path: Path) -> None:
        src, dest, sources = _make_tree(tmp_path)
        _auth(app_client, ["*"])
        _roots(monkeypatch, [str(tmp_path)])
        resp = app_client.post(
            "/traslado-facturas/trasladar",
            json={"sources": [sources[0]], "dest_dir": str(dest), "operation": "copy"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["data"]["copied"]) == 1
        assert data["data"]["failed"] == []
        assert (src / "FEV001").exists()
        assert (dest / "FEV001").exists()

    def test_explorar_traversal_rechazado(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        _auth(app_client, ["monitoreo_carpetas"])
        _roots(monkeypatch, [str(tmp_path)])
        resp = app_client.get("/traslado-facturas/explorar", query_string={"path": "/etc"})
        assert resp.status_code in (400, 422)
        assert resp.get_json()["status"] == "error"

    def test_explorar_raices_ok(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        _auth(app_client, ["monitoreo_carpetas"])
        _roots(monkeypatch, [str(tmp_path)])
        resp = app_client.get("/traslado-facturas/explorar")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["actual"] is None
        assert len(data["data"]["dirs"]) == 1


def _seed_cache(monkeypatch_unused, covered: str) -> None:
    """Siembra el watcher global con una factura bajo la raíz cubierta."""
    from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult

    inv = InvoiceRecord(
        filename="FEV001",
        facturador="Juan",
        full_path=f"{covered}/Juan/FEV001",
        status="Verificada",
        invoice_type="FEV",
        invoice_code="FEV001",
    )
    watcher = monitoreo_route._watcher
    watcher._roots = [covered]
    watcher.set_result(ScanResult(
        facturas=[inv], indicadores={}, duplicados=[],
        vacias=[], errores_scan=[],
    ))


class TestBuscarRaicesLibresYPermisos:
    """Task 4: raíces libres (cache+fresco) + permiso propio traslado_facturas."""

    def test_buscar_mezcla_cache_y_scan_fresco(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        from unittest import mock

        from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult

        covered = str(tmp_path / "covered")
        uncovered = str(tmp_path / "free")
        _seed_cache(monkeypatch, covered)
        _auth(app_client, ["traslado_facturas"])
        _roots(monkeypatch, [covered])

        fresh_inv = InvoiceRecord(
            filename="FEV002", facturador="Ana",
            full_path=f"{uncovered}/Ana/FEV002",
            status="Verificada", invoice_type="FEV", invoice_code="FEV002",
        )
        fresh = ScanResult(
            facturas=[fresh_inv], indicadores={}, duplicados=[],
            vacias=[], errores_scan=[{"root": uncovered, "error": "x"}],
        )
        spy = mock.Mock(return_value=fresh)
        monkeypatch.setattr(
            "app.services.monitoreo_carpetas.detect_all.detect_all", spy
        )

        resp = app_client.post(
            "/traslado-facturas/buscar",
            json={"codigos": "FEV001 FEV002", "raices": [covered, uncovered]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert [e["codigo"] for e in data["data"]["encontradas"]] == [
            "FEV001", "FEV002",
        ]
        assert data["data"]["no_encontradas"] == []
        assert data["data"]["raices"] == [covered]
        assert data["data"]["raices_buscadas"] == [covered, uncovered]
        assert data["data"]["errores_scan"] == [{"root": uncovered, "error": "x"}]
        # detect_all fresco SOLO para la no cubierta
        spy.assert_called_once_with([uncovered])

    def test_raiz_inexistente_no_es_400(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        from unittest import mock

        from app.services.monitoreo_carpetas import ScanResult

        _auth(app_client, ["traslado_facturas"])
        _roots(monkeypatch, [str(tmp_path)])
        missing = str(tmp_path / "no_existe")
        fresh = ScanResult(
            facturas=[], indicadores={}, duplicados=[],
            vacias=[], errores_scan=[{"root": missing, "error": "no accesible"}],
        )
        monkeypatch.setattr(
            "app.services.monitoreo_carpetas.detect_all.detect_all",
            mock.Mock(return_value=fresh),
        )
        resp = app_client.post(
            "/traslado-facturas/buscar",
            json={"codigos": "FEV001", "raices": [missing]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["no_encontradas"] == ["FEV001"]
        assert data["data"]["errores_scan"] == [
            {"root": missing, "error": "no accesible"}
        ]

    def test_validacion_400(self, app_client, monkeypatch, tmp_path: Path) -> None:
        _auth(app_client, ["traslado_facturas"])
        _roots(monkeypatch, [str(tmp_path)])
        for body in (
            {"codigos": "   "},
            {"codigos": "FEV001", "raices": []},
            {"codigos": "FEV001", "raices": "no-lista"},
            {"codigos": "FEV001", "raices": ["   "]},
        ):
            resp = app_client.post("/traslado-facturas/buscar", json=body)
            assert resp.status_code == 400, body
            assert resp.get_json()["status"] == "error"

    def test_buscar_403_sin_ningun_permiso(self, app_client) -> None:
        _auth(app_client, ["derechos"])
        resp = app_client.post(
            "/traslado-facturas/buscar",
            json={"codigos": "FEV001"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_buscar_200_con_permiso_viejo_y_nuevo(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        for permisos in (["monitoreo_carpetas"], ["traslado_facturas"]):
            _auth(app_client, permisos)
            _roots(monkeypatch, [str(tmp_path)])
            resp = app_client.post(
                "/traslado-facturas/buscar", json={"codigos": "FEV001"}
            )
            assert resp.status_code == 200, permisos
            assert resp.get_json()["status"] == "success"

    def test_shell_200_con_permiso_nuevo(self, app_client) -> None:
        _auth(app_client, ["traslado_facturas"])
        assert app_client.get("/traslado-facturas/").status_code == 200

    def test_trasladar_write_viejo_y_nuevo_pasan(
        self, app_client, monkeypatch, tmp_path: Path
    ) -> None:
        for permisos in (
            ["monitoreo_carpetas:write"], ["traslado_facturas:write"],
        ):
            _auth(app_client, permisos)
            _roots(monkeypatch, [str(tmp_path)])
            resp = app_client.post(
                "/traslado-facturas/trasladar",
                json={"sources": [], "dest_dir": str(tmp_path)},
            )
            assert resp.status_code != 403, permisos

    def test_trasladar_403_con_solo_lectura_nueva(self, app_client) -> None:
        _auth(app_client, ["traslado_facturas"])
        resp = app_client.post(
            "/traslado-facturas/trasladar",
            json={"sources": [], "dest_dir": "/tmp"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_permiso_propio_y_ep_map_registrados(self) -> None:
        from pathlib import Path as _Path

        from app.constants.base import (
            ALLOWED_PERMISOS,
            PERMISO_MUTUAL_EXCLUSION,
        )

        assert "traslado_facturas" in ALLOWED_PERMISOS
        assert "traslado_facturas:write" in ALLOWED_PERMISOS
        assert (
            PERMISO_MUTUAL_EXCLUSION["traslado_facturas"]
            == "traslado_facturas:write"
        )
        assert (
            PERMISO_MUTUAL_EXCLUSION["traslado_facturas:write"]
            == "traslado_facturas"
        )
        # La navegación vive en el registro servidor (app/constants/navigation.py);
        # base.html renderiza desde GET /api/nav, sin mapa hardcodeado.
        from app.constants.navigation import NAV_MODULES, modulos_para

        by_key = {m["key"]: m for m in NAV_MODULES}
        assert by_key["traslado_facturas"]["endpoint"] == "traslado_facturas.index"
        assert by_key["traslado_facturas"]["href"] == "/traslado-facturas"
        hrefs = [m["href"] for m in modulos_para(["traslado_facturas"], autenticado=True)]
        assert "/traslado-facturas" in hrefs
