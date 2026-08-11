## Exploration: Agregar OCR a `app/services/auditoria/extractor.py`

### Current State

The existing `app/services/auditoria/extractor.py` uses **PyMuPDF (fitz) only** for PDF text extraction. When `page.get_text()` returns less than 50 chars (indicating a scanned PDF), the function silently returns whatever short text it found — effectively returning `""` for scanned documents.

The original `AUDITORA/extractor.py` performed OCR on scanned pages using:
1. **fitz page rendering**: `page.get_pixmap(matrix=fitz.Matrix(2, 2))` → PNG bytes → PIL `Image.open()`
2. **Tesseract OCR**: `pytesseract.image_to_string(imagen, lang="spa")`

**Key finding**: The original code does NOT use `pdf2image` for the OCR path — it imports it but the actual OCR uses fitz rendering directly. The `pdf2image` import in the original is dead code for the `extraer_texto_pdf` function.

The project has explicit tests (`test_no_pytesseract_import`, `test_no_pdf2image_import`) that verify these imports are absent — these will need updating.

### OCR Gap Analysis

| Aspect | Current | Target |
|--------|---------|--------|
| Digital PDFs | ✅ Works via fitz.get_text() | ✅ Same |
| Scanned PDFs (text < 50 chars) | ❌ Returns `""` | ✅ Runs Tesseract OCR on rendered page image |
| PDF type detection | ✅ fitz tries get_text() | ✅ Same, with OCR fallback |
| Page limit for PDE | ✅ max 2 pages | ✅ Same (faster with OCR since it's slow) |
| Error handling | ✅ Returns `""` on exception | ✅ Returns `""` on exception + Tesseract-not-found fallback |

### Dependencies

#### Python Packages

| Package | Version | Installed? | In requirements.txt? |
|---------|---------|------------|---------------------|
| `pytesseract` | 0.3.13 | ✅ (global) | ❌ Missing |
| `Pillow` | 12.3.0 | ✅ (global) | ❌ Missing |
| `pdf2image` | — | ❌ Not needed | ❌ Do NOT add — dead code in original |

**Important**: `pytesseract` already depends on `Pillow`, so adding only `pytesseract` to `requirements.txt` will transitively pull `Pillow`.

#### System Binaries

| Binary | Path | Status |
|--------|------|--------|
| Tesseract OCR | `C:\Program Files\Tesseract-OCR\tesseract.exe` | ❌ NOT installed on this machine |
| Poppler | `C:\poppler-25.12.0\Library\bin` | ✅ Installed (but NOT needed — OCR uses fitz rendering, not pdf2image) |

**Risk**: Tesseract must be installed separately on each deployment machine. No version manager or installer script exists.

### Affected Areas

| File | Why affected |
|------|-------------|
| `app/services/auditoria/extractor.py` | Core change — add OCR fallback with configurable Tesseract path |
| `requirements.txt` | Add `pytesseract` (and transitively `Pillow`) |
| `app/constants/` | New constant module `auditoria_ocr.py` for Tesseract/OCR config |
| `config/dev.py` | Optional: add TESSERACT_CMD env var override |
| `config/prod.py` | Optional: add TESSERACT_CMD env var override |
| `tests/auditoria/test_service_layer.py` | Update `test_no_pytesseract_import` and `test_no_pdf2image_import` — they currently assert absence |
| `app/services/auditoria/auditor.py` | May improve error messages (currently says "PDF escaneado sin OCR?") |
| `app/routes/derechos.py` | No change needed — imports extractor indirectly through auditor |
| `docs/` | Add Tesseract installation instructions or a section in README |
| `run_dev.py` / `run_prod.py` | No change — config classes handle env vars |

### Approaches

#### 1. Minimal OCR (Recommended)
Add OCR fallback directly in `extractor.py` with configurable Tesseract path via `os.getenv` + default. Tesseract binary path as a constant in `app/constants/auditoria.py`. Graceful fallback if Tesseract is not installed (log warning, skip OCR).

- **Pros**: Simple, 3-4 files changed, uses existing project patterns (env vars, constants module)
- **Cons**: Tesseract binary is a system dependency outside pip
- **Effort**: Low

#### 2. Dataclass Config (Like DB_CONFIG)
Create `app/utils/ocr_config.py` with a `TesseractConfig` dataclass (following `app/utils/db_config.py` pattern) that reads `TESSERACT_CMD` and `TESSERACT_LANG` from env vars.

- **Pros**: Consistent with `DatabaseConfig` pattern, centralized config validation
- **Cons**: Over-engineered for 2 config values, adds a file for minimal logic
- **Effort**: Low-Medium

#### 3. Flask App Config with `init_app`
Register Tesseract path in `app.config` during `create_app()`, accessed via `current_app.config.get("TESSERACT_CMD")` in the extractor.

- **Pros**: Flask-idiomatic, accessible from routes if needed
- **Cons**: Extractor is a standalone utility function — forcing Flask coupling is wrong (it's used from non-Flask contexts too, like test fixtures). Breaks SRP.
- **Effort**: Medium

### Recommendation

**Approach 1 (Minimal OCR)** — it's the right balance.

The extractor is a utility function, not a Flask service class. It should work independently of Flask's app context. The original code had hardcoded paths — we replace that with env var + constant + graceful fallback.

**How it works**:

```
extraer_texto_pdf(ruta, tipo_documento=None):
  1. fitz.open → page.get_text()
  2. If text > 50 chars → use it (digital PDF, fast path)
  3. If text ≤ 50 chars → try OCR:
     a. Check if Tesseract cmd exists on disk (os.path.exists)
     b. If yes: render at 2x, run Tesseract, add OCR text
     c. If no: log warning, return current text
  4. Return cleaned text
```

**Constants in `app/constants/auditoria.py`**:
```python
# Tesseract OCR configuration
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "spa")
OCR_SCALE = float(os.getenv("OCR_SCALE", "2.0"))  # fitz Matrix scale
```

**Graceful fallback**: If `TESSERACT_CMD` doesn't exist on disk, log a warning and skip OCR. The system continues working for digital PDFs — only scanned PDFs return empty text (same as current behavior).

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tesseract not installed | Scanned PDFs return `""` (same as current) | Graceful fallback with log warning |
| Tesseract path differs per machine | OCR fails silently | Make path configurable via env var + constant; log at INFO level which path is being tried |
| OCR is SLOW (3-10s per page) | User waits longer | PDE already limits to 2 pages; no change needed |
| OCR accuracy on medical text | Missed data | Use `lang="spa"`; original code used this same approach |
| Poppler NOT needed | None | Original imports `pdf2image` but OCR path uses fitz directly — no poppler dependency |
| test_no_pytesseract_import fails | CI breaks | Update test to allow pytesseract import |

### Ready for Proposal

**Yes** — the exploration is complete. The change is well-understood and low-risk.

Key decisions the spec/design phase should resolve:
1. Constant module: create `app/constants/auditoria.py` or add to existing `base.py`?
2. Config env var names: `TESSERACT_CMD`, `TESSERACT_LANG`, `OCR_SCALE` — confirm naming
3. Whether to add a `/api/health/ocr` endpoint to verify Tesseract is working
4. Whether to include installation documentation in the same PR

### Effort Estimate

- **Implementation**: ~30-40 lines of code changed across 3-4 files
- **Testing**: Update 2 existing tests + add 2-3 new tests for OCR fallback mock
- **Total**: Low effort (~2-4 hours including testing)
