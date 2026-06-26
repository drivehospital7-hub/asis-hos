# Design: Optimizar Escaneo

## Technical Approach

Replace PDF-level scanning with folder-level detection: walk to depth ~4, match folder names (FEV*/CAP*) via `startswith` pre-filter + regex, verify non-empty via `os.listdir()`. Parallelize root scanning with `ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_SCANS, len(roots)))`. Remove unused `doc_type`/`doc_number` fields. Keeps `os.walk()` (C-level traversal). Same `ScanResult` contract — downstream consumers unchanged.

## Architecture Decisions

| Decision | Options Considered | Choice & Rationale |
|---|---|---|
| **Parallelism** | `ThreadPoolExecutor` vs manual threads vs `ProcessPoolExecutor` | **ThreadPoolExecutor**. SMB I/O is latency-bound → GIL irrelevant. Clean `future.result(timeout=30)` per root. Constants (`MAX_CONCURRENT_SCANS`, `SCAN_TIMEOUT_PER_FACTURADOR`) already defined — no new config. |
| **Thread-safe aggregation** | Shared list + lock vs per-thread dict + post-join merge vs `queue.Queue` | **Per-thread dict + post-join merge**. Roots are completely independent (no shared state during scan). Workers return `dict[str, Any]`; main thread merges sequentially after all futures complete. Deterministic, lock-free, trivially correct. |
| **Timeout handling** | Cancel future vs retry vs log error and skip | **`future.result(timeout=30)` → catch `TimeoutError`, log as error entry, continue**. Same pattern as existing non-existent-dir error handling. Partial results lost — acceptable (next scan cycle retries). |
| **Folder-level detection** | `os.scandir()` recursion vs depth-limited `os.walk()` vs parent-name inference | **Depth-limited `os.walk()` with `startswith` pre-filter**. `os.walk()` stays (C-level, proposal scope). At leaf dirs: `os.listdir()` non-empty + `folder_name.upper().startswith(("FEV","CAP"))` bypasses regex for non-invoice folders. `validate_name()` regex still runs on matching names. |

## Data Flow

```
Root paths (list[str])
  │
  ├─[ThreadPool]──→ _scan_root_walk(root_A) ──→ {invoices, errors, ...}
  ├─[ThreadPool]──→ _scan_root_walk(root_B) ──→ {invoices, errors, ...}
  └─[ThreadPool]──→ _scan_root_walk(root_C) ──→ {invoices, errors, ...}
                          │
                   ┌──────┴───────┐
                   │ Post-join    │ sequential merge (no locks)
                   │ Aggregation  │
                   └──────┬───────┘
                          ▼
                    ScanResult (unchanged)
                          │
                   ┌──────┼───────┐
               route   report   duplicate_detector
            (no changes needed — same InvoiceRecord shape)
```

`_scan_root_walk()` internal flow:
```
os.walk(root) → traverse ~4 depth
  └─ at leaf dir (no subdirs / depth limit):
       └─ folder_name.upper().startswith(("FEV","CAP"))?
            ├─ No → skip
            └─ Yes → os.listdir(path) non-empty?
                  ├─ No → skip (empty invoice folder → logged)
                  └─ Yes → validate_name(folder_name) → InvoiceRecord(
                               filename=folder_name,       # NEW: folder name, not PDF name
                               facturador=<inferred>,
                               full_path=<folder_path>,    # NEW: folder path, not PDF path
                               status=<inferred>,
                               invoice_type=<FEV|CAP>,
                               invoice_code=folder_name    # NEW: folder name IS code
                           )
```

## File Changes

