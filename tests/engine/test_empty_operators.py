"""Unit tests for is_empty / not_empty evaluators (no DB)."""

from app.services.engine.evaluators import (
    IsEmptyEvaluator,
    NotEmptyEvaluator,
    get_evaluator,
)


def test_registered():
    assert isinstance(get_evaluator("is_empty"), IsEmptyEvaluator)
    assert isinstance(get_evaluator("not_empty"), NotEmptyEvaluator)


def test_is_empty():
    ev = IsEmptyEvaluator()
    assert ev.evaluate({}, None, None) is True
    assert ev.evaluate({}, "", None) is True
    assert ev.evaluate({}, "   ", None) is True
    assert ev.evaluate({}, "0", None) is False
    assert ev.evaluate({}, "Soat", None) is False
    assert ev.evaluate({}, 0, None) is False


def test_not_empty():
    ev = NotEmptyEvaluator()
    assert ev.evaluate({}, None, None) is False
    assert ev.evaluate({}, "", None) is False
    assert ev.evaluate({}, "   ", None) is False
    assert ev.evaluate({}, "0", None) is True
    assert ev.evaluate({}, "Soat", None) is True
