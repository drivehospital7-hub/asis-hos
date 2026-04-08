"""Rutas y listado seguro de archivos en el directorio de entrada de datos."""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from app.constants import ALLOWED_EXCEL_SUFFIXES

logger = logging.getLogger(__name__)


def input_data_directory() -> Path:
    """Directorio `app/data/input` (resuelto)."""
    return (Path(__file__).resolve().parent.parent / "data" / "input").resolve()


def output_data_directory(*, create: bool = False) -> Path:
    """Directorio `app/data/output` (resuelto)."""
    base = (Path(__file__).resolve().parent.parent / "data" / "output").resolve()
    if create:
        base.mkdir(parents=True, exist_ok=True)
    return base


def list_excel_filenames() -> list[str]:
    """Nombres de archivo Excel en la carpeta de entrada, ordenados."""
    base = input_data_directory()
    if not base.is_dir():
        return []
    names: list[str] = []
    for path in base.iterdir():
        if path.is_file() and path.suffix.lower() in ALLOWED_EXCEL_SUFFIXES:
            names.append(path.name)
    return sorted(names)


def resolve_safe_excel_in_input(filename: str) -> tuple[Path | None, str | None]:
    """
    Resuelve `filename` dentro de `data/input` sin path traversal.
    Devuelve (path, None) o (None, mensaje_error).
    """
    raw = (filename or "").strip()
    if not raw:
        return None, "Selecciona un archivo."

    basename = Path(raw).name
    if basename != raw or basename in (".", ".."):
        return None, "Nombre de archivo no válido."

    base = input_data_directory()
    candidate = (base / basename).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None, "Ruta fuera del directorio permitido."

    return candidate, None


def resolve_safe_excel_absolute(filepath: str) -> tuple[Path | None, str | None]:
    """
    Resuelve una ruta absoluta (archivo subido) o relative (del repo).
    Para rutas absolutas: valida que esté en temp_uploads.
    Para rutas relativas: usa resolve_safe_excel_in_input.
    Devuelve (path, None) o (None, mensaje_error).
    """
    raw = (filepath or "").strip()
    if not raw:
        return None, "Selecciona un archivo."

    path = Path(raw)
    
    # Si es ruta absoluta (archivo subido)
    if path.is_absolute():
        try:
            resolved = path.resolve()
            temp_dir = temp_upload_directory()
            # Verificar que está dentro del directorio temporal
            if temp_dir not in resolved.parents and resolved.parent != temp_dir:
                return None, "Archivo no está en el directorio temporal permitido."
            if not resolved.exists():
                return None, "El archivo no existe."
            return resolved, None
        except Exception as e:
            return None, f"Ruta no válida: {e}"
    
    # Si es ruta relativa -> buscar en data/input
    return resolve_safe_excel_in_input(raw)


def resolve_safe_excel_in_output(
    filename: str, *, create_dir: bool = True
) -> tuple[Path | None, str | None]:
    """
    Resuelve `filename` dentro de `data/output` sin path traversal.
    Devuelve (path, None) o (None, mensaje_error).
    """
    raw = (filename or "").strip()
    if not raw:
        return None, "Nombre de archivo de salida no válido."

    basename = Path(raw).name
    if basename != raw or basename in (".", ".."):
        return None, "Nombre de archivo de salida no válido."

    base = output_data_directory(create=create_dir)
    candidate = (base / basename).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None, "Ruta fuera del directorio de salida permitido."

    return candidate, None


# =============================================================================
# UPLOAD - Archivos temporales subidos por el usuario
# =============================================================================

def temp_upload_directory() -> Path:
    """Directorio `app/data/temp_uploads` (resuelto)."""
    base = (Path(__file__).resolve().parent.parent / "data" / "temp_uploads").resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_temp_excel(file_storage) -> tuple[Path | None, str | None]:
    """
    Guarda un archivo Excel subido por el usuario en el directorio temporal.
    Devuelve (path, None) o (None, mensaje_error).
    """
    if not file_storage or not file_storage.filename:
        return None, "No se recibió ningún archivo."

    filename = file_storage.filename.strip()
    if not filename:
        return None, "Nombre de archivo no válido."

    # Validar extensión
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXCEL_SUFFIXES:
        return None, f"Formato no permitido. Usar: {', '.join(ALLOWED_EXCEL_SUFFIXES)}"

    # Validar tamaño (comentado - sin límite)
    # file_storage.seek(0, 2)
    # size_mb = file_storage.tell() / (1024 * 1024)
    # file_storage.seek(0)
    #
    # if size_mb > MAX_UPLOAD_SIZE_MB:
    #     return None, f"Archivo demasiado grande. Máximo: {MAX_UPLOAD_SIZE_MB}MB"

    # Generar nombre único para evitar conflictos
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    dest = temp_upload_directory() / unique_name

    try:
        file_storage.save(dest)
        logger.info("Archivo temporal guardado: %s", unique_name)
        return dest, None
    except Exception as e:
        logger.exception("Error guardando archivo temporal")
        return None, f"Error al guardar archivo: {e}"


def cleanup_temp_excel(path: Path) -> None:
    """Elimina un archivo temporal si existe."""
    if not path:
        return
    try:
        if path.exists() and temp_upload_directory() in path.resolve().parents:
            path.unlink()
            logger.info("Archivo temporal eliminado: %s", path.name)
    except Exception as e:
        logger.warning("Error eliminando archivo temporal %s: %s", path, e)
