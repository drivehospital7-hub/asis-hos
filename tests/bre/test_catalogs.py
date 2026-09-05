"""Catalog seed tests (Slice 1, strict TDD).

Additive seeds: rerun leaves existing keys unchanged. cat_in resolves
members via the catalogos table without hardcoding lists.
"""
from pathlib import Path


def test_catalog_seed_rerun_is_additive() -> None:
    text = Path("migrations/010_seed_hospitalizacion_engine_rules.sql").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "profesionales_urgencias" in lowered
    assert ("where not exists" in lowered) or ("on conflict do nothing" in lowered)


def test_catalogo_model_is_additive() -> None:
    from app.models import Catalogo

    assert Catalogo.__tablename__ == "catalogos"
    cols = {c.name for c in Catalogo.__table__.columns}
    assert {"key", "value"} <= cols


def test_cat_in_resolves_members_and_rejects_non_members() -> None:
    from app.services.engine.evaluators import CatalogInEvaluator

    class _Result:
        def __init__(self, value):
            self._value = value

        def fetchone(self):
            return (self._value,)

    class _Session:
        def __init__(self, value):
            self._value = value

        def execute(self, *args, **kwargs):
            return _Result(self._value)

    class _Context:
        def __init__(self, session):
            self.session = session

    evaluator = CatalogInEvaluator()
    member_ctx = _Context(_Session(["A1", "B2"]))
    assert evaluator.evaluate({}, "a1", "profesionales_urgencias", member_ctx) is True
    assert evaluator.evaluate({}, "ZZ", "profesionales_urgencias", member_ctx) is False


def test_cat_in_missing_key_returns_false() -> None:
    from app.services.engine.evaluators import CatalogInEvaluator

    class _Empty:
        def execute(self, *args, **kwargs):
            class _R:
                def fetchone(self):
                    return None

            return _R()

    class _Context:
        session = _Empty()

    assert CatalogInEvaluator().evaluate({}, "A1", "missing_key", _Context()) is False
