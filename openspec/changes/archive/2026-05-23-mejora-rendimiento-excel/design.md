# Design: Mejora de rendimiento de procesamiento de Excel y control de carga

## Technical Approach

Tres capas independientes (cada una = un commit reversible), acumulativas, sin dependencias externas. Cada capa corta en un punto distinto del pipeline: request gateway (Flask), app-level save (upload), y processing (service).

## Architecture Decisions

### Decision: Layer order — Gateway → Upload → Processing

| Layer | Where | What | Feedback |
|-------|-------|------|----------|
| 1. File size | `config/prod.py` (Flask `MAX_CONTENT_LENGTH`) + `save_temp_excel()` | Rejects >100MB at HTTP level; validates per-file in app | 413 or inline error |
| 2. Rate limiter | Decorator on POST routes | N req/min per session via `session["_rate_limiter"]` | 429 |
| 3. Concurrency | `threading.Semaphore` in `processor_gate.py` | Max 3 simultaneous processing tasks, 30s timeout | 503 |

**Rationale**: Cada capa corta en un punto distinto — cuello de botella temprano (gateway), medio (upload), y tardío (procesamiento pesado). Orden elegido intencionalmente: lo más barato (chequear Content-Length) primero.

### Decision: `session`-based rate limiter instead of Redis/memcached

**Choice**: Flask session object (cookies, HMAC-signed, server not needed)
**Alternatives**: Redis, Flask-Limiter extension, filesystem
**Rationale**: Zero new deps. Session es HMAC-signed cookie — no ocupa memoria server. Suficiente para 1ra iteración. La volatilidad (sesión expira) es aceptable: el límite se resetea cuando el usuario vuelve a login. Migrar a Redis post-MVP si hay presión.

### Decision: `threading.Semaphore` instead of `asyncio`/`multiprocessing`

**Choice**: `threading.Semaphore(N)` with `acquire(timeout=30)`
**Alternatives**: `multiprocessing.Semaphore`, Redis lock, asyncio queue
**Rationale**: Semáforo de threads es suficiente porque waitress ya maneja pooling. No hay I/O asíncrono que justifique asyncio. Redis sería overkill para un flag global. `finally` block garantiza release incluso con exception.

### Decision: Rate limiter covers only `excel_headers` and `urgencias` POST endpoints

**Choice**: Decorator only on POST routes in `excel_headers.py` and `urgencias.py`
**Alternatives**: All POST endpoints, Flask `before_request`, middleware
**Rationale**: Solo esos dos endpoints hacen procesamiento pesado de Excel. `ordenado_facturado.py` usa `tempfile.NamedTemporaryFile` directo (no pasa por `save_temp_excel`) — lo excluimos deliberadamente por ahora. `before_request` sería demasiado amplio (afectaría auth y APIs livianas). Decorator explícito = intención clara.

## Data Flow

```
Client POST /odontologia
  │
  ├─[Gateway] Flask MAX_CONTENT_LENGTH (100MB)
  │  413 ─→ "Archivo excede el tamaño máximo"
  │
  ├─[Upload] save_temp_excel()
  │  Error ─→ "Archivo demasiado grande. Máximo: {N}MB"
  │
  ├─[Rate Limit] @rate_limit(10, 60)
  │  429 ─→ "Demasiadas solicitudes. Espere {s} segundos."
  │
  ├─[Concurrency] processor_gate.acquire(timeout=30)
  │  503 ─→ "Servidor ocupado. Intente nuevamente."
  │
  └─ detect_problems_only()
       └─ processor_gate.release() [finally]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `config/prod.py` | Modify | `MAX_CONTENT_LENGTH = 100 * 1024 * 1024` |
| `app/constants/base.py` | Modify | Add `MAX_EXCEL_UPLOAD_SIZE_MB = 100` |
| `app/utils/input_data.py` | Modify | Activate commented size validation in `save_temp_excel()` |
| `app/services/processor_gate.py` | Create | Semaphore singleton + decorator `@rate_limit(limit, window)` |
| `app/services/exporter.py` | Modify | `detect_problems_only()` acquires/releases semaphore |
| `app/routes/excel_headers.py` | Modify | Add `@rate_limit(10, 60)` decorator to POST |
| `app/routes/urgencias.py` | Modify | Add `@rate_limit(10, 60)` decorator to POST |

## Interfaces / Contracts

```python
# app/services/processor_gate.py

from functools import wraps
from threading import Semaphore

MAX_CONCURRENT = 3
SEMAPHORE_TIMEOUT = 30  # seconds
RATE_LIMIT_DEFAULT = (10, 60)  # 10 requests per 60 seconds

_processor_semaphore = Semaphore(MAX_CONCURRENT)

def acquire_semaphore(timeout: int = SEMAPHORE_TIMEOUT) -> bool:
    """Intenta adquirir el semáforo. Retorna True si lo logra."""

def release_semaphore() -> None:
    """Libera el semáforo. Llámame en finally."""

def rate_limit(limit: int = 10, window: int = 60):
    """Decorator: N requests por ventana de M segundos.
    Usa session['_rate_limiter'] = [timestamps_float].
    """
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (file size) | `save_temp_excel()` rejects files > limit | Mock file_storage, assert error message |
| Unit (rate limiter) | Decorator counts timestamps, returns 429 at limit | Flask test client, same session cookie, N+1 requests |
| Unit (semaphore) | Acquire/release, timeout → 503 | Mock Semaphore to simulate full capacity |
| Integration | `@rate_limit` + semaphore stacked on real route | Flask test client hitting `/odontologia` POST |

## Migration / Rollout

No migration required. Each layer deploys independently: size → rate → concurrency. Each commit is revertible individually.

## Open Questions

- None. Spec covers all scenarios; design maps cleanly.
