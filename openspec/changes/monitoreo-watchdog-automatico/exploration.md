## Exploration: monitoreo-watchdog-automatico

### Current State

The `/monitoreo-carpetas` feature is implemented as a fully synchronous, button-triggered full-scan system:

1. **Route**: `app/routes/monitoreo_carpetas.py` — Blueprint with `POST /scan` (full scan), `GET /download/<filename>` (Excel export), and `GET /` (React shell).

2. **Scan Pipeline** (all synchronous, in-request):
   - `POST /scan` → reads roots from `MONITOREO_CARPETAS_ROOTS` env var
   - Calls `detect_all(roots)` → `scan_all(roots)` → uses `ThreadPoolExecutor` (max_workers=3) per root
   - `_scan_root()` → `_scan_dir_controlled()` uses `os.scandir()` depth-first (max depth=6)
   - On each invoice folder (FEV/CAP match): infers status, validates name, checks empty
   - Results assembled into in-memory `ScanResult` dataclass — **ephemeral, no DB persistence**
   - After scan: generates Excel via `generate_excel()`, returns JSON to frontend

3. **Why first scan is slow**:
   - Network UNC paths (SMB) — `os.scandir()` over network is inherently slow
   - `MAX_CONCURRENT_SCANS=3` limits parallelism
   - Each root timeout: `SCAN_TIMEOUT_PER_FACTURADOR=120s`
   - Controlled depth traversal still enumerates potentially thousands of network dirs

4. **Current frontend**: React page (`page.tsx`) with "Iniciar Escaneo" button that POSTs to `/scan` and renders results table. No polling, no auto-refresh, no real-time updates.

5. **No existing background/async infrastructure**:
   - No Celery, no background threads, no asyncio, no SSE, no WebSocket
   - Only `ThreadPoolExecutor` for parallel scanning within a request
   - `threading.Semaphore` in `processor_gate.py` for rate limiting
   - Waitress WSGI (sync) in prod; Flask dev server in dev
   - **No way to run background work without adding it**

6. **Watchdog**: **NOT installed**. Not in `requirements.txt`, not in pip freeze. Would need `pip install watchdog`.

7. **Architecture constraints**:
   - `create_app()` factory pattern in `app/__init__.py` — no hooks for app startup lifecycle
   - `run_prod.py` (waitress.serve) is a simple server — no process manager for background threads
   - `run_dev.py` (Flask dev server) — same limitation
   - No state management layer — scan results are computed fresh each time

### Affected Areas

- `app/services/monitoreo_carpetas/detect_all.py` — Refactor orchestration to support incremental detection from changed paths instead of only full scans
- `app/services/monitoreo_carpetas/folder_scanner.py` — Refactor scanner into (a) full scan + (b) incremental path-level scan; need to make detection functions work on single paths, not just entire root
- `app/services/monitoreo_carpetas/__init__.py` — Add stateful watcher class (e.g. `FolderWatcher`) that holds latest ScanResult and watchdog observer
- `app/routes/monitoreo_carpetas.py` — Replace sync POST /scan with cached-state read; add WebSocket/SSE endpoint or status polling endpoint
- `app/constants/monitoreo_carpetas.py` — Add watchdog-related constants (polling interval for network shares, event types to watch)
- `app/__init__.py` — Add app startup hook to initialize watcher (or lazily on first scan)
- `frontend/src/pages/monitoreo-carpetas/page.tsx` — Add WebSocket client or status polling; show real-time change indicators
- `frontend/src/pages/monitoreo-carpetas/main.tsx` — May need WebSocket provider
- `frontend/package.json` — May need dependency (e.g. `react-use-websocket` or plain `EventSource`)
- `requirements.txt` — Add `watchdog>=4.0.0`
- `run_dev.py` / `run_prod.py` — May need to support background watcher thread lifecycle
- Existing tests under `tests/services/monitoreo_carpetas/` — All tests assume stateless/all-new scan; must add tests for incremental/delta detection

### Approaches

1. **Watchdog background thread (lazy start on first scan)**
   - On first `POST /scan`: do full scan synchronously (as today), then start a `watchdog.observer` in a daemon thread
   - Watchdog watches each configured root directory for `on_created`, `on_deleted`, `on_modified`, `on_moved` events
   - Events trigger incremental re-scan of only the affected subdirectory/subtree
   - `ScanResult` is held in-memory and updated incrementally
   - Subsequent `POST /scan` calls just return cached state (instant)
   - Optionally add `GET /events` SSE endpoint for real-time frontend updates
   - Pros:
     - Real-time change detection (sub-second for local filesystems)
     - No wasted full rescans after first
     - Keeps the "button" but makes it instant
     - Minimal architectural change — watcher is self-contained
   - Cons:
     - Watchdog on Windows SMB/UNC network paths is unreliable — `ReadDirectoryChangesW` on mapped drives works, but UNC paths (`\\server\share`) may require drive letter mapping
     - Network disconnects can cause watchdog to silently stop or miss events
     - Background thread lifecycle in WSGI is not clean — no shutdown hooks in waitress
     - In-memory state is lost on server restart (acceptable tradeoff)
     - Thread safety — `ScanResult` mutation from watchdog thread + reads from Flask request threads
   - Effort: **Medium**

