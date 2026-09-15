"""EvaluationContext — data carrier for rule evaluation.

Carries all data needed to evaluate a rule against a single row:
invoice data, patient data, reference data, column indices, and DB session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationContext:
    """Immutable-ish context passed to every evaluator during rule execution.

    Fields:
        invoice_data: Dict of invoice row values (e.g., vlr_subsidiado, convenio).
        patient_data: Dict of patient-level data (e.g., edad, tipo_doc).
        reference_data: Dict of reference/lookup data (e.g., contracts, procedures).
        indices: Column index mapping (e.g., {"numero_factura": 0}).
        session: SQLAlchemy session for DB lookups (e.g., exists_in_db evaluator).
    """

    invoice_data: dict[str, Any] | None = None
    patient_data: dict[str, Any] | None = None
    reference_data: dict[str, Any] | None = None
    indices: dict[str, int | None] | None = None
    session: Any = None
    group_rows: list[dict[str, Any]] | None = None
    """Group-mode payload: per-row dicts of the factura group.

    None (default) = row mode. Set (even empty) = group mode: providers
    resolve row-written sources against the group (first valid date pair,
    first-row scalars, on-demand collect_set). Row path untouched.
    """
    params: dict[str, Any] | None = None
    """Rule.parametros[0]: operator config forwarded by the engine.

    None (default) = no overrides; evaluators fall back to their defaults.
    """
