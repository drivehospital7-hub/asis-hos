"""Servicio para guardar y cargar el horario de abiertas urgencias."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HORARIO_FILE = Path(__file__).parent.parent / "data" / "horario_abiertas_urgencias.json"


def _ensure_data_dir() -> None:
    """Asegura que el directorio data exista."""
    HORARIO_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_horario() -> dict[str, Any]:
    """Obtener el horario guardado.

    Returns:
        Diccionario con el horario, o dict vacío si no hay datos.
    """
    if not HORARIO_FILE.exists():
        return {"status": "success", "data": {"horario": None, "total_dias": 0}, "errors": []}

    try:
        with open(HORARIO_FILE, encoding="utf-8") as f:
            horario = json.load(f)

        logger.info("Horario cargado: %d días", len(horario.get("dias", [])))
        return {
            "status": "success",
            "data": {
                "horario": horario,
                "total_dias": len(horario.get("dias", [])),
            },
            "errors": [],
        }
    except (json.JSONDecodeError, OSError) as e:
        logger.exception("Error leyendo horario guardado")
        return {"status": "error", "data": {}, "errors": [f"Error leyendo horario: {e}"]}


def save_horario(dias: list[dict[str, Any]]) -> dict[str, Any]:
    """Guardar el horario.

    Args:
        dias: Lista de dicts con dia, manana, tarde, noche.

    Returns:
        Respuesta estándar con status/data/errors.
    """
    if not dias:
        return {"status": "error", "data": {}, "errors": ["No hay datos para guardar"]}

    horario = {
        "dias": dias,
        "total_dias": len(dias),
        "columnas": [
            "07:00 AM - 01:00 PM",
            "01:00 PM - 07:00 PM",
            "07:00 PM - 07:00 AM",
        ],
    }

    try:
        _ensure_data_dir()
        with open(HORARIO_FILE, "w", encoding="utf-8") as f:
            json.dump(horario, f, indent=2, ensure_ascii=False)

        logger.info("Horario guardado: %d días", len(dias))
        return {
            "status": "success",
            "data": {
                "horario": horario,
                "total_dias": len(dias),
            },
            "errors": [],
        }
    except OSError as e:
        logger.exception("Error guardando horario")
        return {"status": "error", "data": {}, "errors": [f"Error guardando horario: {e}"]}


def delete_horario() -> dict[str, Any]:
    """Eliminar el horario guardado."""
    if not HORARIO_FILE.exists():
        return {"status": "success", "data": {}, "errors": []}

    try:
        HORARIO_FILE.unlink()
        logger.info("Horario eliminado")
        return {"status": "success", "data": {}, "errors": []}
    except OSError as e:
        logger.exception("Error eliminando horario")
        return {"status": "error", "data": {}, "errors": [f"Error eliminando horario: {e}"]}
