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

from app.constants import (
    IMAGENES_DIR,
    IMAGENES_FACTURADOR_SCOPE,
    IMAGENES_MAX_PER_OBSERVACION,
    IMAGENES_ALLOWED_TYPES,
    IMAGENES_MAX_SIZE_MB,
    IMAGENES_SCOPES,
    IMAGENES_OWNER_SIDECAR,
)

logger = logging.getLogger(__name__)

# Sentinel para distinguir "no proporcionado" de "vacío"
_NOT_SET = object()

DATA_DIR = Path(__file__).parent.parent / "data"
ERRORES_FILE = DATA_DIR / "control_errores.json"
IMAGENES_PATH = DATA_DIR / "imagenes"

# Lock de módulo para operaciones de escritura (read-append-write) sobre el
# archivo JSON. Un solo proceso + escritura atómica garantiza que envíos
# concurrentes no pierdan actualizaciones entre sí.
_write_lock = threading.Lock()


def normalizar_identidad(s: str | None) -> str:
    """Normaliza una identidad: casefold, sin acentos y espacios colapsados.

    Ej: "LORENY  ESPAÑA " → "loreny espana". None/empty → "".
    """
    value = unicodedata.normalize("NFKD", s or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.casefold().split())


def _get_imagenes_dir(error_id: str, scope: str = "") -> Path:
    """Obtener carpeta de imágenes para un error, por scope.

    - scope "" (observación) → ``IMAGENES_PATH/{error_id}`` (legacy).
    - scope "facturador" → ``IMAGENES_PATH/{error_id}/facturador`` (FA-1).

    El scope alimenta un componente de ruta, así que TODO valor fuera del
    allowlist ``IMAGENES_SCOPES`` lanza ``ValueError`` (backstop de R2/D2);
    la ruta valida el scope y devuelve 400 antes de llegar acá.
    """
    if not error_id or error_id in {".", ".."} or Path(error_id).name != error_id:
        raise ValueError("error_id no permitido")
    if scope not in IMAGENES_SCOPES:
        raise ValueError(f"scope no permitido: {scope!r}")
    if scope == IMAGENES_FACTURADOR_SCOPE:
        return IMAGENES_PATH / error_id / scope
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

    # Agregar conteo de imágenes (por scope: observación + facturador)
    for error in errores:
        error_id = error.get("id", "")
        error["imagenes_count"] = obtener_imagenes_count(error_id)
        error["imagenes_facturador_count"] = obtener_imagenes_count(
            error_id, IMAGENES_FACTURADOR_SCOPE
        )

    return errores


def contar_duplicados(tipo_error: str, factura: str) -> int:
    """Cuenta registros existentes con el mismo ``tipo_error`` y ``factura``.

    Solo lectura (sigue el patrón de ``_leer_datos``); nunca modifica el
    almacén. Se usa para detectar envíos duplicados como advertencia, sin
    bloquear la creación de un registro nuevo.
    """
    data = _leer_datos()
    errores = data.get("errores", [])
    return sum(
        1
        for error in errores
        if error.get("tipo_error") == tipo_error and error.get("factura") == factura
    )


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
    refactura: str = "",
) -> dict[str, Any]:
    """Crea un error de forma ATÓMICA bajo ``_write_lock``.

    Todo el read-append-write (leer, agregar, escribir) corre dentro del lock,
    evitando pérdidas de actualizaciones entre envíos concurrentes. Cada
    llamada crea SIEMPRE un registro nuevo (los duplicados se permiten).

    Args:
        created_by: username del creador (auditoría automática, nunca
            proviene del payload del cliente).
        refactura: campo opcional (ReFactura); default ``""``. Se agrega al
            final de la firma para no romper callers posicionales existentes.

    Returns:
        El registro persistido.
    """
    with _write_lock:
        data = _leer_datos()

        nuevo_error = {
            "id": str(uuid.uuid4()),
            "tipo_error": tipo_error,
            "factura": factura,
            "refactura": refactura,
            "observacion": observacion,
            "observacion_facturador": observacion_facturador,
            "estado": estado,
            "responsable": responsable,
            "validador": validador,
            "created_by": created_by,
            "creado_en": datetime.now().isoformat(),
            "actualizado_en": datetime.now().isoformat(),
        }

        data.setdefault("errores", []).append(nuevo_error)
        _escribir_datos(data)

        logger.info("[BACK] Error creado: %s", nuevo_error["id"])
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
    refactura: str | None = _NOT_SET,
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
            if refactura is not _NOT_SET:
                error["refactura"] = refactura

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


def listar_imagenes(error_id: str, scope: str = "") -> list[str]:
    """Listar nombres de imágenes de un error, dentro del scope indicado.

    Excluye dotfiles (el sidecar ``.owner.json``) para que no cuente para
    cupo/count ni sea exportable/servible (FA-7/R3/D11).
    """
    imagenes_dir = _get_imagenes_dir(error_id, scope)
    if not imagenes_dir.exists():
        return []
    return sorted(
        f.name
        for f in imagenes_dir.iterdir()
        if f.is_file() and not f.name.startswith(".")
    )


def obtener_imagenes_count(error_id: str, scope: str = "") -> int:
    """Contar imágenes de un error, dentro del scope indicado."""
    return len(listar_imagenes(error_id, scope))


