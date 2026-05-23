# Tasks: Mejora de rendimiento de procesamiento de Excel y control de carga

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~290 (55 + 135 + 100) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: File Size layer → PR 2: Rate Limiter → PR 3: Concurrency Semaphore |
| Delivery strategy | ask-always |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | File Size validation (constants + config + save_temp_excel + tests) | PR 1 | Independent, base for all |
| 2 | Rate Limiter (processor_gate decorator + POST routes + tests) | PR 2 | Independent, on top of PR 1 |
| 3 | Concurrency Semaphore (processor_gate semaphore + exporter wrapper + tests) | PR 3 | Independent, on top of PR 2 |

---

## Phase 1: Foundation

- [x] 1.1 RED: Write failing test for `MAX_EXCEL_UPLOAD_SIZE_MB` constant import
- [x] 1.2 GREEN: Add `MAX_EXCEL_UPLOAD_SIZE_MB = 100` to `app/constants/base.py`
- [x] 1.3 GREEN: Set `MAX_CONTENT_LENGTH = 100 * 1024 * 1024` in `config/prod.py`
- [x] 1.4 REFACTOR: Verify both constants are importable and coherent

## Phase 2: File Size Layer

- [x] 2.1 RED: Write test for `save_temp_excel()` rejecting oversized file
- [x] 2.2 GREEN: Activate commented size validation in `app/utils/input_data.py` using `MAX_EXCEL_UPLOAD_SIZE_MB`
- [x] 2.3 REFACTOR: Ensure error message matches spec format — "Archivo excede el tamaño máximo de {N}MB"
- [x] 2.4 RED: Test Flask 413 for requests > 100MB (prod gate)
- [x] 2.5 GREEN: Prod gate already handled by `MAX_CONTENT_LENGTH` — verify passes

## Phase 3: Rate Limiter Layer

- [x] 3.1 RED: Write test for `@rate_limit(10, 60)` decorator — N+1 requests within window → 429
- [x] 3.2 GREEN: Create `app/services/processor_gate.py` with `rate_limit()` decorator using `session["_rate_limiter"]`
- [x] 3.3 RED: Test window expired — N+1th request after `>window` seconds → 200
- [x] 3.4 GREEN: Prune expired timestamps in decorator logic
- [x] 3.5 GREEN: Apply `@rate_limit(10, 60)` to `excel_headers.py` POST route
- [x] 3.6 GREEN: Apply `@rate_limit(10, 60)` to `urgencias.py` POST route
- [x] 3.7 REFACTOR: Verify session isolation — concurrent sessions have independent counters

## Phase 4: Concurrency Semaphore Layer

- [x] 4.1 RED: Write test for semaphore acquire/release — under capacity → success
- [x] 4.2 GREEN: Add `threading.Semaphore(3)` + `acquire_semaphore(timeout=30)` / `release_semaphore()` to `processor_gate.py`
- [x] 4.3 RED: Test semaphore at capacity → 503 after timeout
- [x] 4.4 GREEN: Wrap `detect_problems_only()` call in `exporter.py` with acquire/release in `try/finally`
- [x] 4.5 RED: Test exception safety — task raising releases semaphore
- [x] 4.6 GREEN: Verify `finally` block guarantees release on any exit path
- [x] 4.7 REFACTOR: Add `[BACK]` logging at each semaphore acquire/release

## Phase 5: Integration

- [x] 5.1 Stacked test: Upload file < limit, stay under rate limit, acquire semaphore → 200
- [x] 5.2 Stacked test: Oversized file → 413 before rate or semaphore check
- [x] 5.3 Stacked test: Rate exceeded → 429 before semaphore check
- [x] 5.4 Verify `logger.info("[BACK] ...")` appears in logs for each layer trigger
