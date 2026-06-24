"""EvidenceCollector — immutable batch insert of evaluation evidence.

Collects evidence records in-memory and flushes them in a single batch insert
using session.add_all() + session.flush(). No UPDATE/DELETE paths.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from app.models import Evidencia

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EvidenceCollector:
    """Collects evidence records during evaluation and flushes in batch.

    Usage:
        collector = EvidenceCollector()
        for row in rows:
            result = evaluate(...)
            collector.record(...)
        collector.flush_batch(session)  # single batch insert
    """

    def __init__(self) -> None:
        self._buffer: list[Evidencia] = []

    def record(
        self,
        regla_id: int,
        regla_version: int,
        dominio: str,
        factura: str,
        outcome: str,
        arbol_evaluado: Any,
        snapshot_fila: dict[str, Any],
        param_config_id: int | None = None,
        snapshot_referencia: dict[str, Any] | None = None,
        error_mensaje: str | None = None,
    ) -> None:
        """Add an evidence record to the in-memory buffer.

        Args:
            regla_id: Rule ID.
            regla_version: Rule version used.
            dominio: Domain (e.g., 'odontologia').
            factura: Invoice identifier.
            outcome: MATCH, NO_MATCH, or ERROR.
            arbol_evaluado: Per-node evaluation trace (list of dicts).
            snapshot_fila: Row data at evaluation time.
            param_config_id: Which parameter config produced this (0=default).
            snapshot_referencia: Reference data snapshot.
            error_mensaje: Error message if outcome=ERROR.
        """
        evidence = Evidencia(
            regla_id=regla_id,
            regla_version=regla_version,
            dominio=dominio,
            factura=factura,
            param_config_id=param_config_id,
            outcome=outcome,
            arbol_evaluado=arbol_evaluado,
            snapshot_fila=snapshot_fila,
            snapshot_referencia=snapshot_referencia,
            error_mensaje=error_mensaje,
        )
        self._buffer.append(evidence)

    def flush_batch(self, session: "Session") -> list[Evidencia]:
        """Persist all buffered evidence records in a single batch.

        Uses session.add_all() + flush() for efficiency. No commit — caller owns
        the transaction boundary.

        Returns:
            List of flushed Evidencia objects with IDs populated (for creating
            ResultadoAuditoria links).
        """
        if not self._buffer:
            return []

        logger.info("Flushing %d evidence records", len(self._buffer))
        session.add_all(self._buffer)
        session.flush()
        result = list(self._buffer)  # Capture with IDs populated after flush
        self._buffer.clear()
        return result
