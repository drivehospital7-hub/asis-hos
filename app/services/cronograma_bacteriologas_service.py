"""Servicio CRUD para cronograma de bacteriólogas."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _get_filepath(mes: int, anio: int) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"cronograma_bacteriologas_{anio}_{mes:02d}.json"


def get_cronograma(mes: int | None = None, anio: int | None = None) -> dict:
    now = datetime.now()
    mes = mes or now.month
    anio = anio or now.year
    filepath = _get_filepath(mes, anio)
    if not filepath.exists():
        return {"mes": mes, "anio": anio, "dias": []}
    return json.loads(filepath.read_text(encoding="utf-8"))


def save_cronograma(mes: int, anio: int, data: dict) -> dict:
    filepath = _get_filepath(mes, anio)
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Cronograma guardado: %s", filepath)
    return data


def get_turno_del_dia(mes: int | None = None, anio: int | None = None, dia: int | None = None) -> list[dict]:
    now = datetime.now()
    mes = mes or now.month
    anio = anio or now.year
    dia = dia or now.day
    cronograma = get_cronograma(mes, anio)
    for dia_data in cronograma.get("dias", []):
        if dia_data.get("dia") == dia:
            en_turno = []
            for nombre, codigo in dia_data.get("turnos", {}).items():
                codigo_up = codigo.upper().strip() if codigo else ""
                if "CE" in codigo_up or "PYM" in codigo_up:
                    en_turno.append({"nombre": nombre, "codigo": codigo})
            return en_turno
    return []
