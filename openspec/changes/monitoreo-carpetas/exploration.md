## Exploration: monitoreo-carpetas

### Current State

**File system / directory scanning:**
The system has NO existing infrastructure for scanning shared network folders. Only two directory traversal patterns exist:
- `app/utils/input_data.py` — iterates over `app/data/input/` (local) for Excel files via `iterdir()`
- `app/routes/derechos.py` — uses `os.walk()` to recursively scan for PDF files in a configurable base path

Network paths (UNC) and shared drives are not handled anywhere. `derechos.py` references WSL UNC paths in comments but has no UNC abstraction.

**Excel processing architecture:**
- `app/services/exporter.py` — only detects problems as JSON (no Excel writing). Uses Polars to read, then `_SimpleSheet` wrapper
- `app/services/transversales/create_revision_sheet.py` — creates the "Revision" sheet with openpyxl using header/data style helpers
- `app/utils/formatting.py` — style helpers (header styles, data row styles, auto-width)
- No `cruce_sheet.py` exists (the file mentioned in AGENTS.md is planned or was removed)

**Domain pattern:**
Each area (odontologia/urgencias/equipos_basicos) has:
- Constants in `app/constants/{area}.py`
- A `detect_all.py` orchestrator in `app/services/{area}/`
- Individual detectors as separate files
- A `normalized_rows.py` for 6-column normalization
- A route file in `app/routes/` that receives upload → saves temp → delegates to `exporter.detect_problems_only()`

**Database models:**
- `app/database.py` — lazy SQLAlchemy engine with PostgreSQL (env-configured)
- `app/models.py` — User, UserArea, EpsContratado, Procedimiento, NotaHoja, NotasTecnicas, EpsNota
- No models for folders, files, or scan metadata — all new

**Frontend:**
- React + Vite + Tailwind CSS + shadcn/ui + Lucide icons — MPA (multi-page app) with 12 page entry points
- Each page follows: upload form → POST → show grouped error tables (6-column display)
- Components: `app-layout`, `app-sidebar`, `app-header`, `page-title`, `status-badge`, `breadcrumbs`, `ConfirmDialog`, shadcn/ui primitives

**Specs:**
- `openspec/specs/odontologia-equipos-basicos/spec.md` shows the Given/When/Then + RFC 2119 pattern
- 10 spec directories, 14 active changes in `openspec/changes/`

### Affected Areas

- `app/services/monitoreo_carpetas/` — **New service package** — scanner core: orchestrator, detectors (duplicates, invalid names, empty folders), status inference logic
- `app/constants/monitoreo_carpetas.py` — **New constants** — invoice patterns (FEV: `FEV\d+`, CAP: `CAP\d+_\w+\d+`), status folder names, threshold values
- `app/routes/monitoreo_carpetas.py` — **New blueprint** — endpoints for scan trigger, status dashboard, report download
- `app/services/exporter.py` — Affected if monitoreo needs to export Excel reports alongside detection
- `app/utils/input_data.py` — Reference only: path resolution patterns. **Not directly affected** (works on local paths only)
- `app/database.py` / `app/models.py` — Potentially: new models for folder metadata, scan history, status snapshots
- `frontend/src/pages/monitoreo-carpetas/` — **New page** — dashboard with indicators, alerts, tables
- `frontend/vite.config.ts` — Add new page entry point for monitoreo-carpetas
- `openspec/specs/monitoreo-carpetas/spec.md` — **New spec** — defines behavior for scanning, status inference, anomaly detection, reporting
- `app/utils/db_config.py` — Reference only: new model + migration if persisting scans

### Approaches

1. **Standalone scanner service (recommended)** — Create `app/services/monitoreo_carpetas/` as a new domain package following the existing SRP + orchestrator pattern
   - Pros:
     - Consistent with existing architecture (SRP per detector, detect_all.py orchestrator)
     - Zero risk to existing domains (odontologia/urgencias/equipos_basicos)
     - Reuses transversales patterns (`column_indices`, `normalize_invoice`)
     - Status inference logic is cleanly isolated
   - Cons:
     - New package means creating constants, routes, tests from scratch
     - No existing model for directory scanning to copy from
   - Effort: **Medium** (new domain but established patterns)

2. **Extend exporter.py** — Add folder scanning capabilities to the existing `exporter.py` orchestrator
   - Pros:
     - Reuses existing semaphore/rate-limit/upload machinery
     - Single entry point for all processing
   - Cons:
     - Violates SRP: exporter handles Excel processing, not folder scanning
     - Makes `exporter.py` depend on network paths (security risk)
     - Mixed concerns make testing harder
     - Unclear how to handle ~15 independent scanning targets
   - Effort: **Medium-High** (fighting existing abstractions)

3. **Separate CLI script + Flask trigger** — Implement scanning as a standalone Python script invoked via subprocess or scheduled task, with results written to DB
   - Pros:
     - Cleanest separation of concerns
     - Can run as scheduled task (Windows Task Scheduler) without Flask
     - No impact on existing Flask hotpath
   - Cons:
     - Adds deployment complexity (scheduler setup, script path config)
     - No real-time status updates
     - Duplicates auth/permission logic if results need per-user views
     - Breaks from established pattern (all processing runs in-process via Flask)
   - Effort: **Medium** (standalone script) + integration complexity

### Recommendation

**Approach 1 — Standalone scanner service package.**

This follows the established domain pattern (odontologia/urgencias/equipos_basicos → monitoreo_carpetas) and keeps zero risk to existing modules. The scanner is architecturally a "domain" like any other — it has its own detectors, own constants, own route, and own orchestrator. The only difference is the input source: instead of an uploaded Excel, the input is a network directory tree.

Structure:

```
app/
├── constants/
│   └── monitoreo_carpetas.py     # NEW
├── services/
│   └── monitoreo_carpetas/       # NEW
│       ├── __init__.py
│       ├── detect_all.py         # orchestrator
│       ├── folder_scanner.py     # walks network dirs, lists facturadores
│       ├── status_inferrer.py    # infers status from folder path
│       ├── duplicate_detector.py # same invoice in multiple folders
│       ├── name_validator.py     # validates FEV/CAP patterns
│       ├── empty_folder.py       # detects empty folders
│       └── report_generator.py   # Excel report with openpyxl
├── routes/
│   └── monitoreo_carpetas.py     # NEW blueprint
```

Key design decisions for proposal:
- Invoice status inference is pure data: status = f(parent_folder_name) with constants for folder→status mapping
- Scanner runs on-demand (HTTP trigger) with the semaphore pattern from `processor_gate.py`
- Report output uses `resolve_safe_excel_in_output()` from `input_data.py`
- Facturador paths are configurable (env vars or a config file in `data/`)
- Frontend dashboard shows aggregated indicators and per-facturador status tables

### Risks

- **Network path availability**: Scans depend on shared drives being accessible from the Flask server. If a drive is unmounted, the scanner must handle `PermissionError`/`FileNotFoundError` gracefully (per-facturador, not global failure)
- **Scan duration**: ~15 facturadores with deep folder trees could take significant time — the semaphore timeout (30s) may need adjustment or streaming-first approach
- **Dead code risk**: `cruce_sheet.py` is referenced in AGENTS.md but does not exist — verify if any planned code depends on it before creating the report generator
- **Invoice pattern complexity**: The description mentions FEV (`FEV\d+`) and CAP (`CAP\d+_\w+\d+`) patterns but real-world folder names may have edge cases (whitespace, unicode, mixed formats)
- **No existing folder scan tests**: This domain has zero test coverage precedent — all tests are Excel-based

### Ready for Proposal
Yes
