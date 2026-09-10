"""TDD tests for dominio-grupo-error T6: explicit dominio threading in detect_all.

Spec area isolation parity: every RuleBasedDetector call in the 9 area
orchestrators MUST pass its area dominio; an urgencias sheet with an
odontologia-only violation yields zero findings from that rule.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

SERVICES_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "services"

AREA_MODULES = {
    "ambulatoria": "ambulatoria",
    "equipos_basicos": "equipos_basicos",
    "extramural": "extramural",
    "farmacia": "farmacia",
    "hospitalizacion": "hospitalizacion",
    "intramural": "intramural",
    "odontologia": "odontologia",
    "urgencias": "urgencias",
}

BARE_CALL = re.compile(r'RuleBasedDetector\(\s*"[^"]+"\s*,\s*session\s*\)')
DOMINIO_CALL = re.compile(r"RuleBasedDetector\(.*?dominio\s*=", re.DOTALL)


def _read(area: str) -> str:
    return (SERVICES_DIR / area / "detect_all.py").read_text(encoding="utf-8")


class TestDominioThreadingStatic:
    def test_no_bare_detector_calls_without_dominio(self):
        for area in AREA_MODULES:
            bare = BARE_CALL.findall(_read(area))
            assert not bare, f"{area}/detect_all.py has calls without dominio: {bare[:3]}"

    def test_each_area_threads_its_own_dominio(self):
        for area, dominio in AREA_MODULES.items():
            text = _read(area)
            const = f"AREA_{dominio.upper()}"
            assert (
                f'dominio="{dominio}"' in text
                or f"dominio='{dominio}'" in text
                or f"dominio={const}" in text
            ), f"{area}/detect_all.py does not thread dominio={dominio!r}"


class TestAreaIsolationBehavioral:
    def _sheet(self):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        for col, header in enumerate(
            ["NUMERO_FACTURA", "RESPONSABLE_CIERRA", "FECHA_CIERRE", "FEC_FACTURA"],
            start=1,
        ):
            ws.cell(row=1, column=col, value=header)
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="ALGUIEN")
        return ws

    def test_urgencias_detectors_all_receive_urgencias_dominio(self):
        from app.services.urgencias import detect_all as urgencias_mod

        captured: list[str] = []

        class _FakeDetector:
            def __init__(self, rule_name, session, dominio):
                captured.append(dominio)
                self._rule_name = rule_name

            def detect(self, *args, **kwargs):
                # Odontologia-only violation: no urgencias rule fires
                return []

        session = MagicMock()
        session_manager = MagicMock()
        session_manager.__enter__.return_value = session

        indices = {
            "numero_factura": 0,
            "responsable_cierra": 1,
            "fecha_cierre": 2,
            "fec_factura": 3,
        }
        with (
            patch.object(urgencias_mod, "SessionManager", return_value=session_manager)
            if hasattr(urgencias_mod, "SessionManager")
            else patch(
                "app.services.engine.session_manager.SessionManager",
                return_value=session_manager,
            ),
            patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _FakeDetector,
            ),
        ):
            resultado, _ = urgencias_mod.detect_all_problems_urgencias(
                self._sheet(), indices
            )

        assert captured, "expected RuleBasedDetector instantiations"
        assert set(captured) == {"urgencias"}, f"leaked dominios: {set(captured)}"
        assert resultado["area"] == "urgencias"
