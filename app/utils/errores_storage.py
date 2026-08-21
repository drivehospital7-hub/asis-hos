"""Persistencia JSON para control de errores de urgencias."""

import json
import logging
import uuid
import shutil
import tempfile
import threading
import unicodedata
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

# Lock de módulo para operaciones idempotentes (check-then-write) sobre el
# archivo JSON. Un solo proceso + escritura atómica garantiza no duplicados.
_idempotency_lock = threading.Lock()


def normalizar_identidad(s: str | None) -> str:
    """Normaliza una identidad: casefold, sin acentos y espacios colapsados.

    Ej: "LORENY  ESPAÑA " → "loreny espana". None/empty → "".
    """
    value = unicodedata.normalize("NFKD", s or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.casefold().split())


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
    owner_identity: str | None = None,
    owner_full_identity: str | None = None,
    responsable_identity: str | None = None,
    responsable_full_identity: str | None = None,
    validador: str | None = None,
) -> list[dict[str, Any]]:
    """Listar errores con filtros opcionales.

    Args:
        owner_identity: si se provee, solo devuelve errores cuyos tokens de
            ``responsable`` coincidan con la identidad canónica de los registros
            nuevos, o cuyos tokens estén contenidos en la identidad completa
            para registros legacy. None → sin filtro de propietario.
        owner_full_identity: nombre completo DB usado solo por registros legacy.
        responsable_identity: identidad canónica DB para resolver un filtro.
        responsable_full_identity: nombre completo DB usado por el filtro legacy.
        validador: identidad del validador; se compara normalizada con el campo
            persistido ``validador``.
    """
    data = _leer_datos()
    errores = data.get("errores", [])

    if tipo_error:
        errores = [e for e in errores if e.get("tipo_error") == tipo_error]
    if estado:
        errores = [e for e in errores if e.get("estado") == estado]
    if responsable:
        if responsable_identity is not None:
            errores = [
                e for e in errores
                if _responsable_coincide_con_owner(
                    e.get("responsable", ""),
                    responsable_identity,
                    e.get("created_by", ""),
                    responsable_full_identity,
                )
            ]
        else:
            errores = [e for e in errores if e.get("responsable") == responsable]
    if owner_identity is not None:
        errores = [
            e for e in errores
            if _responsable_coincide_con_owner(
                e.get("responsable", ""),
                owner_identity,
                e.get("created_by", ""),
                owner_full_identity,
            )
        ]
    if validador:
        validador_identity = normalizar_identidad(validador)
        errores = [
            e for e in errores
            if normalizar_identidad(e.get("validador", "")) == validador_identity
        ]

    # Ordenar por fecha de creación (más reciente primero)
    errores = sorted(errores, key=lambda e: e.get("creado_en", ""), reverse=True)

    # Agregar conteo de imágenes
    for error in errores:
        error["imagenes_count"] = obtener_imagenes_count(error.get("id", ""))

    return errores


def _responsable_coincide_con_owner(
    responsable: str | None,
    owner_identity: str,
    created_by: str | None = None,
    owner_full_identity: str | None = None,
) -> bool:
    """Match new records exactly and legacy records by a safe token subset."""
    if normalizar_identidad(created_by):
        return normalizar_identidad(responsable) == normalizar_identidad(owner_identity)

    responsable_tokens = normalizar_identidad(responsable).split()
    owner_tokens = set(
        normalizar_identidad(owner_full_identity or owner_identity).split()
    )
    return len(responsable_tokens) >= 2 and set(responsable_tokens) <= owner_tokens


