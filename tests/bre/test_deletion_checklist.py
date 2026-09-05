"""Legacy-route deletion checklist as code (Slice 3.1, strict TDD).

Gates the deletion of ``app/routes/urgencias.py`` and
``app/routes/odontologia_equipos_basicos.py`` (already removed on the
feature branch in favor of unified ``POST /procesar``).

No deletions are executed here — this file only VERIFIES the checklist
artifact and the unified-route coverage. Direct-to-main merge is forbidden:
deletions land via the feature-branch chain only.
"""
from pathlib import Path
import re
import subprocess

REPO = Path(__file__).resolve().parents[2]
ROUTES = REPO / "app" / "routes"
CHECKLIST = Path(__file__).with_name("LEGACY_DELETION_CHECKLIST.md")

LEGACY_MODULES = ("urgencias.py", "odontologia_equipos_basicos.py")
LEGACY_BLUEPRINTS = ("urgencias_bp", "odontologia_equipos_basicos_bp")


def test_checklist_artifact_exists_and_signed() -> None:
    assert CHECKLIST.exists(), "checklist artifact missing — deletion NOT approved"
    text = CHECKLIST.read_text(encoding="utf-8")
    assert "PASS" in text
    assert "feature/procesamiento-unificado" in text
    assert "NO direct-to-main" in text


def test_legacy_route_modules_absent_on_feature() -> None:
    for module in LEGACY_MODULES:
        assert not (ROUTES / module).exists(), f"legacy route still present: {module}"


def test_unified_procesar_covers_legacy_contract() -> None:
    target = ROUTES / "procesar.py"
    assert target.exists(), "unified route missing — cannot approve deletion"
    text = target.read_text(encoding="utf-8")
    assert "procesar_bp" in text
    assert "detect_problems_only" in text
    assert "AREA_UNIFICADA" in text
    assert '"status"' in text and '"errors"' in text
    assert "import polars" not in text and "import openpyxl" not in text


def test_no_stale_legacy_blueprint_imports() -> None:
    scanned = [REPO / "app" / "__init__.py", *sorted(ROUTES.glob("*.py"))]
    assert len(scanned) > 3
    for path in scanned:
        text = path.read_text(encoding="utf-8")
        for name in LEGACY_BLUEPRINTS:
            pattern = r"(?<![\w])" + re.escape(name) + r"(?![\w])"
            assert re.search(pattern, text) is None, f"stale import {name} in {path.name}"
    init_text = (REPO / "app" / "__init__.py").read_text(encoding="utf-8")
    assert "procesar_bp" in init_text


def test_not_executed_on_main_branch() -> None:
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=REPO, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return
    if out.returncode != 0 or not out.stdout.strip():
        return
    assert out.stdout.strip() not in ("main", "master")
