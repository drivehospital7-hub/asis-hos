# Design: Monitoreo Watchdog Automático

## Technical Approach

Lazy-start watchdog on first `POST /scan`. `FolderWatcher` module-level singleton wraps `watchdog.observer` in a daemon thread. First call: full scan + observer start. Subsequent calls: health check or fallback full scan if observer dead. In-memory `ScanResult` protected by `threading.Lock`. Watchdog events trigger incremental subtree re-scan via `_scan_dir_controlled`, with merge logic that removes stale entries, appends new, recalculates indicators under lock.

## Architecture Decisions

| Decision | Options | Tradeoff | Chosen |
|----------|---------|----------|--------|
| Lifecycle | Module-level in routes vs. standalone module | Routes stay thin; watcher independently testable | **watcher.py singleton** — no app startup hooks, clean lazy init |
| Incremental strategy | Full facturador re-scan vs. targeted subtree | Full scan is wasteful for deep trees; targeted is accurate | **Targeted subtree** — re-scan only changed path, merge into ScanResult |
| Handler pattern | PatternMatchingEventHandler per root vs. single FileSystemEventHandler | Single handler is simpler; per-root isolates errors | **Single FileSystemEventHandler** — routes all events, filters by root prefix |
| Lock model | RLock vs. Lock | Lock is lighter; no recursive call pattern expected | **threading.Lock** — all ScanResult writes/reads under same lock |
| Health response | Return cached ScanResult vs. minimal status | Spec says monitoring status only; cached data is deferred feature | **Minimal health status** — `{"monitoring": true}`, 200, no scan data |
| ScanResult merge | Full replace vs. diff-based update | Diff is correct for concurrent events; replace is simpler | **Diff-based** — remove entries whose `full_path` starts with event path, append re-scanned entries |

## Data Flow

```
First POST /scan:
  route → watcher.first_scan(roots)
    ├─ detect_all(roots) → ScanResult          # full scan (as today)
    ├─ generate_excel(result) → .xlsx          # existing
    ├─ watcher.set_result(result) [LOCK]       # cache
    ├─ watcher.start_observer(roots)           # daemon thread
    └─ return {status, data, excel_download}   # response

Subsequent POST /scan:
  route → watcher.health_check()
    ├─ observer.is_alive()?
    │   YES → return {status: "success", data: {monitoring: True}}
    │   NO  → detect_all(roots) → full scan → Excel → return (fallback)
    └─ return response

Watchdog on_any_event (background daemon thread):
  handler → watcher.update_subtree(event.src_path)
    ├─ extract root from path prefix
    ├─ _scan_dir_controlled(path, root, 0, ...)  [LOCK held]
    ├─ remove existing entries matching path prefix
    ├─ append new entries from re-scan
    ├─ re-run find_duplicates on affected facturadores
    ├─ recalculate indicadores
    └─ release LOCK
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/monitoreo_carpetas/watcher.py` | Create | `FolderWatcher` class — first_scan, health_check, update_subtree, observer lifecycle, ScanResult cache with Lock |
| `app/routes/monitoreo_carpetas.py` | Modify | `POST /scan` delegates to watcher singleton; first-call vs subsequent dispatch |
| `app/services/monitoreo_carpetas/detect_all.py` | Modify | Extract `recalculate_indicators(ScanResult) -> dict` so FolderWatcher reuses it without importing scan internals |
| `app/services/monitoreo_carpetas/folder_scanner.py` | Modify | Rename `_scan_dir_controlled` → `scan_subtree` (public) for incremental use from watcher.py |
| `app/constants/monitoreo_carpetas.py` | Modify | Add watchdog constants: `WATCHDOG_POLL_INTERVAL`, `WATCHDOG_EVENT_TYPES` |
| `requirements.txt` | Modify | Add `watchdog>=4.0.0` |

### watcher.py structure

```python
class FolderWatcher:
    def __init__(self):
        self._result: ScanResult | None = None
        self._observer: Observer | None = None
        self._lock = threading.Lock()
        self._roots: list[str] = []

    def first_scan(self, roots: list[str]) -> tuple[ScanResult, str | None]:
        """Full scan + Excel + observer start. Returns (result, excel_filename)."""

    def health_check(self) -> dict:
        """Returns monitoring status or triggers fallback full scan."""

    def set_result(self, result: ScanResult) -> None: ...
    def get_result(self) -> ScanResult | None: ...
    def update_subtree(self, path: str) -> None:
        """Re-scan affected subtree, merge into ScanResult under lock."""
```

## Interfaces / Contracts

```python
# NEW - watcher.py
def scan_subtree(path: str, root: str, invoices, empty_folders, errors) -> None
# Public from folder_scanner (was _scan_dir_controlled)

# NEW - detect_all.py
def recalculate_indicators(result: ScanResult) -> dict
# Extracted from detect_all() for reuse by watcher
```

The `FolderWatcher` lifecycle: `None` (initial) → `first_scan()` called → result cached + observer daemon running → `update_subtree()` on each watchdog event → `health_check()` on subsequent requests.

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | FolderWatcher result thread safety | Inject ScanResult, concurrent read/write via Lock, verify no race |
| Unit | update_subtree merge | Temp dir → partial modify → verify ScanResult entries correct |
| Unit | Observer lifecycle (start, is_alive, stop) | Mock `watchdog.Observer`, verify start called once, is_alive checked |
| Integration | Existing tests unchanged | All existing `test_folder_scanner.py`, `test_detect_all.py` pass without modification |
| Risk | Watchdog on SMB unreliable | Health check on every request + fallback to full scan restores normal operation |
| Risk | Thread safety | Single `threading.Lock` for all ScanResult access — verified by test |

## Migration / Rollback

No migration required. Rollback: restore `POST /scan` to original sync full scan, delete `watcher.py`, remove `watchdog` from requirements. All existing tests pass without modification either way.

## Open Questions

- None. Fully resolved.
