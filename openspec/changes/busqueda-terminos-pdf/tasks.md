# Tasks: Búsqueda de Términos en PDF

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~675 (source ~505 + tests ~170) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Backend (~389) → PR 2: Frontend (~286) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend: constants + services + routes + tests | PR 1 | ~389 lines; standalone — API contracts define frontend boundary |
| 2 | Frontend: React SPA + sidebar/vite wiring | PR 2 | ~286 lines; depends on PR 1 API existing (contract-first) |

## Phase 1: Foundation — Backend Building Blocks

- [x] **1.1** Create `app/constants/busqueda_pdf.py` — `CONDICIONES`, `TRANSPORTES`, `SINONIMOS_DEFAULT`, `PDF_BASE_PATH` (env var)
- [x] **1.2** Create `app/services/busqueda_pdf/__init__.py` (empty package)
- [x] **1.3** Create `app/services/busqueda_pdf/sinonimos.py` — `merge_sinonimos(custom)` merges defaults + custom, custom wins on collision. Tests: parametrize empty/partial/override scenarios
- [x] **1.4** Create `app/services/busqueda_pdf/extractor.py` — `extraer_texto(ruta_pdf)` wraps fitz.open → get_text(), returns "" on any error. Tests: mock fitz with side_effect (valid text, scanned/corrupt → exception)

## Phase 2: Core Implementation

- [x] **2.1** Create `app/services/busqueda_pdf/buscador.py` — `buscar_en_carpeta(ruta, condicion, transporte, sinonimos)` lists PDFs, extracts text per file, computes "other" terms (exclude selected condicion+transporte), searches case-insensitive, builds resultados + resumen. Tests: mock os.listdir + extractor; scenarios: empty/all-scanned/terms-found/corrupt-pdfs
- [x] **2.2** Create `app/routes/busqueda_pdf.py` — blueprint with 3 endpoints: GET `/busqueda-pdf/` (React shell), GET `/listar-directorios?ruta=` (folder listing scoped to PDF_BASE_PATH), POST `/buscar` (orchestrates search). Tests: Flask test client + tmp_path real PDFs; validate path traversal 400, empty folder, corrupt PDF isolation

## Phase 3: Backend Wiring

- [x] **3.1** Modify `app/constants/base.py` — add `"busqueda_pdf"` to `ALLOWED_PERMISOS` + entry in `DASHBOARD_AREAS`
- [x] **3.2** Modify `app/__init__.py` — import `busqueda_pdf_bp` + `register_blueprint(busqueda_pdf_bp)`

## Phase 4: Frontend SPA

- [x] **4.1** Create `frontend/src/pages/busqueda-pdf/index.html` — Vite entry HTML (same pattern as auditoria/)
- [x] **4.2** Create `frontend/src/pages/busqueda-pdf/main.tsx` — React mount + AppLayout wrapper
- [x] **4.3** Create `frontend/src/pages/busqueda-pdf/page.tsx` — FolderBrowser, CondicionSelect, TransporteSelect, SynonymsInput, ResultsTable. Native `<select>` with Tailwind, no @radix-ui
- [x] **4.4** Modify `frontend/vite.config.ts` — add `busqueda-pdf/index.html` entry to `rollupOptions.input`
- [x] **4.5** Modify `frontend/src/components/app-sidebar.tsx` — add `"Búsqueda PDF"` nav item with `permiso: "busqueda_pdf"`, icon from lucide-react
