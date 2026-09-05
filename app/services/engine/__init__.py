"""Motor de Reglas de Auditoría — DB-Backed Rule Engine.

Replaces hardcoded Python detectors with a DB-backed rule engine.
Rules are data (versioned, parametric, domain-scoped) — not code.

Core components:
- context: EvaluationContext dataclass
- evaluators: AtomicEvaluator registry + built-in operators
- providers: ContextProvider registry + built-in data resolvers
- resolver: RuleResolver (loads active rules by domain)
- evaluator: ConditionEvaluator (recursive AND/OR/NOT tree)
- exceptions: ExceptionHandler (skip/downgrade/override)
- evidence: EvidenceCollector (immutable batch insert)
- engine: RuleEvaluationEngine (orchestrator)
- wrapper: RuleBasedDetector (legacy-compatible interface)
"""
