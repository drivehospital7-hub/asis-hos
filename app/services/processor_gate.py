"""Gate de procesamiento: rate limiting y semáforo de concurrencia.

Capas independientes (cada una = PR distinto):
- rate_limit: decorator que limita requests POST por sesión (PR 2)
- acquire_semaphore / release_semaphore: semáforo de concurrencia global (PR 3)

Sin dependencias externas — usa solo Python stdlib + Flask.
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from threading import Semaphore

from flask import jsonify, request, session

logger = logging.getLogger(__name__)

# =============================================================================
# Semáforo de concurrencia (PR 3)
# =============================================================================

MAX_CONCURRENT = 3
"""Máximo de tareas de procesamiento simultáneas."""

SEMAPHORE_TIMEOUT = 30
"""Tiempo máximo de espera en segundos para adquirir el semáforo."""

_processor_semaphore = Semaphore(MAX_CONCURRENT)
"""Semáforo global que limita la concurrencia del procesamiento de Excel."""

_active_count = 0
"""Contador de tareas activas para logging. Solo se usa para informar."""


def acquire_semaphore(timeout: int = SEMAPHORE_TIMEOUT) -> bool:
    """Intenta adquirir el semáforo de procesamiento.

    Args:
        timeout: Tiempo máximo de espera en segundos.

    Returns:
        True si se adquirió el semáforo, False si se agotó el tiempo.
    """
    global _active_count
    acquired = _processor_semaphore.acquire(blocking=True, timeout=timeout)
    if acquired:
        _active_count += 1
        logger.info(
            "[BACK] Semaphore acquired (running: %d/%d)",
            _active_count,
            MAX_CONCURRENT,
        )
    else:
        logger.info("[BACK] Semaphore timeout — all %d slots busy", MAX_CONCURRENT)
    return acquired


def release_semaphore() -> None:
    """Libera el semáforo de procesamiento.

    Debe llamarse en un bloque ``finally`` para garantizar la liberación
    incluso si ocurre una excepción.
    """
    global _active_count
    _processor_semaphore.release()
    _active_count -= 1
    logger.info(
        "[BACK] Semaphore released (running: %d/%d)",
        _active_count,
        MAX_CONCURRENT,
    )


def rate_limit(limit: int = 1, window: int = 120):
    """Decorator: limita a ``limit`` requests POST en una ventana de ``window`` segundos.

    Usa ``session["_rate_limiter"]`` = lista de timestamps (``time.time()``).
    Solo cuenta requests POST (GET, HEAD, etc. no se limitan).
    Los timestamps expirados (``now - timestamp > window``) se podan antes de contar.
    Retorna 429 con mensaje "Demasiadas solicitudes. Espere {seconds} segundos."
    cuando se excede el límite.

    Args:
        limit: Número máximo de requests permitidos en la ventana.
        window: Duración de la ventana en segundos.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # GET y otros métodos no se cuentan
            if request.method != "POST":
                return f(*args, **kwargs)

            now = time.time()
            timestamps: list[float] = session.get("_rate_limiter", [])

            # Podar timestamps expirados (mayores a window segundos)
            cutoff = now - window
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= limit:
                # Calcular segundos hasta que expire el timestamp más antiguo
                remaining = max(1, int(timestamps[0] + window - now))
                logger.info(
                    "[BACK] Rate limit exceeded: %d requests in %ds window",
                    limit,
                    window,
                )
                return jsonify({
                    "status": "error",
                    "data": {},
                    "errors": [
                        f"Demasiadas solicitudes. Espere {remaining} segundos."
                    ],
                }), 429

            timestamps.append(now)
            session["_rate_limiter"] = timestamps
            return f(*args, **kwargs)
        return decorated
    return decorator
