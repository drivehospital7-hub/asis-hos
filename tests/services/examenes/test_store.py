"""Tests for app/utils/examenes_store.py + app/constants/examenes.py.

Covers EX-4 (catalog store), EX-5 (listado no-reseed policy), EX-19
(store tests) and the constants module that drives the store: filenames,
DEFAULT_EXAMENES (verbatim source defaults) and CSV_HEADERS. All file IO is
redirected to tmp_path via DATA_DIR monkeypatch.

NOTE: the source catalog (D:\\CODE\\examenes\\examenes.json) contains 66
entries, not the 54 stated in the SDD artifacts. Tests assert 66 (the
verbatim source truth); the deviation is documented in apply-progress.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from app.constants.examenes import (
    CSV_HEADERS,
    DEFAULT_EXAMENES,
    EX_EXAMENES_FILE,
    EX_LISTADO_FILE,
)
from app.utils import examenes_store

DATA_DIR = examenes_store.DATA_DIR


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect every store IO to a per-test tmp dir."""
    monkeypatch.setattr(examenes_store, "DATA_DIR", tmp_path)


# =============================================================================
# Constants module (task 1.1)
# =============================================================================


class TestExamenesConstants:
    """app/constants/examenes.py values (filenames, seed, CSV)."""

    def test_data_filenames(self) -> None:
        """EX_EXAMENES_FILE/EX_LISTADO_FILE MUST name the catalog/listado files."""
        assert EX_EXAMENES_FILE == "examenes.json"
        assert EX_LISTADO_FILE == "listado.json"

    def test_default_examenes_is_source_verbatim(self) -> None:
        """DEFAULT_EXAMENES MUST equal the source catalog (66 entries)."""
        source = json.loads(
            Path(r"D:\CODE\examenes\examenes.json").read_text(encoding="utf-8")
        )
        assert DEFAULT_EXAMENES == source
        assert len(DEFAULT_EXAMENES) == 66

    def test_default_examenes_known_entries(self) -> None:
        """Spot-check well-known catalog rows (codes, names, payer flags)."""
        by_cod = {e["cod"]: e for e in DEFAULT_EXAMENES}
        assert by_cod["903859"]["nom"] == "Potasio En Suero U Otros Fluidos"
        assert by_cod["903859"]["neps"] == "X"
        assert by_cod["903859"]["mall"] == "X"
        assert by_cod["903859"]["emss"] == "X"
        assert by_cod["904921"]["neps"] == "AUTH"
        assert by_cod["904921"]["emss"] == ""
        assert by_cod["903833"]["nom"] == "FOSFATASA ALCALINA"

    def test_csv_headers_exact(self) -> None:
        """CSV_HEADERS MUST be the exact EX-14 header row (order sensitive)."""
        assert CSV_HEADERS == [
            "N°",
            "Paciente",
            "Cedula",
            "Codigo",
            "Examen",
            "NEPS",
            "MALLAM",
            "EMSS",
            "Facturador",
            "Fecha/Hora",
        ]


# =============================================================================
# Catalog store (EX-4) + no-reseed policy (EX-5)
# =============================================================================


