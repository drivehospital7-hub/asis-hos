# Upload Rate Limiting Specification

## Purpose

Control de carga de procesamiento de Excel: límite de tamaño de archivo, rate limiting por sesión y semáforo de concurrencia global. Estas tres capas protegen CPU/memoria del servidor y dan feedback claro al usuario cuando se excede algún límite.

## Requirements

### R1: File Size Validation

The system MUST reject Excel uploads exceeding `MAX_EXCEL_UPLOAD_SIZE_MB` (defined in `app/constants/base.py`) before any processing begins. The rejection SHALL return a clear error message indicating the maximum allowed size. In production, Flask `MAX_CONTENT_LENGTH` SHALL be set to 100MB as a hard request-level gate.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| File within limit | file ≤ MAX_EXCEL_UPLOAD_SIZE_MB | upload via POST | 200; processing proceeds |
| File exceeds limit | file > MAX_EXCEL_UPLOAD_SIZE_MB | upload via POST | 413; error message "Archivo excede el tamaño máximo de {N}MB" |
| Prod request gate | Flask MAX_CONTENT_LENGTH = 100MB | request Content-Length > 100MB | 413 before app code runs |
| Empty file | file = 0 bytes | upload via POST | 200 or 400 — existing behavior unchanged |

### R2: Session-Based Rate Limiting

The system MUST limit POST processing requests per session to `N` requests within a sliding `M`-second window. Exceeded requests SHALL return 429 with a "Demasiadas solicitudes. Espere {seconds} segundos." message. The rate limiter SHALL use `session["_rate_limiter"]` (list of timestamps) with no external dependencies.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Within limit | session has N-1 requests in current window | POST processing request | 200; request processed |
| Rate exceeded | session has N requests in current window | POST processing request | 429; request rejected |
| Window expired | session has N requests, oldest > M seconds ago | POST processing request | 200; old timestamp pruned, request processed |
| Independent sessions | session A at limit | session B POST | 200; independent counter |
| GET excluded | any session | GET request | 200; not counted |

### R3: Concurrency Semaphore

The system MUST limit simultaneous processing tasks to `MAX_CONCURRENT_PROCESSORS` (default 3) using a `threading.Semaphore`. If the semaphore cannot be acquired within `SEMAPHORE_TIMEOUT` seconds (default 30), the request SHALL return 503 with "Servidor ocupado. Intente nuevamente en unos momentos." All processing tasks MUST acquire the semaphore before starting and release it in a `finally` block — never leak the semaphore.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Under capacity | ≤ MAX_CONCURRENT_PROCESSORS tasks active | new processing request | semaphore acquired; processing starts |
| At capacity | MAX_CONCURRENT_PROCESSORS tasks active | new processing request | 503 after timeout; task not started |
| Task frees slot | MAX_CONCURRENT_PROCESSORS tasks active, one finishes | next queued request | 200; semaphore released; processing starts |
| Exception safety | processing task raises | exception raised | semaphore released in `finally`; no leak |

## Non-Functional Requirements

- **Logging**: Each layer MUST log with `[BACK]` prefix when a limit is reached.
- **Rollback**: Each layer MUST be independently revertible (separate commits).
- **Testing**: Each layer MUST have at least one unit test covering happy path and limit-exceeded path.
- **No external deps**: All layers MUST use only Python stdlib (`threading`, `time`, `dataclasses`).
