"""Simulator service — dry-run of the real pipeline with a rule subset.

Uploads an Excel, runs the SAME detection pipeline as POST /procesar
(area unificada, ALL rows), and returns the SAME shaped payload, optionally
filtered to a selected set of rule ids.

The simulator NEVER persists evidence/audit rows: evaluation runs inside
``domain_detection.simulation_scope``. No legacy Python detectors are used.
"""

from __future__ import annotations

import logging
from typing import Any

from app.constants import AREA_UNIFICADA
from app.services.engine.domain_detection import simulation_scope
from app.services.exporter import detect_problems_only
from app.services.procesar_response import build_procesar_response_data
from app.utils import procesar_export_store as export_store
from app.utils.input_data import cleanup_temp_excel, save_temp_excel

logger = logging.getLogger(__name__)


def _parse_regla_id(value: object) -> int | None:
    """Parse normalized-row regla ('#33') to int id. None when absent."""
    text = str(value or "").strip().lstrip("#").strip()
    return int(text) if text.isdigit() else None


def simulate(
    db_session,
    file_storage,
    rule_ids: list[int] | set[int] | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Run a dry-run simulation of /procesar restricted to selected rules.

    Args:
        db_session: Unused (kept for backward compatibility). Engine sessions
            are owned by each detect_all orchestrator via SessionManager.
        file_storage: werkzeug FileStorage (uploaded Excel).
        rule_ids: Rule ids to evaluate. None or empty = all enabled rules.
        sheet_name: Excel sheet name (None = active sheet).

    Returns:
        /procesar-shaped payload (errores, total_errores, tipos_procesados,
        columnas, export_id) plus ``reglas_aplicadas`` (sorted ids, empty
        means "all enabled rules").

    Raises:
        ValueError: If the file format is invalid or required columns
            are missing.
    """
    del db_session  # engine owns its sessions; simulator never persists
    selected: set[int] | None = (
        {int(r) for r in rule_ids} if rule_ids else None
    )

    temp_path, error = save_temp_excel(file_storage)
    if error or temp_path is None:
        raise ValueError(error or "No se pudo guardar el archivo Excel")
    filename = str(temp_path)

    try:
        with simulation_scope(selected):
            export_result, _status_code = detect_problems_only(
                filename=filename,
                sheet_name=sheet_name,
                area=AREA_UNIFICADA,
            )
    finally:
        cleanup_temp_excel(temp_path)

    if export_result["status"] != "success":
        raise ValueError(
            "; ".join(export_result.get("errors", ["Error desconocido"]))
        )

    problemas_data = export_result["data"].get("problemas", {})
    missing_columns = problemas_data.get("missing_columns", [])
    if missing_columns:
        raise ValueError(
            "Columnas no encontradas en el Excel: "
            + ", ".join(missing_columns)
            + ". Verifica que el archivo tenga los encabezados correctos."
        )

    problemas_dict = problemas_data.get("problemas", {})
    normalized_rows = problemas_dict.get("normalizados", [])

    # Filter to the selected rules BEFORE display dedup, so winners are
    # chosen among the selected rules only (same as if only those rules
    # existed). Normalized rows carry regla as "#<id>".
    if selected is not None:
        before = len(normalized_rows)
        normalized_rows = [
            row for row in normalized_rows
            if _parse_regla_id(row.get("regla")) in selected
        ]
        logger.info(
            "Simulator rule filter: %d -> %d rows (%d rules selected)",
            before, len(normalized_rows), len(selected),
        )

    response_data, deduped_items = build_procesar_response_data(
        normalized_rows=normalized_rows,
        problemas_data=problemas_data,
        tipos_procesados_fallback=export_result["data"].get("tipos_procesados", []),
    )

    # Same best-effort export cache as /procesar: the simulator result
    # downloads through GET /procesar/export?id= (admin-only anyway).
    try:
        export_id: str | None = export_store.put(deduped_items)
    except Exception:
        logger.exception("[BACK][ERROR] Simulator export cache write failed")
        export_id = None
    if export_id is not None:
        response_data["export_id"] = export_id

    response_data["reglas_aplicadas"] = sorted(selected) if selected else []
    return response_data
