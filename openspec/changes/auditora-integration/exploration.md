# Exploration: AUDITORA Integration

## 1. Current State Analysis

### 1.1 Flask App Architecture (Existing)

**App factory pattern** (`app/__init__.py`):
- `create_app(config)` creates Flask instance
- Blueprints registered with optional `url_prefix`
- Middleware: `before_request` checks session auth against `PUBLIC_ENDPOINTS` frozenset
- Context processor injects `session_username`, `session_rol`, `session_permisos` to all templates

**Route pattern** (every route follows the same shape):
```
Blueprint("name", __name__)
  GET / → render_template("react_shell.html", ...)
  POST / → @permiso_requerido("perm") → API logic → jsonify(...)
```
- `_get_manifest_asset()` reads Vite `manifest.json` for `entry_js` and `entry_css`
- Pages get `initial_data` with `can_write`, `username`, `permisos`
- Response format: `{"status": "success"|"error", "data": {}, "errors": []}`

**Auth** (`app/utils/auth.py`):
- `@permiso_requerido(*permisos)` — decorator, checks session `permisos`, expands `:write` suffixes
- `@login_requerido` — checks session authenticated
- `@admin_requerido` — checks `*` perm

**Constants** (`app/constants/`):
- Package with `__init__.py` re-exporting from domain modules
- `base.py` has `_filter_areas()` for dashboard visibility
- Each domain has its own file (odontologia.py, colores.py, etc.)

**File upload / temp files** (`app/utils/input_data.py`):
- `save_temp_excel(file_storage)` → saves to `app/data/temp_uploads/` with UUID prefix
- `cleanup_temp_excel(path)` → deletes temp file
- `resolve_safe_excel_in_input/Output()` → path traversal prevention
- Existing max: 100MB, Excel-only extensions

### 1.2 Frontend Architecture (React + Vite)

- Source: `frontend/src/pages/{page-name}/`
- Each page: `index.html` + `main.tsx` + `page.tsx` (component)
- Entry points registered in `frontend/vite.config.ts` → `rollupOptions.input`
- Build output: `app/static/react-dist/` + `manifest.json`
- `react_shell.html` reads `entry_js`/`entry_css` from manifest + injects `__INITIAL_DATA__`
- Sidebar (`app-sidebar.tsx`): static `ALL_NAV` array with `permiso` guards
- UI kit: Tailwind v4 (CDN), custom CSS, Lucide icons, shadcn-inspired components

### 1.3 AUDITORA Module (Current State)

**Files** (11 entries in `AUDITORA/`):

| File | Lines | Purpose | Key Dependencies |
|------|-------|---------|-----------------|
| `procesador_pdfs.pyw` | 322 | Orchestrator — walks dir, processes PDFs, runs validations | tkinter, json |
| `extractor.py` | 1690 | PDF text extraction + PDE parsing (6 EPS) | **fitz** (PyMuPDF), **pytesseract**, **pdf2image**, PIL |
| `diagnostico_fev_layout.py` | 703 | FEV PDF parser via pdfplumber | **pdfplumber** |
| `normalizador.py` | 450 | FEV ↔ PDE normalization + field comparison | stdlib only |
| `validador_soportes.py` | 421 | Support doc validation (EPI, HAU, HAO, etc.) | json (stdlib) |
| `reglas_soportes.json` | 1327 | JSON validation rules for support documents | — |

**Key Functions to Expose**:
1. `recorrer_carpeta(base)` — walks dir tree, processes PDFs, returns nested dict with validations
2. `parsear_fev(ruta_pdf)` — FEV layout parsing via pdfplumber
3. `extraer_texto_pdf(ruta_pdf, tipo)` — text extraction via PyMuPDF + Tesseract OCR
4. `extraer_datos_derechos(bloque)` — PDE parsing
5. `validar_soportes(archivos, servicios_fev)` — support document validation
6. `normalizar_fev_emssanar(fev_data)` / `normalizar_pde_emssanar(pde_data)` / `comparar_campos(fev_norm, pde_norm)` — comparison logic

