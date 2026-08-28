"""Persistencia JSON atómica para el módulo Exámenes (Lab Prefactura).

Espeja el patrón de ``monitoreo_store.py`` (escrituras atómicas vía
``tempfile.mkstemp`` + ``Path.replace``) y la convención
``FLASK_DATA_SUFFIX`` del app standalone original
(``D:\\CODE\\examenes\\app.py``): ``examenes-dev.json`` vs ``examenes.json``.

Contratos (EX-4 / EX-5):
- ``get_examenes()``: catálogo. Si el archivo NO existe → siembra
  ``DEFAULT_EXAMENES`` (seed solo cuando está ausente — no-reseed) y lo
  devuelve. Si el archivo existe pero está corrupto → ``[]`` + log
  (nunca se pisa ni se siembra sobre basura).
- ``get_listado()``: listado. Ausente → ``[]`` (NUNCA se siembra: la copia
  del listado vivo es un paso manual de despliegue); corrupto → ``[]`` + log.
- ``save_examenes`` / ``save_listado``: escritura atómica.
- ``save_if_unchanged``: CAS atómico (compara ``base_hash`` y escribe bajo el
  mismo lock, R4-001).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from app.constants.examenes import (
    DEFAULT_EXAMENES,
    EX_EXAMENES_FILE,
    EX_LISTADO_FILE,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# Lock de módulo para escrituras atómicas (precedente errores_storage.py:36):
# serializa los replace de archivos completos para que dos writers concurrentes
# no pisen el guardado del otro entre mkstemp y replace (R4-001).
_write_lock = threading.Lock()


def _suffixed(filename: str) -> str:
    """Inserta ``FLASK_DATA_SUFFIX`` antes de la extensión (convención fuente).

    Ej: ``examenes.json`` + ``FLASK_DATA_SUFFIX=-dev`` → ``examenes-dev.json``.
    Se lee por llamada (no al import) para que los tests puedan aislar dev/prod.
    """
    suffix = os.environ.get("FLASK_DATA_SUFFIX", "")
    stem, ext = os.path.splitext(filename)
    return f"{stem}{suffix}{ext}"


def _resolve(filename: str) -> Path:
    """Ruta completa de un archivo de datos respetando el sufijo de entorno."""
    return DATA_DIR / _suffixed(filename)


def _read_json(path: Path) -> list | None:
    """Lee y parsea un arreglo JSON. None si falta el archivo o está corrupto."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Error leyendo archivo de datos de exámenes: %s", path)
        return None
    if not isinstance(data, list):
        logger.error("Archivo de datos de exámenes sin arreglo: %s", path)
        return None
    return data


def _write_atomic(path: Path, data: list) -> None:
    """Escritura atómica pública: adquiere ``_write_lock`` y delega."""
    with _write_lock:
        _write_atomic_unlocked(path, data)


def _write_atomic_unlocked(path: Path, data: list) -> None:
    """Escritura atómica bajo lock ya adquirido: mkstemp + Path.replace.

    El archivo nunca queda a medias: el replace es atómico dentro del
    filesystem (EX-4 atomic write). En fallo se limpia el temp y se re-lanza.
    NO adquiere ``_write_lock``: el caller debe sostenerlo (escrituras
    full-array concurrentes se serializan, R4-001).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        Path(tmp_path).replace(path)
        logger.info("Datos de exámenes guardados: %s", path.name)
    except Exception:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise


def file_hash(filename: str) -> str:
    """SHA-256 canónico del estado actual del archivo (R4-001).

    La serialización canónica (compacta, ``sort_keys``, sin escape ASCII)
    coincide con ``canonicalJson`` del frontend. Ausente/corrupto → hash del
    arreglo vacío (lo que devuelve el GET): un cliente que basó su copia en
    ese estado no recibe un 409 falso en la primera escritura.
    """
    data = _read_json(_resolve(filename))
    if data is None:
        data = []
    canonical = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_if_unchanged(filename: str, data: list, base_hash: str | None = None) -> str:
    """CAS atómico (R4-001): compara y escribe bajo el MISMO ``_write_lock``.

    Cierra el TOCTOU de routes (examenes.py): la comparación de
    ``base_hash`` y la escritura compiten por el lock, así dos POSTs
    concurrentes con el mismo ``base_hash`` no pasan la verificación y se
    pisan entre sí. ``base_hash`` ausente → reemplazo legacy (escribe siempre).

    Returns:
        ``"ok"`` si escribió; ``"conflict"`` si ``base_hash`` no coincide
        con el estado actual (sin escribir).
    """
    with _write_lock:
        if base_hash is not None and base_hash != file_hash(filename):
            return "conflict"
        _write_atomic_unlocked(_resolve(filename), data)
        return "ok"


def get_examenes() -> list:
    """Catálogo de exámenes; siembra DEFAULT_EXAMENES SOLO si no hay archivo.

    Returns:
        La lista del catálogo (archivo existente, defaults sembrados o ``[]``
        si el archivo está corrupto — nunca crash, EX-4).
    """
    path = _resolve(EX_EXAMENES_FILE)
    data = _read_json(path)
    if data is None:
        if not path.exists():
            logger.info(
                "Catálogo de exámenes ausente — sembrando %d defaults",
                len(DEFAULT_EXAMENES),
            )
            _write_atomic(path, DEFAULT_EXAMENES)
            return DEFAULT_EXAMENES
        # Corrupto: nunca sobrescribir ni sembrar sobre basura (EX-4)
        return []
    return data


def save_examenes(data: list) -> None:
    """Persiste el catálogo completo (arreglo) de forma atómica."""
    _write_atomic(_resolve(EX_EXAMENES_FILE), data)


def get_listado() -> list:
    """Listado de prefacturas; ausente → ``[]`` (nunca se siembra, EX-5).

    Returns:
        El listado del archivo, o ``[]`` si falta o está corrupto (con log).
    """
    data = _read_json(_resolve(EX_LISTADO_FILE))
    return data if data is not None else []


def save_listado(data: list) -> None:
    """Persiste el listado completo (arreglo) de forma atómica."""
    _write_atomic(_resolve(EX_LISTADO_FILE), data)