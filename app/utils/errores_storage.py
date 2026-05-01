"""Persistencia JSON para control de errores de urgencias."""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
ERRORES_FILE = DATA_DIR / "control_errores.json"


def _leer_datos() -> dict[str, list[dict[str, Any]]]:
    """Leer datos del archivo JSON."""
    if not ERRORES_FILE.exists():
        return {"errores": []}

    try:
        with open(ERRORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Error leyendo archivo de errores")
        return {"errores": []}


def _escribir_datos(data: dict[str, list[dict[str, Any]]]) -> None:
    """Escribir datos al archivo JSON."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(ERRORES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Error escribiendo archivo de errores")
        raise


def listar_errores(
    tipo_error: str | None = None,
    estado: str | None = None,
    responsable: str | None = None,
) -> list[dict[str, Any]]:
    """Listar errores con filtros opcionales."""
    data = _leer_datos()
    errores = data.get("errores", [])

    if tipo_error:
        errores = [e for e in errores if e.get("tipo_error") == tipo_error]
    if estado:
        errores = [e for e in errores if e.get("estado") == estado]
    if responsable:
        errores = [e for e in errores if e.get("responsable") == responsable]

    # Ordenar por fecha de creación (más reciente primero)
    errores = sorted(errores, key=lambda e: e.get("creado_en", ""), reverse=True)

    return errores


def crear_error(
    tipo_error: str,
    factura: str,
    observacion: str,
    estado: str,
    responsable: str,
) -> dict[str, Any]:
    """Crear un nuevo error."""
    data = _leer_datos()

    nuevo_error = {
        "id": str(uuid.uuid4()),
        "tipo_error": tipo_error,
        "factura": factura,
        "observacion": observacion,
        "estado": estado,
        "responsable": responsable,
        "creado_en": datetime.now().isoformat(),
        "actualizado_en": datetime.now().isoformat(),
    }

    data.setdefault("errores", []).append(nuevo_error)
    _escribir_datos(data)

    logger.info("Error creado: %s", nuevo_error["id"])
    return nuevo_error


def obtener_error(error_id: str) -> dict[str, Any] | None:
    """Obtener un error por ID."""
    data = _leer_datos()
    for error in data.get("errores", []):
        if error.get("id") == error_id:
            return error
    return None


def actualizar_error(
    error_id: str,
    tipo_error: str | None = None,
    factura: str | None = None,
    observacion: str | None = None,
    estado: str | None = None,
    responsable: str | None = None,
) -> dict[str, Any] | None:
    """Actualizar un error existente."""
    data = _leer_datos()

    for error in data.get("errores", []):
        if error.get("id") == error_id:
            if tipo_error is not None:
                error["tipo_error"] = tipo_error
            if factura is not None:
                error["factura"] = factura
            if observacion is not None:
                error["observacion"] = observacion
            if estado is not None:
                error["estado"] = estado
            if responsable is not None:
                error["responsable"] = responsable

            error["actualizado_en"] = datetime.now().isoformat()

            _escribir_datos(data)
            logger.info("Error actualizado: %s", error_id)
            return error

    return None


def eliminar_error(error_id: str) -> bool:
    """Eliminar un error por ID."""
    data = _leer_datos()

    errores_original = data.get("errores", [])
    errores_nuevos = [e for e in errores_original if e.get("id") != error_id]

    if len(errores_nuevos) < len(errores_original):
        data["errores"] = errores_nuevos
        _escribir_datos(data)
        logger.info("Error eliminado: %s", error_id)
        return True

    return False