**Current Workflow**:
1. User runs `procesador_pdfs.pyw` (Tkinter dialog)
2. Selects a folder via `filedialog.askdirectory()`
3. `recorrer_carpeta(base)` walks directory tree, processes all PDFs
4. Results saved to `resultado.json`

---

## 2. Integration Points

### 2.1 Backend Integration

**Route Blueprint**: Create `app/routes/auditoria.py` with `auditoria_bp`

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/auditoria` | React shell page | `@permiso_requerido("derechos")` (or new perm "auditoria") |
| POST | `/auditoria/procesar` | Run audit on a folder path | `@permiso_requerido("derechos")` |
| GET | `/auditoria/resultado/<task_id>` | Poll async result | `@permiso_requerido("derechos")` |

**Constants**: Add `AREA_AUDITORIA = "auditoria"` to `app/constants/base.py` and add `"auditoria"` perm to `ALLOWED_PERMISOS`.

**Service structure**: Three options:

**Option A — Extract to `app/services/auditoria/` (RECOMMENDED)**
```
app/services/auditoria/
├── __init__.py
├── extractor.py          # PDF extraction (wrapper around fitz + pytesseract)
├── fev_parser.py         # FEV layout parsing (from diagnostico_fev_layout.py)
├── pde_parser.py         # PDE parsing (from extractor.py)
├── normalizador.py       # FEV ↔ PDE comparison
├── validador_soportes.py # Support doc validation
├── reglas_soportes.json  # Rules file (moved to this dir)
└── auditor.py            # Orchestrator (replaces procesador_pdfs.pyw walk logic)
```

**Option B — Import in place from `AUDITORA/`**
- Add `AUDITORA/` to Python path
- Import modules directly
- Pros: zero code changes to AUDITORA, faster setup
- Cons: messy imports, hardcoded paths (`reglas_soportes.json`), Tkinter dependency, mixed concerns

**Option C — Hybrid (middle ground)**
- Move core logic (extractors, parsers, validators) to `app/services/auditoria/`
- Keep the orchestration layer (`recorrer_carpeta`) there too
- Leave `AUDITORA/` intact as a standalone app reference (or deprecate it)

### 2.2 Frontend Integration

**New page**: `frontend/src/pages/auditoria/`
```
frontend/src/pages/auditoria/
├── index.html
├── main.tsx
└── page.tsx
```

**Add entry to** `frontend/vite.config.ts`:
```ts
path.resolve(__dirname, "src/pages/auditoria/index.html"),
```

**Add sidebar link** in `app-sidebar.tsx`:
```tsx
{ label: "Auditoría PDF", href: "/auditoria", icon: Search, permiso: "derechos" },
```

**Dashboard area** in `app/constants/base.py` → `DASHBOARD_AREAS`:
```python
{
    "title": "Auditoría PDF",
    "slug": "auditoria",
    "permiso": "derechos",
    "href": "/auditoria",
    "tone": "info",
    "pending_label": "",
    "description": "Validación de PDFs FEV, PDE y soportes.",
},
```

### 2.3 API Contract (POST /auditoria/procesar)

**Request**:
```json
{
    "ruta": "C:\\Users\\Documents\\Carpetas\\CAP447148"
}
```

**Response** (success):
```json
{
    "status": "success",
    "data": {
        "ruta": "C:\\Users\\...",
        "estructura": {
            "PACIENTE123": {
                "archivos": [
                    {"tipo": "FEV", "archivo": "FEV_123.PDF", "data": {...}},
                    {"tipo": "PDE", "archivo": "PDE.PDF", "data": {...}},
                    {"tipo": "SOPORTE", "archivo": "EPI_001.PDF", "texto": "..."}
                ],
                "validacion": {
                    "fev_normalizado": {...},
                    "pde_normalizado": {...},
                    "diferencias": {"campo": {"fev": "x", "pde": "y"}, ...}
                },
                "validacion_soportes": {
                    "EPI": {"concepto": "...", "coincidencias": [...], ...}
                },
                "alerta_archivos": null,
                "duplicado_global": null
            }
        },
        "total_expedientes": 42,
        "total_pdfs": 156
    },
    "errors": []
}
```

---

## 3. Critical Issues & Risks

### 3.1 Hardcoded Paths (HIGH)

| File | Line | Hardcoded Value |
|------|------|-----------------|
| `extractor.py` | L9 | `r"C:\Program Files\Tesseract-OCR\tesseract.exe"` |
| `extractor.py` | L11 | `r"C:\poppler-25.12.0\Library\bin"` |
| `validador_soportes.py` | L5 | `"reglas_soportes.json"` (relative to CWD) |

**Mitigation**:
- Make Tesseract path configurable via env var (`TESSERACT_CMD`) or `app.config`
- Make poppler path configurable via env var (`POPPLER_PATH`)
- Find `reglas_soportes.json` relative to the module (`__file__`)
- Wrap imports with graceful fallbacks when binaries are missing

### 3.2 Synchronous PDF Processing (HIGH)

`recorrer_carpeta()` processes all PDFs synchronously in a single request. A folder with 100+ PDFs could take 30+ seconds, hitting WSGI timeouts.

**Options** (ordered by complexity):
1. **Simple timeout increase** — configure waitress/Flask with longer timeout (fastest)
2. **Background task with polling** — spawn a thread, return `task_id`, poll `/auditoria/resultado/<task_id>`
3. **Redis/Celery** — full async task queue (overkill for this scope)
4. **SSE/WebSocket** — real-time progress updates

**Recommendation**: Option 2 (background thread + polling) for v1. This pattern already exists implicitly in the codebase (no Celery dependency, no Redis).

### 3.3 Tkinter Dependency

`procesador_pdfs.pyw` uses `tkinter.filedialog.askdirectory()`. This CANNOT work in a web context — no display, no GUI.

**Replacement**: The `derechos.py` route already solved this exact problem: accept a text input for the folder path, resolve it on the server, process it. Same pattern for AUDITORA.

### 3.4 New Dependencies

| Library | Purpose | Size/Complexity |
|---------|---------|----------------|
| `PyMuPDF` (fitz) | PDF text extraction | Medium (~10MB) |
| `pytesseract` | OCR for scanned PDFs | Requires Tesseract binary (~50MB) |
| `pdf2image` | PDF → image conversion for OCR | Requires poppler (~30MB) |
| `pdfplumber` | FEV table parsing | Small (~2MB) |
| `Pillow` (PIL) | Image handling (dependency of pdf2image) | Medium (~5MB) |

**Total new runtime deps**: 4 PyPI packages + 2 system binaries (Tesseract, poppler).

**Existing dep**: `pypdf==5.2.0` already in requirements.txt (can be used for basic PDF extraction, but not sufficient for FEV layout parsing or OCR).

### 3.5 Error Handling Gaps

- `extractor.py` has minimal error handling — `extraer_texto_pdf` can return `None` or throw
- `validador_soportes.py` does `assert archivos` on line 67 (could crash)
- `recorrer_carpeta()` doesn't handle permission errors on subdirectories
- No logging in AUDITORA (just `print()`)

**Mitigation**: Wrap all external calls in try/except, add logging via `logger = logging.getLogger(__name__)`, replace `assert` with proper conditionals.

### 3.6 PEP 668 / pip Issues in Production

The `Instalar librerias.txt` references a specific Python 3.11 installation path. If the server has PEP 668 (externally-managed environment), pip installs will fail.

**Mitigation**: Document installation via `--break-system-packages` or virtual env. Add to project's setup docs.

### 3.7 Thread Safety

If using background threads for async processing, multiple concurrent audit requests could interfere:
- `recorrer_carpeta()` is reentrant (no shared state)
- `resultado.json` should NOT be used — results should be returned in the response, not written to disk
- Each request gets its own temp directory for intermediate files

---

## 4. Proposed Architecture — Migration Path

### 4.1 Extract Phase (Recommended Approach — Option A)

```
AUDITORA/  ← STAYS as-is (reference/standalone)
└── (all files preserved)

