# Tasks: Optimizar Escaneo

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~275 (scanner ~150, __init__ ~10, conftest ~30, test_folder_scanner ~40, test_dataclasses ~15, test_integration ~30) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR — all phases fit well under 400-line budget |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full scanner optimization | Single PR | ~275 lines; TDD per phase; all existing detection stays green |

## Phase 1: Foundation — InvoiceRecord Cleanup

- [x] 1.1 (RED) `tests/.../test_dataclasses.py`: Remove `test_create_invoice_record_with_doc_fields`; update field set assertion to exclude `doc_type`/`doc_number`
- [x] 1.2 (RED) `tests/.../test_folder_scanner.py`: Remove all assertions referencing `doc_type`/`doc_number` on InvoiceRecord instances
- [x] 1.3 (RED) `tests/.../conftest.py` + `tests/.../test_integration.py`: Strip `doc_type`/`doc_number` kwargs from InvoiceRecord constructors in fixtures
- [x] 1.4 (GREEN) `app/.../__init__.py`: Remove `doc_type: str | None = None` and `doc_number: str | None = None` from InvoiceRecord dataclass
- [x] 1.5 (GREEN) `app/.../folder_scanner.py`: Remove `doc_type`/`doc_number` extraction (lines 92–97) and kwargs from InvoiceRecord() call (lines 107–108)
- [x] 1.6 Run `pytest tests/services/monitoreo_carpetas/test_dataclasses.py -v` → all green

## Phase 2: Core — Scanner Rewrite (folder-level + parallel + pre-filter)

- [x] 2.1 (RED) `tests/.../conftest.py`: Rewrite `temp_scan_root()` to multi-level tree: `root/facturador/mid/FEV12345/dummy.txt`. Add non-invoice folders `CRC_01/`, `HAU_02/` at leaf.
- [x] 2.2 (RED) `tests/.../test_folder_scanner.py`: Update assertions — `filename` = folder name (no `.pdf`), `full_path` = folder path. Add tests: pre-filter excludes CRC_/HAU_, empty invoice folder skipped, parallel 2-root aggregation. Remove PDF filename assertions.
- [x] 2.3 (GREEN) `app/.../folder_scanner.py`: Rewrite `_scan_root_walk()` — `os.walk()` to depth ~4; `folder_name.upper().startswith(("FEV","CAP"))` pre-filter; `os.listdir()` non-empty; `validate_name(folder_name)`; `InvoiceRecord(filename=folder_name, full_path=folder_path)`.
- [x] 2.4 (GREEN) `app/.../folder_scanner.py`: Import `ThreadPoolExecutor` + `TimeoutError`. Wrap roots loop with `executor(max_workers=min(MAX_CONCURRENT_SCANS, len(roots)))`. Per-thread dict aggregation; post-join sequential merge. `future.result(timeout=SCAN_TIMEOUT_PER_FACTURADOR)`.
- [x] 2.5 (REFACTOR) Remove dead PDF-level comments + docstrings. Remove `_infer_status_from_parts` if unused.
- [x] 2.6 Run `pytest tests/services/monitoreo_carpetas/test_folder_scanner.py -v` → all green

## Phase 3: Integration Tests

- [x] 3.1 (RED) `tests/.../test_integration.py`: Rewrite `complex_scan_tree` to depth ~4 with invoice folders (FEV001, CAP001_CC123, CAP002_TI456, FEV002, FEV003) + non-invoice CRC_01 + empty FEV_EMPTY. Update E2E inline temp trees similarly.
- [x] 3.2 Update assertions: `filename` = folder name, `full_path` = folder path, empty folder at invoice-folder level (spec R4). Keep indicadores + duplicate detection assertions.
- [x] 3.3 (GREEN) Run `pytest tests/services/monitoreo_carpetas/test_integration.py -v` → all green
- [x] 3.4 Run full module suite: `pytest tests/services/monitoreo_carpetas/ -v` → 100% green

## Phase 4: Verification

- [x] 4.1 Verify untouched tests stay green: `pytest tests/services/monitoreo_carpetas/test_name_validator.py test_detect_all.py test_duplicate_detector.py -v`
- [x] 4.2 Verify E2E endpoints: Flask POST `/monitoreo-carpetas/scan` → 200 + valid JSON; GET `/download/<file>` → serves xlsx
- [x] 4.3 Run full project: `python -m pytest -v` — zero regressions
- [x] 4.4 Manual sanity: scan time reduced ≥60% vs baseline, same invoice count detected (zero data loss per proposal success criteria)
