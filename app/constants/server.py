"""Constantes de tuning del servidor WSGI de producción (Waitress).

Centraliza los parámetros de ``waitress.serve`` para que ``run_prod.py``
no hardcodee valores y queden documentados en un solo lugar.

Contexto: con los defaults de Waitress (4 threads) y exports de Excel
bloqueantes de ~15-20s, la cola se saturaba (``Task queue depth`` en logs)
y el servidor parecía "caerse por segundos". Estos valores dejan threads
libres para requests livianos (login, nav, polling) mientras el semáforo
de ``processor_gate`` sigue protegiendo el CPU de exports concurrentes.
"""

from __future__ import annotations

WAITRESS_THREADS: int = 16
"""Threads worker de Waitress (default upstream: 4).

16 alcanza para ~3 exports bloqueantes + polls livianos concurrentes
en una LAN chica sin disparar el uso de memoria.
"""

WAITRESS_CONNECTION_LIMIT: int = 200
"""Máximo de conexiones TCP pendientes (default upstream: 100)."""

WAITRESS_CHANNEL_TIMEOUT: int = 120
"""Timeout en segundos de un canal inactivo (default upstream: 120)."""

WAITRESS_CLEANUP_INTERVAL: int = 30
"""Intervalo en segundos de limpieza de canales muertos (default: 30)."""

WAITRESS_MAX_REQUEST_BODY_SIZE: int = 100 * 1024 * 1024
"""Cuerpo máximo aceptado por Waitress: 100 MB.

Alineado con ``ProdConfig.MAX_CONTENT_LENGTH`` para rechazar temprano
uploads gigantes antes de que lleguen a Flask.
"""

ERRORES_WRITE_MAX_RETRIES: int = 5
"""Reintentos de ``os.replace`` ante ``PermissionError`` (WinError 5).

En Windows el antivirus o un thread concurrente puede lockear el JSON
por milisegundos; reintentar con backoff evita 500 espurios.
"""

ERRORES_WRITE_RETRY_DELAY_SECS: float = 0.2
"""Espera base entre reintentos de escritura (backoff lineal)."""