app/services/auditoria/  ← NEW extracted package
├── __init__.py
├── constants.py         ← AUDITORA-specific constants (EPS names, categories, etc.)
├── extractor.py         ← Wrapper: PDF text extraction via fitz/pdfplumber
├── fev_parser.py        ← FEV layout parser (from diagnostico_fev_layout.py)
├── pde_parser.py        ← PDE parser (from extractor.py, section 2+)
├── normalizador.py      ← Normalization + comparison (from normalizador.py)
├── validador_soportes.py ← Support doc validator (from validador_soportes.py)
└── auditor.py           ← Orchestrator: walk + process + aggregate (from procesador_pdfs.pyw)

app/routes/auditoria.py  ← NEW blueprint

app/constants/base.py    ← ADD: AREA_AUDITORIA perm + dashboard entry

frontend/src/pages/auditoria/  ← NEW React page
├── index.html
├── main.tsx
└── page.tsx
```

### 4.2 Extraction Principles

1. **Copy, don't move** — AUDITORA/ remains intact as standalone app reference
2. **Wrap hardcoded paths** — env vars or `app.config` for Tesseract/poppler paths
3. **Replace `print()` with `logger`** — consistent with existing codebase
4. **Remove Tkinter** — accept folder path as POST parameter
5. **Fix `reglas_soportes.json` path** — resolve relative to `__file__`
6. **Add error boundaries** — each extraction/parsing function must handle failures gracefully
7. **Preserve business logic** — zero changes to normalization, comparison, or validation rules

### 4.3 API Design

**Simple sync (v1 — fast to ship)**:
- POST `/auditoria/procesar` → runs audit synchronously → returns full result
- For small folders (< 50 PDFs), acceptable within 30s

**Async with polling (v1.1 — recommended)**:
- POST `/auditoria/procesar` → spawns background thread → returns `{"task_id": "...", "status": "processing"}` 
- GET `/auditoria/resultado/<task_id>` → returns current status + partial/final result
- Cleanup: auto-delete task results after 30 min

### 4.4 Constants Registration

In `app/constants/base.py`:
```python
AREA_AUDITORIA = "auditoria"
```

In `ALLOWED_PERMISOS`:
```python
"auditoria",
```

In `DASHBOARD_AREAS`:
```python
{
    "title": "Auditoría PDF",
    "slug": "auditoria",
    "permiso": "auditoria",
    "href": "/auditoria",
    "tone": "info",
    "pending_label": "",
    "description": "Validación de PDFs FEV, PDE y soportes.",
},
```

---

## 5. Dependencies & Requirements

### 5.1 Python Packages (to add to `requirements.txt`)

| Package | Version (min) | Purpose | Notes |
|---------|-------------|---------|-------|
| `PyMuPDF` | ≥1.23.0 | PDF text extraction (fitz) | Fast, reliable |
| `pdfplumber` | ≥0.11.0 | FEV table parsing | Already stable API |
| `pytesseract` | ≥0.3.10 | OCR for scanned PDFs | Optional — only if OCR needed |
| `pdf2image` | ≥1.17.0 | PDF → PIL images for OCR | Optional — only if OCR needed |
| `Pillow` | ≥10.0.0 | Image handling | Dependency of pdf2image |

### 5.2 System Binaries

| Binary | Required For | Install |
|--------|-------------|---------|
| Tesseract OCR | `pytesseract` | `winget install TesseractOCR.Tesseract` or manual download |
| Poppler | `pdf2image` (via `pdftoppm`) | `winget install poppler` or manual download |

**Important**: OCR + image conversion is only needed for scanned PDFs. If the PDFs are text-based (digital), `PyMuPDF` alone suffices. The `extractor.py` already has conditional logic: it tries fitz first, falls back to OCR if text is empty.

### 5.3 Installation Script

```bash
# Python packages
pip install PyMuPDF pdfplumber
# Optional (for OCR/scan support):
pip install pytesseract pdf2image Pillow

