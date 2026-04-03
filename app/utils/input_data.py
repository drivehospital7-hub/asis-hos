"""Rutas y listado seguro de archivos en el directorio de entrada de datos."""

from __future__ import annotations

from pathlib import Path

from app.constants import ALLOWED_EXCEL_SUFFIXES


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
