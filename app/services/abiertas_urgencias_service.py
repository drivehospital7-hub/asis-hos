"""Servicio para guardar y cargar el horario de abiertas urgencias (file-per-month)."""

import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HORARIO_FILE = Path(__file__).parent.parent / "data" / "horario_abiertas_urgencias.json"
HORARIOS_DIR = Path(__file__).parent.parent / "data" / "horarios"

COLUMNAS = [
    "07:00 AM - 01:00 PM",
    "01:00 PM - 07:00 PM",
    "07:00 PM - 07:00 AM",
]


def _ensure_data_dir() -> None:
    """Asegura que el directorio de horarios exista."""
    HORARIOS_DIR.mkdir(parents=True, exist_ok=True)
    HORARIO_FILE.parent.mkdir(parents=True, exist_ok=True)


def _mes_actual() -> dict[str, int]:
    """Devuelve el mes y año actual."""
    hoy = date.today()
    return {"mes": hoy.month, "anio": hoy.year}


def _horario_path(mes: int, anio: int) -> Path:
    """Return sharded path for given mes/anio, validating ranges."""
    if not isinstance(mes, int) or not 1 <= mes <= 12:
        raise ValueError("mes invalido")
    if not isinstance(anio, int) or not 2000 <= anio <= 2100:
        raise ValueError("anio invalido")
    _ensure_data_dir()
    return HORARIOS_DIR / f"abiertas_urgencias_{anio:04d}-{mes:02d}.json"


def _migrate_legacy_if_needed() -> bool:
    """Copy legacy single file to sharded location if sharded missing."""
    if not HORARIO_FILE.exists():
        return False
    try:
        with open(HORARIO_FILE, encoding="utf-8") as f:
            legacy = json.load(f)
    except Exception:
        logger.exception("[BACK][ERROR] Error leyendo legacy horario para migracion")
        return False
    mes = legacy.get("mes")
    anio = legacy.get("anio")
    if not isinstance(mes, int) or not isinstance(anio, int):
        return False
    try:
        dest = _horario_path(mes, anio)
    except ValueError:
        return False
    if dest.exists():
        return False
    dias = legacy.get("dias", [])
    horario = {
        "mes": mes,
        "anio": anio,
        "dias": dias,
        "total_dias": len(dias) if isinstance(dias, list) else 0,
        "columnas": legacy.get("columnas", COLUMNAS),
    }
    try:
        _ensure_data_dir()
        tmp = dest.with_name(dest.name + f".tmp.{os.getpid()}")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(horario, f, indent=2, ensure_ascii=False)
        tmp.replace(dest)
        logger.info("[BACK] Migrating legacy horario %s/%s -> horarios/%s", mes, anio, dest.name)
        return True
    except OSError:
        logger.exception("[BACK][ERROR] Error migrando legacy horario")
        return False