def _owner_sidecar_path(error_id: str, scope: str = "") -> Path:
    """Ruta del sidecar de ownership dentro del scope ({id}/.owner.json).

    ``_get_imagenes_dir`` ya valida error_id y scope contra el allowlist
    (backstop de R2/D2), así que el sidecar nunca escapa del scope.
    """
    return _get_imagenes_dir(error_id, scope) / IMAGENES_OWNER_SIDECAR


def _leer_owner(error_id: str, scope: str = "") -> dict[str, str]:
    """Leer el mapeo {filename: username} del sidecar (vacío si no existe)."""
    sidecar = _owner_sidecar_path(error_id, scope)
    if not sidecar.exists():
        return {}
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        return {}
    except Exception:
        logger.exception("[BACK][ERROR] Sidecar ilegible: %s", sidecar)
        return {}


def _escribir_owner(error_id: str, owner: dict[str, str], scope: str = "") -> None:
    """Persistir el sidecar de ownership de forma atómica bajo ``_write_lock``.

    Patrón tempfile→replace igual que ``_escribir_datos``. Solo se llama
    desde guardar/eliminar_imagen, que ya corren dentro de ``_write_lock``
    (no anida el lock).
    """
    sidecar = _owner_sidecar_path(error_id, scope)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=sidecar.parent, suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(owner, f, ensure_ascii=False, indent=2)
        Path(tmp_path).replace(sidecar)
    except Exception:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        logger.error("[BACK][ERROR] Fallo escribiendo sidecar de ownership: %s", sidecar)
        raise


def validar_imagen(file) -> tuple[bool, str]:
    """Validar archivo (imagen, PDF o Excel)."""
    ext = Path(file.filename).suffix.lower()
    if ext not in IMAGENES_ALLOWED_TYPES:
        return False, f"Tipo no permitido: {ext}"
    file.seek(0, 2)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > IMAGENES_MAX_SIZE_MB:
        return False, f"Tamaño máximo: {IMAGENES_MAX_SIZE_MB}MB"
    return True, ""


def guardar_imagen(
    error_id: str, file, scope: str = "", username: str | None = None
) -> tuple[bool, str]:
    """Guardar archivo (imagen, PDF o Excel) dentro del scope indicado.

    El cupo máximo (IMAGENES_MAX_PER_OBSERVACION) se aplica POR scope:
    observación y facturador tienen 3 archivos cada uno (FA-1).

    Si ``username`` se provee, registra la propiedad en el sidecar
    ``{filename: username}`` (FA-7). El storage persiste metadata pero NO
    decide permisos (D1/D13); la autorización vive en el service.
    """
    with _write_lock:
        if obtener_imagenes_count(error_id, scope) >= IMAGENES_MAX_PER_OBSERVACION:
            return False, f"Máximo {IMAGENES_MAX_PER_OBSERVACION} archivos"

        valid, error = validar_imagen(file)
        if not valid:
            return False, error

        imagenes_dir = _get_imagenes_dir(error_id, scope)
        imagenes_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename).suffix.lower()
        filename = f"file_{obtener_imagenes_count(error_id, scope) + 1}{ext}"
        filepath = imagenes_dir / filename
        file.seek(0)
        try:
            with filepath.open("xb") as output:
                output.write(file.read())
        except Exception:
            filepath.unlink(missing_ok=True)
            raise
        if username:
            owner = _leer_owner(error_id, scope)
            owner[filename] = username
            _escribir_owner(error_id, owner, scope)
        logger.info("[BACK] Archivo guardado: %s", filepath)
        return True, filename


def eliminar_imagen(
    error_id: str, filename: str, scope: str = "", username: str | None = None
) -> tuple[bool, str]:
    """Eliminar imagen dentro del scope, SOLO si está en su listado (R1).

    El check ``filename in listar_imagenes(error_id, scope)`` corre ANTES de
    cualquier operación de filesystem: nombres con ``../`` o no listados se
    rechazan sin tocar nada (bloquea borrados cross-scope y path tricks).

    Al borrar, limpia la entrada del sidecar para mantener la metadata
    consistente con el filesystem (FA-7/D10). ``username`` no se usa en
    storage (no decide permisos); queda para simetría de firma.
    """
    if filename not in listar_imagenes(error_id, scope):
        return False, "Imagen no encontrada"
    imagenes_dir = _get_imagenes_dir(error_id, scope)
    filepath = imagenes_dir / filename
    if not filepath.exists():
        return False, "Imagen no encontrada"
    filepath.unlink()
    owner = _leer_owner(error_id, scope)
    if filename in owner:
        del owner[filename]
        if owner:
            _escribir_owner(error_id, owner, scope)
        else:
            _owner_sidecar_path(error_id, scope).unlink(missing_ok=True)
    logger.info("[BACK] Imagen eliminada: %s", filepath)
    return True, ""


def obtener_uploader(error_id: str, filename: str, scope: str = "") -> str | None:
    """Devuelve el username que subió ``filename`` (o None si legacy/sin dueño).

    Lee el sidecar ``{filename: username}`` del scope. Los adjuntos legacy
    (sin sidecar) devuelven None → no borrables por no-admin (FA-8).
    """
    return _leer_owner(error_id, scope).get(filename)