| File | Action | Description |
|---|---|---|
| `app/services/monitoreo_carpetas/__init__.py` | **Modify** | Remove `doc_type`, `doc_number` from `InvoiceRecord` (dead fields — zero consumers). |
| `app/services/monitoreo_carpetas/folder_scanner.py` | **Modify** | Replace sequential `for rp in root_paths` with `ThreadPoolExecutor`. Refactor `_scan_root_walk()`: folder-level detection instead of PDF enumeration. Add `startswith` pre-filter before regex. Update `empty_folders` detection to new semantics. |
| `app/services/monitoreo_carpetas/name_validator.py` | **No change** | Same FEV/CAP regex patterns. `validate_name()` now receives folder names instead of PDF filenames — behavior unchanged. |
| `app/services/monitoreo_carpetas/detect_all.py` | **No change** | Consumes `scan_all()` → `ScanResult`. Contract unchanged. |
| `tests/services/monitoreo_carpetas/conftest.py` | **Modify** | Restructure `temp_scan_root()` fixture to multi-level tree (depth ~4): `root/facturador/company/invoice_folder/file`. Add non-invoice folders (CRC_, HAU_) for pre-filter testing. |
| `tests/services/monitoreo_carpetas/test_folder_scanner.py` | **Modify** | Update assertions to new semantics: `filename` = folder name (not PDF), `full_path` = folder path. Add tests for parallel scanning and empty folder detection. |
| `tests/services/monitoreo_carpetas/test_dataclasses.py` | **Modify** | Remove `test_create_invoice_record_with_doc_fields`. No other test references `doc_type`/`doc_number`. |
| `tests/services/monitoreo_carpetas/test_integration.py` | **Modify** | Update `complex_scan_tree` fixture to multi-level structure matching new scan semantics. |

## Interfaces / Contracts

**Updated `InvoiceRecord`** (fields removed — NO new fields added):
```python
@dataclass
class InvoiceRecord:
    filename: str       # Changed semantics: folder name (e.g. "FEV416488"), not PDF filename
    facturador: str     # Unchanged
    full_path: str      # Changed semantics: folder path, not PDF path
    status: str         # Unchanged
    invoice_type: str   # Unchanged
    invoice_code: str   # Changed semantics: folder name IS the code
    # doc_type: removed
    # doc_number: removed
```

`ScanResult` is **unchanged** — same fields, same types, same contract for downstream.

`scan_all(root_paths: list[str]) -> ScanResult`: **signature unchanged**. Internal implementation is threaded; external contract is identical.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| **Unit** | Folder-level detection: `startswith` pre-filter rejects CRC_/HAU_/OPF_ folders; empty folder skipped; valid FEV/CAP folder detected | Test `_scan_root_walk()` with multi-level `tmp_path` fixture. Assert invoice count, folder names in `filename`, no PDF references. |
| **Unit** | Parallel aggregation: 2 roots → merged results | Test `scan_all()` with 2 temp roots. Verify results from both roots present, no duplicates, no cross-contamination. |
| **Unit** | Timeout isolation: slow root doesn't block others | Mock `os.walk()` with `time.sleep(35)` on one root. Assert timeout error logged, other root results intact. |
| **Unit** | `InvoiceRecord` without `doc_type`/`doc_number` | Assert field set excludes both; construction without them works. |
| **Integration** | `detect_all()` full pipeline with multi-level tree | Update `complex_scan_tree` fixture to depth ~4. Assert invoice count, types, statuses, empty folders match expectations. |
| **Regression** | `name_validator` unchanged | All 11 existing tests remain green (regex patterns unchanged). |
| **E2E** | Flask `/scan` and `/download` endpoints | Test with env-configured multi-level roots. Assert 200, valid JSON, download serves xlsx. |

## Migration / Rollout

No migration required. Rollback: revert `folder_scanner.py`, `__init__.py`, and test fixtures. `name_validator.py` and `detect_all.py` untouched — risk isolated to scanner module. API contract unchanged (same `ScanResult` shape).

## Open Questions

- [ ] Should empty invoice folders (named FEV*/CAP* but containing zero files) be reported as errors or `vacias`? Proposal says "marcar como vacía" but current `vacias` semantics are first-level dirs. Needs user clarification.
- [ ] Max depth of 4 levels (root/facturador/company/invoice) — is this invariant, or can some roots have 3 or 5 levels? If variable, need depth-flexible leaf detection.