def list_horarios() -> dict[str, Any]:
    """List available months as YYYY-MM sorted ascending."""
    try:
        _migrate_legacy_if_needed()
        if not HORARIOS_DIR.exists():
            return {"status": "success", "data": {"meses": []}, "errors": []}
        meses: list[str] = []
        for p in HORARIOS_DIR.glob("abiertas_urgencias_*.json"):
            stem = p.stem  # abiertas_urgencias_2026-09
            try:
                suffix = stem.replace("abiertas_urgencias_", "")
                # suffix is YYYY-MM
                year_str, month_str = suffix.split("-")
                int(year_str)
                int(month_str)
                # verify file is valid json (skip corrupted but not fatal)
                with open(p, encoding="utf-8") as f:
                    json.load(f)
                meses.append(suffix)
            except Exception as e:
                logger.warning("[BACK][ERROR] Horario corrupto ignorado: %s (%s)", p.name, e)
                continue
        meses.sort()
        return {"status": "success", "data": {"meses": meses}, "errors": []}
    except Exception as e:
        logger.exception("[BACK][ERROR] Error listando horarios")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def get_horario(mes: int | None = None, anio: int | None = None) -> dict[str, Any]:
    """Obtener el horario guardado.

    If mes/anio are None -> legacy compat: return current month.
    """
    # Legacy compat: no params -> current month
    if mes is None and anio is None:
        _migrate_legacy_if_needed()
        actual = _mes_actual()
        mes, anio = actual["mes"], actual["anio"]
        # Try sharded file first
        try:
            path = _horario_path(mes, anio)
        except ValueError as e:
            return {"status": "error", "data": {}, "errors": [str(e)]}
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    horario = json.load(f)
                logger.info("[BACK] Horario cargado: %d dias para %s/%s", len(horario.get("dias", [])), mes, anio)
                return {"status": "success", "data": {"horario": horario, "total_dias": len(horario.get("dias", []))}, "errors": []}
            except (json.JSONDecodeError, OSError) as e:
                logger.exception("[BACK][ERROR] Error leyendo horario guardado")
                return {"status": "error", "data": {}, "errors": [f"Error leyendo horario: {e}"]}
        # Fallback to legacy file if sharded missing
        if not HORARIO_FILE.exists():
            return {"status": "success", "data": {"horario": None, "total_dias": 0}, "errors": []}
        try:
            with open(HORARIO_FILE, encoding="utf-8") as f:
                horario = json.load(f)
            mes_guardado = horario.get("mes")
            anio_guardado = horario.get("anio")
            if mes_guardado != mes or anio_guardado != anio:
                logger.info("[BACK] Horario ignorado: pertenece a %s/%s, mes actual %s/%s", mes_guardado, anio_guardado, mes, anio)
                if mes_guardado is not None:
                    return {"status": "success", "data": {"horario": None, "total_dias": 0}, "errors": []}
            logger.info("[BACK] Horario cargado: %d dias", len(horario.get("dias", [])))
            return {"status": "success", "data": {"horario": horario, "total_dias": len(horario.get("dias", []))}, "errors": []}
        except (json.JSONDecodeError, OSError) as e:
            logger.exception("[BACK][ERROR] Error leyendo horario guardado")
            return {"status": "error", "data": {}, "errors": [f"Error leyendo horario: {e}"]}

    # Explicit mes/anio
    try:
        if not isinstance(mes, int) or not isinstance(anio, int):
            raise ValueError("mes invalido")
        path = _horario_path(mes, anio)
    except ValueError as e:
        return {"status": "error", "data": {}, "errors": [str(e)]}
    if not path.exists():
        return {"status": "success", "data": {"horario": None, "total_dias": 0}, "errors": []}
    try:
        with open(path, encoding="utf-8") as f:
            horario = json.load(f)
        logger.info("[BACK] Horario cargado: %d dias para %s/%s", len(horario.get("dias", [])), mes, anio)
        return {"status": "success", "data": {"horario": horario, "total_dias": len(horario.get("dias", []))}, "errors": []}
    except (json.JSONDecodeError, OSError) as e:
        logger.exception("[BACK][ERROR] Error leyendo horario guardado")
        return {"status": "error", "data": {}, "errors": [f"Error leyendo horario: {e}"]}