# System binaries (Windows - as admin)
winget install TesseractOCR.Tesseract
winget install poppler
# OR download manually from respective GitHub repos
```

---

## 6. Migration Strategy

### Phase 1 — Extract (2-3 days)
1. Create `app/services/auditoria/` package
2. Copy + adapt extractor.py → split into `extractor.py` + `pde_parser.py`
3. Copy + adapt `diagnostico_fev_layout.py` → `fev_parser.py`
4. Copy + adapt `normalizador.py` (mostly unchanged)
5. Copy + adapt `validador_soportes.py` (fix path, remove assert)
6. Copy + adapt `procesador_pdfs.pyw` → `auditor.py` (remove Tkinter, add logging)
7. Move `reglas_soportes.json` into the package

### Phase 2 — Backend Route (1 day)
1. Create `app/routes/auditoria.py` with GET + POST
2. Wire into `app/__init__.py`
3. Add constants (perm, dashboard area)
4. Implement async processing with thread pool (or simple sync for v1)

### Phase 3 — Frontend (1-2 days)
1. Create `frontend/src/pages/auditoria/` with index.html, main.tsx, page.tsx
2. Add entry to `vite.config.ts`
3. Add sidebar link
4. Implement React component: folder path input + results display (tree view with expandable cards)

### Phase 4 — Polish (1 day)
1. Error handling edge cases
2. Logging review
3. Test with real data
4. Build frontend (`cd frontend && npm run build`)

### Total Estimated Complexity: **Medium** (5-7 days full-time)

---

## 7. Risks Summary

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Hardcoded Tesseract/poppler paths | High | Certain | Make configurable via env vars; document system requirements |
| PDF processing timeout (sync) | High | High | Implement async polling; set reasonable timeout |
| OCR needs system binaries | Medium | Medium | Fallback to fitz-only; user opts into OCR explicitly |
| `reglas_soportes.json` path broken | High | Certain | Resolve relative to `__file__` |
| Thread safety on concurrent requests | Low | Medium | No shared state; each request independent |
| Tkinter import errors in web context | High | Certain | Remove entirely; replace with text input |
| Print statements instead of logging | Low | Certain | Replace with `logger.{info,warning,exception}` |
| PEP 668 install issues | Medium | Low | Document virtual env setup |
| `pytesseract` Windows OCR accuracy | Medium | Medium | Document that scanned PDF support requires tuning |
| Vite build config changes | Low | Low | Follow existing pattern; one new entry point |

---

## 8. Key Decisions Needed

### Decision 1: Module Structure
- **Option A** (Recommended): Extract core logic to `app/services/auditoria/`, keep `AUDITORA/` intact
- **Option B**: Import from `AUDITORA/` in place (faster but messier)
- **Option C**: Hybrid — extract only the orchestrator, reference parsers in place

### Decision 2: Async vs Sync
- **Option Sync**: POST blocks until all PDFs processed (simple, risk of timeout)
- **Option Async** (Recommended): POST returns task_id, frontend polls for results

### Decision 3: OCR Support
- **Full OCR**: Include pytesseract + pdf2image + Pillow (heavy install)
- **Fitz-only** (Recommended): Extract text via PyMuPDF only, skip OCR for v1
- **Hybrid**: Fitz-only by default, OCR flag to enable

### Decision 4: New Permission
- **Reuse `derechos`** — AUDITORA goes under existing "derechos" permission
- **New `auditoria`** (Recommended) — clean separation, follow existing pattern

---

## 9. Open Questions

1. Is the folder being audited local to the Flask server, or is it a network share? (`derechos.py` already handles Windows/WSL/Linux paths — this pattern works)
2. Should OCR fallback be included in v1 or deferred?
3. How large are typical folders? (for timeout calculation)
4. Is there a need to persist audit results in the database, or is JSON enough?
5. Should the React page show real-time progress (WebSocket/SSE) or just poll?
