"""Unit tests for branch tracking (rama N del editor)."""

from app.services.engine.condition_evaluator import ConditionEvaluator


def _ctx(data):
    from app.services.engine.context import EvaluationContext
    return EvaluationContext(invoice_data=data)


def _or_tree():
    ev = ConditionEvaluator()
    conds = [
        {"id": 1, "regla_id": 1, "padre_id": None, "tipo": "composite",
         "operador": "OR", "fuente_datos": None, "valor_esperado": None, "orden": 0},
        {"id": 2, "regla_id": 1, "padre_id": 1, "tipo": "atomic",
         "operador": "eq", "fuente_datos": "invoice.a", "valor_esperado": "X", "orden": 0},
        {"id": 3, "regla_id": 1, "padre_id": 1, "tipo": "atomic",
         "operador": "eq", "fuente_datos": "invoice.b", "valor_esperado": "Y", "orden": 1},
    ]
    return ev, ev.build_tree(conds)


def test_or_reports_matching_branch():
    ev, tree = _or_tree()
    res, idx = ev.evaluate_root(tree, _ctx({"a": "no", "b": "Y"}))
    assert res["outcome"] is True and idx == 1
    assert ConditionEvaluator.branch_info(tree, idx) == (2, 3)


def test_or_no_match_reports_none():
    ev, tree = _or_tree()
    res, idx = ev.evaluate_root(tree, _ctx({"a": "no", "b": "no"}))
    assert res["outcome"] is False and idx is None
    assert ConditionEvaluator.branch_info(tree, idx) == (1, 2)


def test_atomic_root_is_rama_1():
    ev = ConditionEvaluator()
    conds = [
        {"id": 9, "regla_id": 1, "padre_id": None, "tipo": "atomic",
         "operador": "eq", "fuente_datos": "invoice.a", "valor_esperado": "X", "orden": 0},
    ]
    tree = ev.build_tree(conds)
    res, idx = ev.evaluate_root(tree, _ctx({"a": "X"}))
    assert res["outcome"] is True and idx is None
    assert ConditionEvaluator.branch_info(tree, idx) == (1, 9)


def test_and_match_reports_first_branch():
    ev = ConditionEvaluator()
    conds = [
        {"id": 1, "regla_id": 1, "padre_id": None, "tipo": "composite",
         "operador": "AND", "fuente_datos": None, "valor_esperado": None, "orden": 0},
        {"id": 2, "regla_id": 1, "padre_id": 1, "tipo": "atomic",
         "operador": "eq", "fuente_datos": "invoice.a", "valor_esperado": "X", "orden": 0},
        {"id": 3, "regla_id": 1, "padre_id": 1, "tipo": "atomic",
         "operador": "eq", "fuente_datos": "invoice.b", "valor_esperado": "Y", "orden": 1},
    ]
    tree = ev.build_tree(conds)
    res, idx = ev.evaluate_root(tree, _ctx({"a": "X", "b": "Y"}))
    assert res["outcome"] is True and idx == 0
    res, idx = ev.evaluate_root(tree, _ctx({"a": "X", "b": "no"}))
    assert res["outcome"] is False and idx == 1
    assert ConditionEvaluator.branch_info(tree, idx) == (2, 3)


def test_branch_index_from_trace_or():
    ev, tree = _or_tree()
    res = ev.evaluate(tree, _ctx({"a": "no", "b": "Y"}), collect_trace=True)
    assert res["outcome"] is True
    assert ConditionEvaluator.branch_index_from_trace(res.get("trace")) == 1