class TestGetExamenes:
    """get_examenes reads the catalog; seeds ONLY when the file is absent."""

    def test_seed_when_absent(self, tmp_path: Path) -> None:
        """No examenes.json → returns DEFAULT_EXAMENES AND writes the seed file."""
        result = examenes_store.get_examenes()

        assert result == DEFAULT_EXAMENES
        seed_file = tmp_path / "examenes.json"
        assert seed_file.exists()
        assert json.loads(seed_file.read_text(encoding="utf-8")) == DEFAULT_EXAMENES

    def test_no_reseed_over_existing(self, tmp_path: Path) -> None:
        """Existing catalog with custom data → returned verbatim, never overwritten."""
        custom = [
            {"cod": "999001", "nom": "Examen Personalizado", "neps": "X", "mall": "", "emss": ""}
        ]
        (tmp_path / "examenes.json").write_text(
            json.dumps(custom, ensure_ascii=False), encoding="utf-8"
        )

        result = examenes_store.get_examenes()

        assert result == custom
        on_disk = json.loads((tmp_path / "examenes.json").read_text(encoding="utf-8"))
        assert on_disk == custom

    def test_no_reseed_after_modification(self, tmp_path: Path) -> None:
        """After an initial seed, a later write is never reset to defaults."""
        examenes_store.get_examenes()  # seeds defaults
        modified = [{"cod": "777", "nom": "Modificado"}]
        examenes_store.save_examenes(modified)

        assert examenes_store.get_examenes() == modified

    def test_empty_existing_file_returns_empty(self, tmp_path: Path) -> None:
        """Existing file with '[]' → [] (no seed: file exists)."""
        (tmp_path / "examenes.json").write_text("[]", encoding="utf-8")
        assert examenes_store.get_examenes() == []

    def test_corrupt_file_returns_empty_and_logs(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unparseable JSON → [] + logged error, never crash (EX-4)."""
        (tmp_path / "examenes.json").write_text("{bad syntax}", encoding="utf-8")

        with caplog.at_level(logging.ERROR, logger="app.utils.examenes_store"):
            result = examenes_store.get_examenes()

        assert result == []
        assert any("examenes" in r.message.lower() for r in caplog.records)


class TestGetListado:
    """get_listado reads the listado; NEVER seeds (manual deploy step, EX-5)."""

    def test_absent_returns_empty_and_creates_nothing(self, tmp_path: Path) -> None:
        """No listado.json → [] and NO file is created by code."""
        result = examenes_store.get_listado()

        assert result == []
        assert not (tmp_path / "listado.json").exists()

    def test_reads_existing(self, tmp_path: Path) -> None:
        """Existing listado with live records → identical records (no overwrite)."""
        records = [
            {
                "id": "pf-1",
                "paciente": "Paciente",
                "cedula": "123",
                "facturador": "ANGIE ARIAS",
                "hora": "01/01/2026 08:00",
                "items": [{"cod": "903859", "nom": "Potasio", "neps": "X", "mall": "X", "emss": "X"}],
            }
        ]
        (tmp_path / "listado.json").write_text(
            json.dumps(records, ensure_ascii=False), encoding="utf-8"
        )

        assert examenes_store.get_listado() == records

    def test_corrupt_file_returns_empty_and_logs(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unparseable JSON → [] + logged error, never crash (EX-4)."""
        (tmp_path / "listado.json").write_text("{nope}", encoding="utf-8")

        with caplog.at_level(logging.ERROR, logger="app.utils.examenes_store"):
            result = examenes_store.get_listado()

        assert result == []
        assert any("listado" in r.message.lower() for r in caplog.records)


# =============================================================================
# Atomic writes (EX-4 / EX-19)
# =============================================================================


class TestAtomicWrites:
    """save_examenes / save_listado write atomically (mkstemp + Path.replace)."""

    def test_save_examenes_creates_parseable_file(self, tmp_path: Path) -> None:
        """save → file exists, JSON parseable, content matches."""
        data = [{"cod": "1", "nom": "A", "neps": "", "mall": "", "emss": ""}]
        examenes_store.save_examenes(data)

        target = tmp_path / "examenes.json"
        assert target.exists()
        assert json.loads(target.read_text(encoding="utf-8")) == data

    def test_save_listado_creates_parseable_file(self, tmp_path: Path) -> None:
        """save → file exists, JSON parseable, content matches."""
        data = [{"id": "pf-x", "paciente": "P", "items": []}]
        examenes_store.save_listado(data)

        target = tmp_path / "listado.json"
        assert target.exists()
        assert json.loads(target.read_text(encoding="utf-8")) == data

    def test_atomic_write_preserves_original_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If Path.replace fails, the original file stays intact (EX-4 atomic)."""
        original = [{"cod": "orig", "nom": "Original", "neps": "", "mall": "", "emss": ""}]
        examenes_store.save_examenes(original)

        def failing_replace(self, target) -> None:  # noqa: ANN001
            raise OSError("Simulated write failure")

        monkeypatch.setattr(Path, "replace", failing_replace)

        with pytest.raises(OSError, match="Simulated write failure"):
            examenes_store.save_examenes([{"cod": "new", "nom": "Nuevo", "neps": "", "mall": "", "emss": ""}])

        on_disk = json.loads((tmp_path / "examenes.json").read_text(encoding="utf-8"))
        assert on_disk == original


# =============================================================================
# FLASK_DATA_SUFFIX (EX-4/EX-5)
# =============================================================================


class TestDataSuffix:
    """FLASK_DATA_SUFFIX MUST isolate dev files from prod files."""

    def test_suffix_reads_writes_suffixed_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """With FLASK_DATA_SUFFIX=-dev → examenes-dev.json is read/written."""
        monkeypatch.setenv("FLASK_DATA_SUFFIX", "-dev")
        data = [{"cod": "dev", "nom": "Dev only", "neps": "", "mall": "", "emss": ""}]
        examenes_store.save_examenes(data)

        assert (tmp_path / "examenes-dev.json").exists()
        assert not (tmp_path / "examenes.json").exists()
        assert examenes_store.get_examenes() == data

    def test_suffix_isolates_listado(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dev listado never touches the prod file (EX-5 dev/prod scenario)."""
        prod_records = [{"id": "prod", "paciente": "Prod", "items": []}]
        (tmp_path / "listado.json").write_text(json.dumps(prod_records), encoding="utf-8")

        monkeypatch.setenv("FLASK_DATA_SUFFIX", "-dev")
        examenes_store.save_listado([{"id": "dev", "paciente": "Dev", "items": []}])

        assert (tmp_path / "listado-dev.json").exists()
        # prod file untouched
        assert json.loads((tmp_path / "listado.json").read_text(encoding="utf-8")) == prod_records

    def test_no_suffix_uses_bare_filename(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without the env var → bare examenes.json / listado.json."""
        monkeypatch.delenv("FLASK_DATA_SUFFIX", raising=False)
        examenes_store.save_listado([{"id": "bare", "paciente": "B", "items": []}])

        assert (tmp_path / "listado.json").exists()
        assert not (tmp_path / "listado-dev.json").exists()


# =============================================================================
# Committed seed + gitignore (task 1.5)
# =============================================================================


class TestSeedFile:
    """Repo rollout: app/data/examenes.json committed; listado never committed."""

    def test_committed_seed_matches_defaults(self) -> None:
        """app/data/examenes.json MUST exist and equal DEFAULT_EXAMENES."""
        seed_file = DATA_DIR / "examenes.json"
        assert seed_file.exists(), "app/data/examenes.json seed is missing"
        assert json.loads(seed_file.read_text(encoding="utf-8")) == DEFAULT_EXAMENES

    def test_gitignore_unignores_seed(self) -> None:
        """.gitignore MUST contain the negation for app/data/examenes.json."""
        gitignore = Path(__file__).resolve().parents[3] / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "!app/data/examenes.json" in content