"""ConditionEvaluator — recursive AND/OR/NOT tree evaluator with short-circuit.

Builds a condition tree from flat DB rows, then evaluates it depth-first against
an EvaluationContext using the evaluator and provider registries.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from app.services.engine.evaluators import get_evaluator
from app.services.engine.providers import get_provider

if TYPE_CHECKING:
    from app.services.engine.context import EvaluationContext

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluates a condition tree (built from condiciones rows) against a context.

    Usage:
        evaluator = ConditionEvaluator()
        tree = evaluator.build_tree(conditions_list)  # flat list → nested tree
        result = evaluator.evaluate(tree, context)     # recursive evaluation
    """

    def build_tree(self, conditions: list[dict]) -> dict | None:
        """Build a nested condition tree from a flat list of condition dicts.

        Each dict must have: id, padre_id, tipo, operador, fuente_datos, valor_esperado.
        Returns the root node dict with _children key for composites.
        """
        if not conditions:
            return None

        # Index by id for fast lookup
        by_id: dict[int, dict] = {}
        children_map: dict[int | None, list[dict]] = {}

        for c in conditions:
            node = dict(c)  # shallow copy to avoid mutating input
            pid = node.get("padre_id")
            children_map.setdefault(pid, []).append(node)
            by_id[node["id"]] = node

        # Link children
        for pid, kids in children_map.items():
            if pid is not None and pid in by_id:
                # Sort by orden
                kids.sort(key=lambda n: n.get("orden", 0))
                by_id[pid]["_children"] = kids

        # Find root (padre_id is None)
        roots = children_map.get(None, [])
        if not roots:
            return None
        if len(roots) > 1:
            logger.warning("Multiple root conditions found (%d), using first", len(roots))

        return roots[0]

    def evaluate(
        self,
        node: dict,
        context: "EvaluationContext",
    ) -> dict[str, Any]:
        """Recursively evaluate a condition node against the context.

        Returns:
            dict with keys: outcome (bool), trace (dict), error (str|None).
        """
        tipo = node.get("tipo", "")
        operador = node.get("operador", "")

        if tipo == "composite":
            return self._evaluate_composite(node, context)
        else:
            return self._evaluate_atomic(node, context)

    # ── Private ──────────────────────────────────────────────────────────

    def _evaluate_composite(
        self,
        node: dict,
        context: "EvaluationContext",
    ) -> dict[str, Any]:
        """Evaluate AND/OR/NOT composite node with short-circuit."""
        operador = (node.get("operador") or "").upper()
        children = node.get("_children", [])

        if operador == "AND":
            return self._eval_and(children, context)
        elif operador == "OR":
            return self._eval_or(children, context)
        elif operador == "NOT":
            return self._eval_not(children, context)
        else:
            logger.warning("Unknown composite operator: %s", operador)
            return {
                "outcome": False,
                "trace": {"tipo": "composite", "operador": operador, "_children": []},
                "error": f"Unknown composite operator: {operador}",
            }

    def _eval_and(
        self,
        children: list[dict],
        context: "EvaluationContext",
    ) -> dict[str, Any]:
        """AND: true only if ALL children are true. Short-circuits on first false."""
        child_results = []
        for child in children:
            result = self.evaluate(child, context)
            child_results.append(result.get("trace", result))
            if not result.get("outcome"):
                # Short-circuit: mark remaining children as not evaluated
                for remaining in children[len(child_results):]:
                    child_results.append({"outcome": None, "_skipped": True})
                return {
                    "outcome": False,
                    "trace": {
                        "tipo": "composite",
                        "operador": "AND",
                        "outcome": False,
                        "_children": child_results,
                    },
                }
        return {
            "outcome": True,
            "trace": {
                "tipo": "composite",
                "operador": "AND",
                "outcome": True,
                "_children": child_results,
            },
        }

    def _eval_or(
        self,
        children: list[dict],
        context: "EvaluationContext",
    ) -> dict[str, Any]:
        """OR: true if ANY child is true. Short-circuits on first true."""
        child_results = []
        for child in children:
            result = self.evaluate(child, context)
            child_results.append(result.get("trace", result))
            if result.get("outcome"):
                # Short-circuit
                for remaining in children[len(child_results):]:
                    child_results.append({"outcome": None, "_skipped": True})
                return {
                    "outcome": True,
                    "trace": {
                        "tipo": "composite",
                        "operador": "OR",
                        "outcome": True,
                        "_children": child_results,
                    },
                }
        return {
            "outcome": False,
            "trace": {
                "tipo": "composite",
                "operador": "OR",
                "outcome": False,
                "_children": child_results,
            },
        }

    def _eval_not(
        self,
        children: list[dict],
        context: "EvaluationContext",
    ) -> dict[str, Any]:
        """NOT: inverts the single child's result."""
        if not children:
            return {
                "outcome": False,
                "trace": {
                    "tipo": "composite",
                    "operador": "NOT",
                    "outcome": False,
                    "_children": [],
                },
                "error": "NOT node has no children",
            }
        child = children[0]
        result = self.evaluate(child, context)
        inverted = not result.get("outcome")
        return {
            "outcome": inverted,
            "trace": {
                "tipo": "composite",
                "operador": "NOT",
                "outcome": inverted,
                "_children": [result.get("trace", result)],
            },
        }

    def _evaluate_atomic(
        self,
        node: dict,
        context: "EvaluationContext",
    ) -> dict[str, Any]:
        """Evaluate an atomic condition: resolve value, look up evaluator, compare."""
        operador = node.get("operador", "")
        fuente = node.get("fuente_datos", "")
        valor_esperado = node.get("valor_esperado")

        # Resolve the actual value from context
        provider = get_provider(fuente) if fuente else None
        if provider is None and fuente:
            logger.warning("No provider for data path: %s", fuente)
            return {
                "outcome": False,
                "trace": {
                    "tipo": "atomic",
                    "operador": operador,
                    "fuente_datos": fuente,
                    "outcome": False,
                },
                "error": f"No provider for data path: {fuente}",
            }

        row_value = provider.resolve(fuente, context) if provider else None

        # Look up evaluator
        evaluator = get_evaluator(operador)
        if evaluator is None:
            logger.error("Unknown evaluator operator: %s", operador)
            return {
                "outcome": False,
                "trace": {
                    "tipo": "atomic",
                    "operador": operador,
                    "fuente_datos": fuente,
                    "valor_real": row_value,
                    "valor_esperado": valor_esperado,
                    "outcome": False,
                },
                "error": f"Unknown evaluator operator: {operador}",
            }

        try:
            outcome = evaluator.evaluate(node, row_value, valor_esperado, context=context)
        except Exception as exc:
            logger.exception("Evaluator %s failed for value=%s, expected=%s", operador, row_value, valor_esperado)
            return {
                "outcome": False,
                "trace": {
                    "tipo": "atomic",
                    "operador": operador,
                    "fuente_datos": fuente,
                    "valor_real": row_value,
                    "valor_esperado": valor_esperado,
                    "outcome": False,
                },
                "error": str(exc),
            }

        return {
            "outcome": outcome,
            "trace": {
                "tipo": "atomic",
                "operador": operador,
                "fuente_datos": fuente,
                "valor_real": str(row_value) if row_value is not None else None,
                "valor_esperado": str(valor_esperado) if valor_esperado is not None else None,
                "outcome": outcome,
            },
        }
