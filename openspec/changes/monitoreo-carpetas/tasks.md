# Tasks: Monitoreo de Carpetas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 750–950 (services + tests + frontend) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Backend foundation + detectors → PR 2: Scanner + orchestrator + report → PR 3: Route + frontend + wiring |
| Delivery strategy | ask-on-risk |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Constants + dataclasses + 4 detectors + tests | PR 1 | Pure logic, no IO. Independent. |
| 2 | Scanner + orchestrator + report generator + tests | PR 2 | Depends on Unit 1 types/detectors. IO-bound. |
| 3 | Route + frontend + blueprint registration + integration tests | PR 3 | Depends on Unit 2 orchestrator. Wire everything. |

## Phase 1: Foundation

- [x] 1.1 Create `app/constants/monitoreo_carpetas.py` — STATUS_KEYWORDS mapping, FEV/CAP regex, env var name, timeout defaults
- [x] 1.2 Create `app/services/monitoreo_carpetas/__init__.py` — `InvoiceRecord` and `ScanResult` dataclasses
- [x] 1.3 Create `tests/services/monitoreo_carpetas/conftest.py` — shared fixtures and sample data for detector tests

## Phase 2: Individual Detectors (TDD)

- [x] 2.1 Create `status_inferrer.py` — `infer_status()` with parametrized test for all keyword variants + default fallback
- [x] 2.2 Create `name_validator.py` — `validate_name()` with test for FEV/CAP/INVALID patterns, edge cases, case-insensitive
- [x] 2.3 Create `empty_folder_detector.py` — `detect_empty()` with test for empty, non-invoice-only, and valid folders
- [x] 2.4 Create `duplicate_detector.py` — `find_duplicates()` with test for 2-way, 3-way, and no-duplicate scenarios

## Phase 3: Scanner + Orchestrator + Report

- [x] 3.1 Create `folder_scanner.py` — `scan_all(roots)` with semaphore, per-facturador timeout, symlink skip, `tmp_path` test
- [x] 3.2 Create `detect_all.py` — orchestrator: acquire semaphore, call scanner + all detectors, assemble `ScanResult`
- [x] 3.3 Create `report_generator.py` — openpyxl Workbook with 2 sheets (Facturas + Indicadores), `formatting.py` styles

## Phase 4: Wiring + Frontend

- [x] 4.1 Create `app/routes/monitoreo_carpetas.py` — Blueprint: `POST /scan`, `GET /download/<filename>` with traversal guard
- [x] 4.2 Register `monitoreo_carpetas_bp` in `app/__init__.py` with url prefix `/monitoreo-carpetas`
- [x] 4.3 Create `frontend/src/pages/monitoreo-carpetas/` — index.html + main.tsx + page.tsx (trigger button, results table, download)
- [x] 4.4 Add entry point in `frontend/vite.config.ts` — `src/pages/monitoreo-carpetas/index.html`

## Phase 5: Integration Tests

- [x] 5.1 Write integration test for `detect_all()` — create fixture folder tree with known files, assert `ScanResult` fields match
- [x] 5.2 Write E2E test for Flask route — `app_client` fixture, `POST /monitoreo-carpetas/scan`, assert 200 + JSON + Excel file created
