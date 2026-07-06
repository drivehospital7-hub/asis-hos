# Tasks: Monitoreo Watchdog Automático

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 150-170 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Foundation — TDD

### scan_subtree — public API

- [x] 1.1 [RED] Write test: `scan_subtree(path, root)` scans a subpath independently and returns entries
- [x] 1.2 [GREEN] Rename `_scan_dir_controlled` → `scan_subtree` in folder_scanner.py, update callers

### recalculate_indicators — extract from detect_all

- [x] 1.3 [RED] Write test: `recalculate_indicators(ScanResult)` returns correct indicadores dict
- [x] 1.4 [GREEN] Extract `recalculate_indicators()` from `detect_all()` into standalone function

### Config & dependencies

- [x] 1.5 Add `watchdog>=4.0.0` to requirements.txt
- [x] 1.6 Add `WATCHDOG_POLL_INTERVAL` and `WATCHDOG_EVENT_TYPES` to constants/monitoreo_carpetas.py

## Phase 2: FolderWatcher — TDD

### RED — tests first

- [x] 2.1 [RED] Test: FolderWatcher thread safety — concurrent threads read/write ScanResult via Lock, no race
- [x] 2.2 [RED] Test: `update_subtree(path)` re-scans path, removes stale entries, appends fresh, recalculates indicators
- [x] 2.3 [RED] Test: `health_check()` returns `monitoring` when observer alive; triggers fallback full scan when dead

### GREEN — implement

- [x] 2.4 [GREEN] Create `watcher.py`: `FolderWatcher.__init__` with threading.Lock, ScanResult cache, Observer ref, roots list
- [x] 2.5 [GREEN] Implement `first_scan(roots)`: detect_all → Excel → set_result → start observer daemon → return
- [x] 2.6 [GREEN] Implement `update_subtree(path)`: scan_subtree → merge entries under Lock → recalculate_indicators
- [x] 2.7 [GREEN] Implement `health_check()`: observer.is_alive() → monitoring response or fallback full scan
- [x] 2.8 [GREEN] Implement `set_result(result)` / `get_result()` thread-safe accessors with Lock

## Phase 3: Route Wiring

- [x] 3.1 Modify `POST /scan` in routes/monitoreo_carpetas.py: first call → watcher.first_scan(); subsequent → watcher.health_check()

## Phase 4: Verification

- [x] 4.1 Run full test suite; confirm all existing tests pass + new watcher tests pass
