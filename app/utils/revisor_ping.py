"""Ping "hubo cambios" al servidor de Revisor de Soportes.

Cuando una novedad queda lista para avisar, control-novedades le avisa a
Revisor con un POST sin datos; Revisor responde consultando
``GET /api/integration/control-novedades/nuevas``. El ping es solo un
acelerador: Revisor igual consulta cada pocos minutos, así que un ping
perdido nunca pierde una novedad.

Reglas:
- Nunca frena ni rompe el guardado: corre en un hilo aparte, con timeout, y
  cualquier error se registra y se ignora.
- No lleva datos de la novedad; solo la clave compartida en un header.
- Sin ``REVISOR_PING_URL`` en el entorno no hace nada.
- Ráfagas (p. ej. una carga masiva) se agrupan: a lo sumo un hilo activo y un
  ping adicional al terminar, que cubre todo lo ocurrido mientras tanto.
"""

import logging
import os
import threading
import urllib.request

from app.constants.urgencias import (
    REVISOR_PING_CLAVE_ENV,
    REVISOR_PING_HEADER,
    REVISOR_PING_TIMEOUT_S,
    REVISOR_PING_URL_ENV,
)

logger = logging.getLogger(__name__)

_estado_lock = threading.Lock()
_en_curso = False
_pendiente = False


def _config() -> tuple[str, str]:
    """Lee (url, clave) del entorno; url vacía si falta o no es http(s)."""
    url = os.getenv(REVISOR_PING_URL_ENV, "").strip()
    clave = os.getenv(REVISOR_PING_CLAVE_ENV, "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        logger.warning("[BACK] %s inválida: debe ser http(s)", REVISOR_PING_URL_ENV)
        return "", clave
    return url, clave


def _enviar(url: str, clave: str) -> None:
    """Hace el POST; cualquier fallo se registra y se ignora."""
    try:
        request = urllib.request.Request(
            url,
            data=b"",
            method="POST",
            headers={REVISOR_PING_HEADER: clave},
        )
        with urllib.request.urlopen(request, timeout=REVISOR_PING_TIMEOUT_S) as response:
            response.read()
        logger.info("[BACK] Ping a Revisor enviado")
    except Exception as error:  # el ping nunca debe propagar errores
        logger.warning("[BACK] Ping a Revisor falló (se ignora): %s", error)


def _bucle(url: str, clave: str) -> None:
    """Envía y repite una vez más si hubo cambios durante el envío."""
    global _en_curso, _pendiente
    while True:
        _enviar(url, clave)
        with _estado_lock:
            if not _pendiente:
                _en_curso = False
                return
            _pendiente = False


def notificar_cambios() -> None:
    """Avisa a Revisor que hay novedades por consultar. No bloquea."""
    global _en_curso, _pendiente
    url, clave = _config()
    if not url:
        return
    with _estado_lock:
        if _en_curso:
            _pendiente = True
            return
        _en_curso = True
    threading.Thread(
        target=_bucle, args=(url, clave), daemon=True, name="revisor-ping"
    ).start()
