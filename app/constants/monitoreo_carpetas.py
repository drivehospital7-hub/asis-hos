"""Constantes para el módulo Monitoreo de Carpetas.

Configuración de rutas de red, patrones regex para validación de nombres,
keywords de inferencia de estado y timeouts de escaneo.

Todas las rutas de red se configuran via MONITOREO_CARPETAS_ROOTS env var.
"""

from __future__ import annotations

# =============================================================================
# STATUS - Keywords de inferencia de estado
# =============================================================================

STATUS_VERIFICADA: str = "Verificada"
STATUS_POR_CORREGIR: str = "Por corregir"
STATUS_EN_REVISION: str = "En revisión"

STATUS_KEYWORDS: dict[str, list[str]] = {
    STATUS_VERIFICADA: ["FACTURAS CAPITA OK", "LISTAS PARA PASAR"],
    STATUS_POR_CORREGIR: ["CORREGIR", "CORRECCION"],
    STATUS_EN_REVISION: ["default"],
}

# =============================================================================
# REGEX - Patrones de validación de nombres de facturas
# =============================================================================

# FEV seguido de uno o más dígitos (case-insensitive)
FEV_REGEX: str = r"FEV\d+"

# CAP + dígitos + _ + letras/dígitos + dígitos (ej: CAP001_CC123)
CAP_REGEX: str = r"CAP\d+_\w+\d+"

# =============================================================================
# ENV VAR - Configuración de rutas de red
# =============================================================================

ENV_MONITOREO_ROOTS: str = "MONITOREO_CARPETAS_ROOTS"

# =============================================================================
# TIMEOUTS - Configuración de escaneo
# =============================================================================

SCAN_TIMEOUT_PER_FACTURADOR: int = 120
"""Tiempo máximo en segundos para escanear un solo facturador.

NOTA (2026-09): 120s puede ser poco para un root UNC grande con miles de
carpetas en SMB lento — se evaluó subirlo a 300s o hacerlo configurable
por env var. Se MANTIENE en 120 a propósito: con el pre-probe acotado por
`ROOT_PROBE_TIMEOUT` + el guard anti-solapamiento del scheduler, un root
que excede este timeout genera una entrada de error acotada en vez de
colgar el request/scheduler. Si hay evidencia de timeouts legítimos (roots
accesibles pero lentos que siempre caen en timeout), subir a 300 o leer de
env var es el cambio previsto — ningún test actual lo exige."""

MAX_CONCURRENT_SCANS: int = 3
"""Máximo de escaneos simultáneos (semáforo de concurrencia)."""

# =============================================================================
# WATCHDOG — Configuración del observador de filesystem
# =============================================================================

WATCHDOG_POLL_INTERVAL: float = 1.0
"""Intervalo en segundos entre polls del watchdog observer."""

WATCHDOG_EVENT_TYPES: list[str] = ["created", "modified", "deleted", "moved"]
"""Tipos de eventos del filesystem que watchdog debe monitorear."""

ROOT_PROBE_TIMEOUT: float = 2.0
"""Timeout en segundos para el probe liviano de accesibilidad por root.

El health check prueba cada root con `os.scandir` de una sola entrada
(solo nombre/ruta, sin entrar a FEV/CAP). Si el probe excede este
timeout (típico en desconexión SMB) el root se marca degradado."""

# =============================================================================
# RECONCILIADOR — Background reconciler para pérdidas de eventos en SMB
# =============================================================================

RECONCILE_INTERVAL_SECS: float = 900.0
"""Intervalo en segundos entre ciclos del scheduler programado (15 min).

El escaneo programado es la FUENTE DE VERDAD (el watchdog Observer sobre
SMB es volátil: eventos perdidos, observer ciego). Cada ciclo hace un
`detect_all` completo de los roots accesibles (solo nombre/ruta de
carpetas FEV/CAP, sin abrir contenido interno) y mergea diffs al cache,
preservando los datos de roots degradados."""

ENABLE_WATCHDOG_OBSERVER: bool = False
"""Si True, arranca el watchdog Observer como best-effort en tiempo real.

Apagado por defecto: el Observer sobre SMB pierde eventos y no es
fuente de verdad. El scheduler programado (`RECONCILE_INTERVAL_SECS`)
es la única fuente de verdad."""

RECONCILE_ON_DEGRADED: bool = True
"""Si True, el reconciliador escanea los roots accesibles aunque haya
roots degradados (nunca fuerza los caídos ni borra sus datos del cache)."""

# =============================================================================
# CONFIG FILE - Ruta del archivo de configuración persistente
# =============================================================================

MONITOREO_CONFIG_FILE: str = "data/monitoreo_carpetas_config.json"

# =============================================================================
# EXCEL - Configuración del reporte
# =============================================================================

REPORT_SHEET_FACTURAS: str = "Facturas"
REPORT_SHEET_INDICADORES: str = "Indicadores"
REPORT_PREFIX: str = "monitoreo_"
REPORT_SUFFIX: str = ".xlsx"

EXCEL_REGEN_THROTTLE_SECS: float = 60.0
"""Throttle mínimo en segundos entre regeneraciones del Excel fresco.

Evita regenerar en cada evento watchdog (caro en I/O): `ensure_fresh_excel`
solo regenera si `excel_stale` es True Y pasó este intervalo desde la
última generación. Solo importa nombre/ruta de carpetas FEV/CAP."""

# Columnas del reporte de detalle
REPORT_COLUMNS: list[str] = [
    "Código Factura",
    "Tipo",
    "Estado",
    "Ruta Completa",
    "Facturador",
    "Fecha Escaneo",
    "Duplicado",
    "Carpeta Vacía",
    "Nombre Inválido",
]

# =============================================================================
# MOVE - Configuración de movimiento masivo de facturas
# =============================================================================

MOVE_MAX_BATCH: int = 50
"""Máximo de facturas por solicitud de movimiento masivo."""

MOVE_ERR_DEST_OUTSIDE_ROOTS: str = "Destination is outside configured roots."
MOVE_ERR_TRAVERSAL: str = "Destination path is not allowed."
MOVE_ERR_BATCH_LIMIT: str = "Batch exceeds maximum of 50 items."
MOVE_ERR_SRC_OUTSIDE_ROOTS: str = "Source is outside configured roots."
MOVE_ERR_SRC_MISSING: str = "Source does not exist."
MOVE_ERR_COLLISION: str = "Target already exists."