def save_horario(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Guardar el horario para un mes/anio.

    Supports:
      save_horario(mes, anio, dias)
      save_horario(dias)  legacy -> uses mes actual
      save_horario(dias=[...]) legacy
    """
    # Parse args/kwargs into mes, anio, dias
    mes: int | None = None
    anio: int | None = None
    dias: Any = None

    # kwargs explicit
    if "dias" in kwargs:
        dias = kwargs.pop("dias")
    if "mes" in kwargs:
        mes = kwargs.pop("mes")
    if "anio" in kwargs:
        anio = kwargs.pop("anio")

    # positional args
    if args:
        if len(args) == 1 and isinstance(args[0], list):
            # legacy single list
            if dias is None:
                dias = args[0]
        elif len(args) == 3:
            mes, anio, dias = args  # type: ignore
        elif len(args) == 1 and dias is None:
            # mes is list legacy? already handled
            dias = args[0]
        elif len(args) == 2:
            # maybe (mes, dias) not expected; treat as error
            mes, dias = args  # type: ignore
        else:
            # fallback: first arg is dias if dias not set
            if dias is None:
                dias = args[0]

    # Legacy without mes/anio -> use current month
    if dias is not None and (mes is None or anio is None):
        # Check if dias is actually mes list and mes/anio missing -> legacy current month
        if isinstance(mes, list) and anio is None and isinstance(dias, type(None)):
            dias = mes
            actual = _mes_actual()
            mes = actual["mes"]
            anio = actual["anio"]
        elif mes is None and anio is None:
            actual = _mes_actual()
            mes = actual["mes"]
            anio = actual["anio"]
        elif mes is not None and dias is not None and anio is None and isinstance(mes, int):
            # ambiguous; treat anio as missing -> error will be raised
            pass

    # Handle case where mes is list due to save_horario([...]) with mes positional
    if isinstance(mes, list) and dias is None:
        dias = mes
        actual = _mes_actual()
        mes = actual["mes"]
        anio = actual["anio"]
    if isinstance(mes, list) and isinstance(dias, list) and anio is None:
        # mes is list but dias also list -> mes was dias
        actual = _mes_actual()
        mes = actual["mes"]
        anio = actual["anio"]

    if not dias:
        return {"status": "error", "data": {}, "errors": ["No hay datos para guardar"]}

    # Validate mes/anio
    try:
        if not isinstance(mes, int) or not isinstance(anio, int):
            raise ValueError("mes invalido")
        if not 1 <= mes <= 12:
            raise ValueError("mes invalido")
        if not 2000 <= anio <= 2100:
            raise ValueError("anio invalido")
    except ValueError as e:
        return {"status": "error", "data": {}, "errors": [str(e)]}

    # Validate dias shape (strict per T1: list of dicts with dia,manana,tarde,noche)
    if not isinstance(dias, list) or len(dias) == 0:
        return {"status": "error", "data": {}, "errors": ["No hay datos para guardar"]}
    for idx, item in enumerate(dias):
        if not isinstance(item, dict):
            return {"status": "error", "data": {}, "errors": [f"formato invalido en dia {idx}"] }
        dia_val = item.get("dia")
        if not isinstance(dia_val, int) or not 1 <= dia_val <= 31:
            return {"status": "error", "data": {}, "errors": ["dia invalido"] }
        for field in ("manana", "tarde", "noche"):
            val = item.get(field)
            if not isinstance(val, str) or not val.strip():
                return {"status": "error", "data": {}, "errors": [f"{field} invalido"] }

    horario = {
        "mes": mes,
        "anio": anio,
        "dias": dias,
        "total_dias": len(dias),
        "columnas": COLUMNAS,
    }

    try:
        dest = _horario_path(mes, anio)
        _ensure_data_dir()
        tmp = dest.with_name(dest.name + f".tmp.{os.getpid()}")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(horario, f, indent=2, ensure_ascii=False)
        tmp.replace(dest)
        logger.info("[BACK] Horario guardado: %d dias para %s/%s", len(dias), mes, anio)
        return {"status": "success", "data": {"horario": horario, "total_dias": len(dias)}, "errors": []}
    except OSError as e:
        logger.exception("[BACK][ERROR] Error guardando horario")
        return {"status": "error", "data": {}, "errors": [f"Error guardando horario: {e}"]}


def delete_horario(mes: int | None = None, anio: int | None = None) -> dict[str, Any]:
    """Eliminar el horario guardado."""
    # Legacy compat: no params -> delete current month (fallback to legacy file)
    if mes is None and anio is None:
        actual = _mes_actual()
        mes, anio = actual["mes"], actual["anio"]
        try:
            path = _horario_path(mes, anio)
        except ValueError as e:
            return {"status": "error", "data": {}, "errors": [str(e)]}
        # Try sharded first
        if path.exists():
            try:
                path.unlink()
                logger.info("[BACK] Horario eliminado %s/%s", mes, anio)
                return {"status": "success", "data": {}, "errors": []}
            except OSError as e:
                logger.exception("[BACK][ERROR] Error eliminando horario")
                return {"status": "error", "data": {}, "errors": [f"Error eliminando horario: {e}"]}
        # Fallback legacy
        if not HORARIO_FILE.exists():
            return {"status": "success", "data": {}, "errors": []}
        try:
            HORARIO_FILE.unlink()
            logger.info("[BACK] Horario eliminado")
            return {"status": "success", "data": {}, "errors": []}
        except OSError as e:
            logger.exception("[BACK][ERROR] Error eliminando horario")
            return {"status": "error", "data": {}, "errors": [f"Error eliminando horario: {e}"]}

    # Explicit mes/anio
    try:
        if not isinstance(mes, int) or not isinstance(anio, int):
            raise ValueError("mes invalido")
        path = _horario_path(mes, anio)
    except ValueError as e:
        return {"status": "error", "data": {}, "errors": [str(e)]}
    if not path.exists():
        return {"status": "success", "data": {}, "errors": []}
    try:
        path.unlink()
        logger.info("[BACK] Horario eliminado %s/%s", mes, anio)
        return {"status": "success", "data": {}, "errors": []}
    except OSError as e:
        logger.exception("[BACK][ERROR] Error eliminando horario")
        return {"status": "error", "data": {}, "errors": [f"Error eliminando horario: {e}"]}