2. **Watchdog + SSE with persistent snapshot**
   - Same as #1, but:
     - Cache `ScanResult` to a JSON/Excel snapshot file so state survives restart
     - Add `GET /events` SSE endpoint that streams change events to connected browsers
     - Frontend subscribes to SSE and live-updates the table (no button needed after first scan)
   - Pros:
     - Full real-time UX: files appear/disappear on the page as changes happen
     - State survives server restart
     - SSE is simple (no WebSocket protocol, just HTTP streaming)
   - Cons:
     - SSE needs eventlet/gevent monkey-patching for waitress (or Flask dev server works)
     - More moving parts: snapshot persistence, SSE endpoint, frontend EventSource client
     - Same watchdog SMB reliability issues as #1
     - SSE connection management (reconnect, stale clients)
   - Effort: **High**

3. **Periodic background scan (no watchdog)**
   - After first full scan, launch a background thread that rescans at configurable intervals (e.g. every 30s)
   - Compare results with previous snapshot — only return delta
   - No external dependency needed (stdlib `threading` + `time.sleep`)
   - Pros:
     - Zero new dependencies — works with SMB/UNC natively
     - Predictable behavior — no silent failures
     - Simpler to implement and test
     - Thread safety is still needed but simpler (no event queue)
   - Cons:
     - Not real-time — up to 30s delay
     - Still doing full rescans (though in background, no request blocking)
     - Network load from repeated rescans
   - Effort: **Low-Medium**

4. **Hybrid: watchdog for local/mapped drives + periodic fallback for UNC**
   - Use watchdog when possible (mapped drives, local paths)
   - Fall back to periodic scan when watchdog observer reports errors or for UNC paths
   - Configurable per-root: `watch_method = "auto" | "watchdog" | "poll"`
   - Pros:
     - Best-effort real-time where possible, reliable fallback otherwise
     - Graceful degradation
   - Cons:
     - Most complex implementation
     - Need to detect when watchdog has failed (network drop)
     - Two code paths to maintain
   - Effort: **High**

### Recommendation

**Approach #2 (Watchdog + SSE with snapshot)** is the right end-state, but given the current codebase maturity and watchdog SMB limitations, **Approach #1 (Watchdog background thread, in-memory state, lazy start)** is the most pragmatic first step:

- It keeps the button-based interaction but makes subsequent scans instant
- It introduces background processing via `threading.Thread` (already used elsewhere for `ThreadPoolExecutor`)
- It allows incremental step-by-step evolution toward full real-time
- SSE/persistent snapshot can be added in a follow-up change
- The main risk (watchdog SMB reliability) is isolated and can be handled with try/except fallback to full rescan

Technical sketch for Approach #1:

```python
# app/services/monitoreo_carpetas/watcher.py (NEW)
class FolderWatcher:
    """Manages the full scan + watchdog-based incremental updates."""
    
    def __init__(self):
        self._result: ScanResult | None = None
        self._observer: Observer | None = None
        self._lock = threading.Lock()
    
    def start_watching(self, roots: list[str]) -> None:
        """Start watchdog observer after first scan."""
        event_handler = FolderChangeHandler(self)
        self._observer = Observer()
        for root in roots:
            self._observer.schedule(event_handler, root, recursive=True)
        self._observer.start()
    
    def set_result(self, result: ScanResult) -> None:
        with self._lock:
            self._result = result
    
    def get_result(self) -> ScanResult | None:
        with self._lock:
            return self._result
    
    def handle_change(self, path: str, event_type: str) -> None:
        """Re-scan affected paths incrementally, update in-memory state."""
        # partial rescans of just the changed subtree
        ...
```

```python
# app/routes/monitoreo_carpetas.py
# On first POST /scan: full scan + start watcher
# On subsequent POST /scan: return cached state immediately
_watcher = FolderWatcher()

@monitoreo_carpetas_bp.post("/scan")
def trigger_scan():
    if _watcher.has_result():
        return jsonify({"status": "success", "data": _watcher.serialize_result()})
    # first scan: full pipeline
    ...
    _watcher.start_watching(roots)
```

### Risks

- **Watchdog reliability on SMB/UNC**: Windows `ReadDirectoryChangesW` works on mapped drives but is unreliable on raw UNC paths. Network disconnects can stop the observer silently. **Mitigation**: Use mapped drive letters where possible; add watchdog health check + auto-recovery; fall back to full rescan on observation errors.
- **Thread safety**: Watchdog runs in a background thread; Flask request handlers read `ScanResult` concurrently. **Mitigation**: Use `threading.Lock` for all `ScanResult` reads/writes.
- **Background thread lifecycle**: No clean shutdown on server stop (waitress doesn't provide hooks). **Mitigation**: Use daemon threads (`daemon=True`) so they die with the main process.
- **In-memory state loss**: Server restart loses cached scan. **Mitigation**: Acceptable — first scan after restart does a full scan. Can be mitigated later with JSON/Excel snapshot.
- **Watchdog not in requirements**: Must add `watchdog` dependency. **Mitigation**: Pin version, test install.
- **Partial re-scan accuracy**: Re-scanning just a subtree may miss cascade effects (e.g., a deleted folder may remove a duplicate pair from two facturadores). **Mitigation**: When a change event fires on a subtree, re-run `detect_all()` but only on the affected facturador roots, not all roots. Full scan fallback if inconsistencies detected.
- **Scanned files growth over time**: As more invoice folders accumulate, first scan gets slower. No incremental improvement for first scan (it's still O(n)). **Mitigation**: Acceptable — first scan is a one-time cost per server start.

### Ready for Proposal

Yes — the change is well-defined and the current codebase is fully understood. The recommendation is Approach #1 (Watchdog background thread, in-memory state, lazy start on first scan) as a pragmatic first step that can evolve toward full real-time later.