def crear_error(
    tipo_error: str,
    factura: str,
    observacion: str,
    estado: str,
    responsable: str,
    observacion_facturador: str = "",
    validador: str = "",
    created_by: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Crear un nuevo error.

    Args:
        created_by: username del creador (auditoría automática, nunca
            proviene del payload del cliente).
        idempotency_key: clave de idempotencia (integración LAN). Se persiste
            en el registro para deduplicar reintentos.
    """
    record, _ = crear_error_idempotente(
        idempotency_key=idempotency_key,
        tipo_error=tipo_error,
        factura=factura,
        observacion=observacion,
        observacion_facturador=observacion_facturador,
        estado=estado,
        responsable=responsable,
        validador=validador,
        created_by=created_by,
    )
    return record


def crear_error_idempotente(
    idempotency_key: str,
    tipo_error: str,
    factura: str,
    observacion: str,
    estado: str,
    responsable: str,
    observacion_facturador: str = "",
    validador: str = "",
    created_by: str = "",
) -> tuple[dict[str, Any], bool]:
    """Crea un error de forma ATÓMICA e idempotente bajo ``_idempotency_lock``.

    Todo el check-then-write (leer, comprobar clave, agregar, escribir) corre
    dentro del lock, eliminando el TOCTOU de ``_find_by_idempotency`` +
    ``crear_error`` separados: dos envíos concurrentes con la misma
    ``idempotency_key`` jamás persisten dos registros (también protege contra
    la pérdida de actualizaciones entre claves distintas, R4-2).

    Returns:
        (record, created): ``created`` es True si se persistió un registro
        nuevo; False si ya existía uno con esa ``idempotency_key`` (se devuelve
        el existente y NO se escribe nada).
    """
    with _idempotency_lock:
        data = _leer_datos()

        # Idempotencia: si la clave ya existe, devolver el original sin escribir.
        if idempotency_key:
            for error in data.get("errores", []):
                if error.get("idempotency_key") == idempotency_key:
                    return error, False

        nuevo_error = {
            "id": str(uuid.uuid4()),
            "tipo_error": tipo_error,
            "factura": factura,
            "observacion": observacion,
            "observacion_facturador": observacion_facturador,
            "estado": estado,
            "responsable": responsable,
            "validador": validador,
            "created_by": created_by,
            "idempotency_key": idempotency_key or "",
            "creado_en": datetime.now().isoformat(),
            "actualizado_en": datetime.now().isoformat(),
        }

        data.setdefault("errores", []).append(nuevo_error)
        _escribir_datos(data)

        logger.info("[BACK] Error creado: %s", nuevo_error["id"])
        return nuevo_error, True


def find_by_idempotency(idempotency_key: str) -> dict[str, Any] | None:
    """Busca un registro por su clave de idempotencia (bajo lock)."""
    if not idempotency_key:
        return None
    with _idempotency_lock:
        data = _leer_datos()
        for error in data.get("errores", []):
            if error.get("idempotency_key") == idempotency_key:
                return error
    return None


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
            logger.info("[BACK] Error actualizado: %s", error_id)
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
        logger.info("[BACK] Error eliminado: %s", error_id)
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
    """Validar archivo (imagen o PDF)."""
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
    """Guardar archivo (imagen o PDF)."""
    if obtener_imagenes_count(error_id) >= IMAGENES_MAX_PER_OBSERVACION:
        return False, f"Máximo {IMAGENES_MAX_PER_OBSERVACION} archivos"

    valid, error = validar_imagen(file)
    if not valid:
        return False, error

    imagenes_dir = _get_imagenes_dir(error_id)
    imagenes_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix.lower()
    count = obtener_imagenes_count(error_id)
    filename = f"file_{count + 1}{ext}"
    filepath = imagenes_dir / filename

    file.seek(0)
    filepath.write_bytes(file.read())
    logger.info("[BACK] Archivo guardado: %s", filepath)

    return True, filename


def eliminar_imagen(error_id: str, filename: str) -> tuple[bool, str]:
    """Eliminar imagen."""
    imagenes_dir = _get_imagenes_dir(error_id)
    filepath = imagenes_dir / filename
    if not filepath.exists():
        return False, "Imagen no encontrada"
    filepath.unlink()
    logger.info("[BACK] Imagen eliminada: %s", filepath)
    return True, ""
