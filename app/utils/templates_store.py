"""Almacenamiento local de plantillas de permisos (JSON, sin DB).

Provee persistencia entre sesiones via archivo instance/templates.json.
Si el archivo no existe, se crea con las plantillas por defecto al
primer intento de lectura.
"""

import json
import logging
import os
from pathlib import Path

from app.constants.base import ALLOWED_PERMISOS, DEFAULT_TEMPLATES

logger = logging.getLogger(__name__)

TEMPLATES_FILE = Path("instance") / "templates.json"

# Nombres de plantillas por defecto (no se pueden eliminar)
DEFAULT_TEMPLATES_NAMES: frozenset = frozenset(
    {t["nombre"] for t in DEFAULT_TEMPLATES}
)


def _load_templates() -> list[dict]:
    """Carga plantillas desde el archivo JSON.

    Si el archivo no existe, crea las plantillas por defecto.
    Si el archivo está corrupto, retorna lista vacía (logged error).
    """
    if not TEMPLATES_FILE.exists():
        _ensure_default_templates()

    try:
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Error leyendo %s: %s", TEMPLATES_FILE, e)
        return []


def _save_templates(templates: list[dict]) -> None:
    """Guarda plantillas al archivo JSON (escritura atómica).

    Escribe a un archivo temporal y luego usa os.replace() para
    reemplazar el archivo original. Esto previene corrupción
    por crash durante la escritura.
    """
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = TEMPLATES_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)
    os.replace(tmp, TEMPLATES_FILE)


def _ensure_default_templates() -> None:
    """Crea el archivo con las plantillas por defecto."""
    _save_templates(DEFAULT_TEMPLATES)
    logger.info(
        "Archivo %s creado con %d plantillas por defecto",
        TEMPLATES_FILE,
        len(DEFAULT_TEMPLATES),
    )


def list_templates() -> list[dict]:
    """Retorna todas las plantillas (copia de cada una, sin leak de estado interno)."""
    templates = _load_templates()
    return [dict(t) for t in templates]


def get_template(nombre: str) -> dict | None:
    """Retorna una plantilla por su nombre o None si no existe."""
    templates = _load_templates()
    for t in templates:
        if t["nombre"] == nombre:
            return dict(t)
    return None


def create_template(nombre: str, descripcion: str, permisos: list) -> tuple:
    """Crea una nueva plantilla.

    Returns:
        (True, mensaje) si se creó, (False, mensaje) si ya existe o hay error.
    """
    templates = _load_templates()

    if any(t["nombre"] == nombre for t in templates):
        return False, f"La plantilla '{nombre}' ya existe"

    # Validar permisos
    for p in permisos:
        if p not in ALLOWED_PERMISOS:
            return False, f"Permiso inválido: {p}"

    templates.append(
        {
            "nombre": nombre,
            "descripcion": descripcion,
            "permisos": permisos,
        }
    )
    _save_templates(templates)
    return True, f"Plantilla '{nombre}' creada"


def update_template(nombre: str, updates: dict) -> tuple:
    """Actualiza parcialmente una plantilla.

    Los campos en `updates` son opcionales:
      - nombre: str — nuevo nombre.
      - descripcion: str — nueva descripción.
      - permisos: list — nuevos permisos (cada uno debe estar en ALLOWED_PERMISOS).

    Returns:
        (True, mensaje) si se actualizó, (False, mensaje) si hay error.
    """
    templates = _load_templates()
    target = None
    for t in templates:
        if t["nombre"] == nombre:
            target = t
            break

    if target is None:
        return False, f"Plantilla '{nombre}' no encontrada"

    updated = dict(target)

    if "nombre" in updates:
        updated["nombre"] = updates["nombre"]

    if "descripcion" in updates:
        updated["descripcion"] = updates["descripcion"]

    if "permisos" in updates:
        nuevos_permisos = updates["permisos"]
        for p in nuevos_permisos:
            if p not in ALLOWED_PERMISOS:
                return False, f"Permiso inválido: {p}"
        updated["permisos"] = nuevos_permisos

    # Reemplazar en la lista
    for i, t in enumerate(templates):
        if t["nombre"] == nombre:
            templates[i] = updated
            break

    _save_templates(templates)
    return True, f"Plantilla '{nombre}' actualizada"


def delete_template(nombre: str) -> tuple:
    """Elimina una plantilla.

    Las plantillas por defecto (odontologia, urgencias, auditor) NO pueden
    ser eliminadas.

    Returns:
        (True, mensaje) si se eliminó, (False, mensaje) si no existe
        o si es una plantilla por defecto.
    """
    if nombre in DEFAULT_TEMPLATES_NAMES:
        return False, f"No se puede eliminar la plantilla por defecto '{nombre}'"

    templates = _load_templates()
    filtered = [t for t in templates if t["nombre"] != nombre]
    if len(filtered) == len(templates):
        return False, f"Plantilla '{nombre}' no encontrada"
    _save_templates(filtered)
    return True, f"Plantilla '{nombre}' eliminada"
