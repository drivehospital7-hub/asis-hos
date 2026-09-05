"""RowStore — build list[dict] from 2D row data for facts-first evaluation.

Converts the 1-based 2D list (from ``_SimpleSheet``) into a list of dicts
using column indices, so that all rules can access row data via
snake_case keys instead of openpyxl ``cell()`` lookups.
"""

from __future__ import annotations

from typing import Any


def build_row_store(
    rows_2d: list[list[Any]], indices: dict[str, int | None]
) -> list[dict[str, Any]]:
    """Convert 1-based 2D list to ``list[dict]`` using column index map.

    Only includes keys with non-None indices. Data starts at row 2
    (row 0 and row 1 are unused/header respectively in the 1-based format).

    Args:
        rows_2d: 1-based 2D list where ``rows_2d[0]`` is unused and
                 ``rows_2d[1]`` is the header row.
        indices: Column name → 0-based column index (or ``None`` to skip).

    Returns:
        List of dicts, one per data row (row 2+).
    """
    result: list[dict[str, Any]] = []

    # Build (key, col_index) pairs for non-None indices only
    active_columns: list[tuple[str, int]] = []
    for key, idx in indices.items():
        if idx is not None:
            active_columns.append((key, idx))

    # Data starts at row 2 (1-based); row 0 is unused, row 1 is header
    for row in range(2, len(rows_2d)):
        row_dict: dict[str, Any] = {}
        for key, col_idx in active_columns:
            row_dict[key] = rows_2d[row][col_idx + 1]
        result.append(row_dict)

    return result


def row_from_dict(
    row: dict[str, Any], indices: dict[str, int | None]
) -> dict[str, Any]:
    """Identity function for dict rows.

    Kept for interface consistency so the engine can call either
    ``row_from_dict`` or ``build_row_store`` interchangeably.

    Args:
        row: A dict row.
        indices: Column index map (unused — kept for interface consistency).

    Returns:
        The same dict row, unchanged.
    """
    return row
