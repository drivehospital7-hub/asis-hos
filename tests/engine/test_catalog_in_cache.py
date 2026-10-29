"""Unit tests for CatalogInEvaluator cache (no DB, fake session)."""

import time

from app.services.engine.evaluators import (
    CATALOG_CACHE_TTL_SECONDS,
    CatalogInEvaluator,
)


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def fetchone(self):
        if self._value is None:
            return None
        return (self._value,)


class _FakeSession:
    def __init__(self, catalogs):
        self.catalogs = catalogs
        self.calls = 0

    def execute(self, query, params):
        self.calls += 1
        return _FakeResult(self.catalogs.get(params["key"]))


class _Ctx:
    def __init__(self, session):
        self.session = session


def test_single_query_for_many_rows_same_verdicts():
    ev = CatalogInEvaluator()
    session = _FakeSession({"codigos": ["A", "b "]})
    ctx = _Ctx(session)
    assert ev.evaluate({}, "a", "codigos", context=ctx) is True
    assert ev.evaluate({}, "B", "codigos", context=ctx) is True
    assert ev.evaluate({}, "zzz", "codigos", context=ctx) is False
    assert session.calls == 1


def test_missing_catalog_is_false_and_cached_negative():
    ev = CatalogInEvaluator()
    session = _FakeSession({})
    ctx = _Ctx(session)
    assert ev.evaluate({}, "a", "nope", context=ctx) is False
    assert ev.evaluate({}, "a", "nope", context=ctx) is False
    assert session.calls == 1


def test_invalidate_forces_requery_with_new_values():
    ev = CatalogInEvaluator()
    session = _FakeSession({"k": ["A"]})
    ctx = _Ctx(session)
    assert ev.evaluate({}, "A", "k", context=ctx) is True
    assert ev.evaluate({}, "B", "k", context=ctx) is False
    session.catalogs["k"] = ["A", "B"]
    ev.invalidate("k")
    assert ev.evaluate({}, "B", "k", context=ctx) is True
    assert session.calls == 2


def test_ttl_expiry_requeries():
    ev = CatalogInEvaluator()
    session = _FakeSession({"k": ["A"]})
    ctx = _Ctx(session)
    assert ev.evaluate({}, "A", "k", context=ctx) is True
    # Envejecer la entrada mas alla del TTL
    for key in list(ev._catalog_cache):
        val, _ = ev._catalog_cache[key]
        ev._catalog_cache[key] = (val, time.monotonic() - CATALOG_CACHE_TTL_SECONDS - 1)
    assert ev.evaluate({}, "A", "k", context=ctx) is True
    assert session.calls == 2


def test_no_session_still_false_without_query():
    ev = CatalogInEvaluator()
    session = _FakeSession({"k": ["A"]})
    assert ev.evaluate({}, "A", "k", context=None) is False
    assert session.calls == 0


def test_accent_folding_matches_variants():
    ev = CatalogInEvaluator()
    session = _FakeSession({"nombres": ["ESPAÑA DIAZ LORENY ALEJANDRA", "Núñez"]})
    ctx = _Ctx(session)
    assert ev.evaluate({}, "ESPANA DIAZ LORENY ALEJANDRA", "nombres", context=ctx) is True
    assert ev.evaluate({}, "españa diaz loreny alejandra", "nombres", context=ctx) is True
    assert ev.evaluate({}, "NUNEZ", "nombres", context=ctx) is True
    assert ev.evaluate({}, "OTRO NOMBRE", "nombres", context=ctx) is False
