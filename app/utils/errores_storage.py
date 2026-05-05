"""Persistencia JSON para control de errores de urgencias."""

import json
import logging
import uuid
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Any

from app.constants import IMAGENES_DIR, IMAGENES_MAX_PER_OBSERVACION, IMAGENES_ALLOWED_TYPES, IMAGENES_MAX_SIZE_MB

logger = logging.getLogger(__name__)

# Sentinel para distinguir "no proporcionado" de "vacío"
_NOT_SET = object()

DATA_DIR = Path(__file__).parent.parent / "data"
ERRORES_FILE = DATA_DIR / "control_errores.json"
IMAGENES_PATH = DATA_DIR / "imagenes"


def _get_imagenes_dir(error_id: str) -> Path:
    """Obtener carpeta de imágenes para un error."""
    return IMAGENES_PATH / error_id


def _leer_datos() -> dict[str, list[dict[str, Any]]]:
    """Leer datos del archivo JSON."""
    if not ERRORES_FILE.exists():
        return {"errores": [], "ultima_actualizacion": None}

    try:
        with open(ERRORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Error leyendo archivo de errores")
        return {"errores": [], "ultima_actualizacion": None}


def _escribir_datos(data: dict[str, list[dict[str, Any]]]) -> None:
    """Escribir datos al archivo JSON de forma atómica (evita corrupción)."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Actualizar timestamp de última modificación
        data["ultima_actualizacion"] = datetime.now().isoformat()
        # Escritura atómica: escribir a temp, luego renombrar
        fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            Path(tmp_path).replace(ERRORES_FILE)
        except:
            # Limpiar temp file en caso de error
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except:
                pass
            raise
    except Exception as e:
        logger.exception("Error escribiendo archivo de errores")
        raise


def get_ultima_actualizacion() -> str | None:
    """Obtener timestamp de última modificación."""
    data = _leer_datos()
    return data.get("ultima_actualizacion")


def check_cambios(since: str | None) -> tuple[bool, str | None]:
    """Verificar si hubo cambios desde un timestamp.
    
    Returns:
        (hay_cambios, ultima_actualizacion)
    """
    current = get_ultima_actualizacion()
    if current is None:
        return True, None  # Primera carga
    if since is None:
        return True, current  # Sin filtro, siempre hay cambios
    return current > since, current


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

    # Agregar conteo de imágenes
    for error in errores:
        error["imagenes_count"] = obtener_imagenes_count(error.get("id", ""))

    return errores


def crear_error(
    tipo_error: str,
    factura: str,
    observacion: str,
    estado: str,
    responsable: str,
    observacion_facturador: str = "",
) -> dict[str, Any]:
    """Crear un nuevo error."""
    data = _leer_datos()

    nuevo_error = {
        "id": str(uuid.uuid4()),
        "tipo_error": tipo_error,
        "factura": factura,
        "observacion": observacion,
        "observacion_facturador": observacion_facturador,
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
    tipo_error: str | None = _NOT_SET,
    factura: str | None = _NOT_SET,
    observacion: str | None = _NOT_SET,
    observacion_facturador: str | None = _NOT_SET,
    estado: str | None = _NOT_SET,
    responsable: str | None = _NOT_SET,
) -> dict[str, Any] | None:
    """Actualizar un error existente."""
    data = _leer_datos()

    for error in data.get("errores", []):
        if error.get("id") == error_id:
            if tipo_error is not _NOT_SET:
                error["tipo_error"] = tipo_error
            if factura is not _NOT_SET:
                error["factura"] = factura
            if observacion is not _NOT_SET:
                error["observacion"] = observacion
            if observacion_facturador is not _NOT_SET:
                error["observacion_facturador"] = observacion_facturador
            if estado is not _NOT_SET:
                error["estado"] = estado
            if responsable is not _NOT_SET:
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
        # Eliminar carpeta de imágenes
        _eliminar_carpeta_imagenes(error_id)
        return True

    return False


# =============================================================================
# Gestión de Imágenes
# =============================================================================

def _eliminar_carpeta_imagenes(error_id: str) -> None:
    """Eliminar carpeta de imágenes."""
    imagenes_dir = _get_imagenes_dir(error_id)
    if imagenes_dir.exists():
        shutil.rmtree(imagenes_dir)


def listar_imagenes(error_id: str) -> list[str]:
    """Listar nombres de imágenes."""
    imagenes_dir = _get_imagenes_dir(error_id)
    if not imagenes_dir.exists():
        return []
    return sorted([f.name for f in imagenes_dir.iterdir() if f.is_file()])


def obtener_imagenes_count(error_id: str) -> int:
    """Contar imágenes."""
    return len(listar_imagenes(error_id))


def validar_imagen(file) -> tuple[bool, str]:
    """Validar imagen."""
    ext = Path(file.filename).suffix.lower()
    if ext not in IMAGENES_ALLOWED_TYPES:
        return False, f"Tipo no permitido: {ext}"
    file.seek(0, 2)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > IMAGENES_MAX_SIZE_MB:
        return False, f"Tamaño máximo: {IMAGENES_MAX_SIZE_MB}MB"
    return True, ""


def guardar_imagen(error_id: str, file) -> tuple[bool, str]:
    """Guardar imagen."""
    if obtener_imagenes_count(error_id) >= IMAGENES_MAX_PER_OBSERVACION:
        return False, f"Máximo {IMAGENES_MAX_PER_OBSERVACION} imágenes"

    valid, error = validar_imagen(file)
    if not valid:
        return False, error

    imagenes_dir = _get_imagenes_dir(error_id)
    imagenes_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix.lower()
    count = obtener_imagenes_count(error_id)
    filename = f"img_{count + 1}{ext}"
    filepath = imagenes_dir / filename

    file.seek(0)
    filepath.write_bytes(file.read())
    logger.info("Imagen guardada: %s", filepath)

    return True, filename


def eliminar_imagen(error_id: str, filename: str) -> tuple[bool, str]:
    """Eliminar imagen."""
    imagenes_dir = _get_imagenes_dir(error_id)
    filepath = imagenes_dir / filename
    if not filepath.exists():
        return False, "Imagen no encontrada"
    filepath.unlink()
    logger.info("Imagen eliminada: %s", filepath)
    return True, ""