"""TDD tests for Cambio 2: dynamic domain rule evaluation (no hardcoded names).

Spec dominio-100-desde-DB:
- detect_domain_rules resolves enabled rules for the domain via RuleResolver
  (dominio + transversal, activo-only) and evaluates each DISTINCT nombre
  exactly once via RuleBasedDetector, threading the AREA dominio.
- Results bucket by rule-declared grupo_error (fallback: rule nombre).
- retired+activo=true resolves (single-flag); activo=false never evaluates.
- No DB writes here: hermetic SQLite + persist=False.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _session_with_rules(rowspec: list[tuple]):
    """Real SQLite session. Rows: (nombre, dominio, estado, activo, prioridad, grupo[, version])."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models import Regla
    import app.models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    for row in rowspec:
        nombre, dominio, estado, activo, prioridad, grupo = row[:6]
        version = row[6] if len(row) > 6 else 1
        session.add(
            Regla(
                nombre=nombre, dominio=dominio, estado=estado,
                version=version, prioridad=prioridad, severidad="error",
                activo=activo, grupo_error=grupo,
            )
        )
    session.commit()
    return session


class _RecordingDetector:
    """Fake RuleBasedDetector: records (nombre, dominio), serves payloads."""

    instances: list[tuple[str, str]] = []
    payloads: dict[str, list[dict]] = {}

    def __init__(self, nombre: str, session, dominio: str) -> None:
        type(self).instances.append((nombre, dominio))
        self._nombre = nombre

    def detect(self, *args, **kwargs):
        return [dict(p) for p in type(self).payloads.get(self._nombre, [])]

    @classmethod
    def reset(cls, payloads: dict | None = None) -> None:
        cls.instances = []
        cls.payloads = dict(payloads or {})


class TestDetectDomainRules:
    def test_resolves_domain_and_transversal_rules(self):
        from app.services.engine.domain_detection import detect_domain_rules

        session = _session_with_rules([
            ("regla_odonto", "odontologia", "active", True, 10, "Profesionales"),
            ("regla_trans", "transversal", "active", True, 20, "Decimales"),
            ("regla_urg", "urgencias", "active", True, 30, "Decimales"),
        ])
        _RecordingDetector.reset()
        try:
            with patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _RecordingDetector,
            ):
                batches = detect_domain_rules(
                    session, "odontologia", None, {}, persist=False,
                )
        finally:
            session.close()
        assert [b.nombre for b in batches] == ["regla_odonto", "regla_trans"]
        assert [(n, d) for n, d in _RecordingDetector.instances] == [
            ("regla_odonto", "odontologia"),
            ("regla_trans", "odontologia"),
        ]

    def test_threads_area_dominio_into_every_detector(self):
        from app.services.engine.domain_detection import detect_domain_rules

        session = _session_with_rules([
            ("regla_trans", "transversal", "active", True, 10, "Decimales"),
        ])
        _RecordingDetector.reset()
        try:
            with patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _RecordingDetector,
            ):
                detect_domain_rules(session, "urgencias", None, {}, persist=False)
        finally:
            session.close()
        assert _RecordingDetector.instances == [("regla_trans", "urgencias")]

    def test_dedupes_same_nombre_across_domains(self):
        from app.services.engine.domain_detection import detect_domain_rules

        session = _session_with_rules([
            ("valores_decimales", "odontologia", "active", True, 10, "Decimales", 1),
            ("valores_decimales", "transversal", "active", True, 20, "Decimales", 2),
        ])
        _RecordingDetector.reset({"valores_decimales": [{"factura": "F1"}]})
        try:
            with patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _RecordingDetector,
            ):
                batches = detect_domain_rules(
                    session, "odontologia", None, {}, persist=False,
                )
        finally:
            session.close()
        assert [b.nombre for b in batches] == ["valores_decimales"]
        assert _RecordingDetector.instances == [("valores_decimales", "odontologia")]
        assert batches[0].items == [{"factura": "F1"}]

    def test_buckets_by_grupo_error_with_nombre_fallback(self):
        from app.services.engine.domain_detection import (
            detect_domain_rules,
            group_by_grupo,
        )

        session = _session_with_rules([
            ("r1", "odontologia", "active", True, 10, "Profesionales"),
            ("r2", "odontologia", "active", True, 20, "Profesionales"),
            ("r_sin_grupo", "odontologia", "active", True, 30, None),
        ])
        _RecordingDetector.reset({
            "r1": [{"factura": "F1"}],
            "r2": [{"factura": "F2"}],
            "r_sin_grupo": [{"factura": "F3"}],
        })
        try:
            with patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _RecordingDetector,
            ):
                batches = detect_domain_rules(
                    session, "odontologia", None, {}, persist=False,
                )
        finally:
            session.close()
        grupos = group_by_grupo(batches)
        assert sorted(grupos) == ["Profesionales", "r_sin_grupo"]
        assert [i["factura"] for i in grupos["Profesionales"]] == ["F1", "F2"]
        assert grupos["r_sin_grupo"] == [{"factura": "F3"}]

    def test_retired_activo_true_evaluates_activo_false_skipped(self):
        from app.services.engine.domain_detection import detect_domain_rules

        session = _session_with_rules([
            ("drift_rule", "odontologia", "retired", True, 10, "Decimales"),
            ("off_rule", "odontologia", "active", False, 20, "Decimales"),
        ])
        _RecordingDetector.reset()
        try:
            with patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _RecordingDetector,
            ):
                batches = detect_domain_rules(
                    session, "odontologia", None, {}, persist=False,
                )
        finally:
            session.close()
        assert [b.nombre for b in batches] == ["drift_rule"]

    def test_empty_resolve_evaluates_nothing(self):
        from app.services.engine.domain_detection import detect_domain_rules

        session = _session_with_rules([])
        _RecordingDetector.reset()
        try:
            with patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _RecordingDetector,
            ):
                batches = detect_domain_rules(
                    session, "odontologia", None, {}, persist=False,
                )
        finally:
            session.close()
        assert batches == []
        assert _RecordingDetector.instances == []


class TestSplitCodigoEntidad:
    def test_splits_grupo_into_two_legacy_buckets(self):
        from app.services.engine.domain_detection import (
            detect_domain_rules,
            group_by_grupo,
            split_codigo_entidad,
        )

        session = _session_with_rules([
            ("tipo_id_requiere_entidad_86000", "transversal", "active", True, 10,
             "Codigo-Entidad-vs-Afiliacion"),
            ("codigo_entidad", "transversal", "active", True, 20,
             "Codigo-Entidad-vs-Afiliacion"),
        ])
        _RecordingDetector.reset({
            "tipo_id_requiere_entidad_86000": [{"factura": "F1"}],
            "codigo_entidad": [{"factura": "F2"}],
        })
        try:
            with patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _RecordingDetector,
            ):
                batches = detect_domain_rules(
                    session, "odontologia", None, {}, persist=False,
                )
        finally:
            session.close()
        tipo_entidad, codigo = split_codigo_entidad(group_by_grupo(batches), batches)
        assert [i["factura"] for i in tipo_entidad] == ["F1"]
        assert [i["factura"] for i in codigo] == ["F2"]
