## Exploration: Clipboard Image Copy Issue in Urgencias Control

### Current State

The clipboard image handling lives in **Control de Novedades** (`app/templates/control_errores.html`), NOT in the Urgencias Excel-processing module. It uses vanilla JavaScript (no frameworks) on a Jinja2 template served by `/control-errores`.

There are **two paste handlers** that handle image pasting:

#### Handler 1: Global paste (line 1550)
```javascript
document.addEventListener('paste', async (e) => { ... })
```
Covers TWO paths:
- **Carga Masiva path**: When `cargaModal` is open and Step 2 (preview) is visible → adds the FIRST matching clipboard image to `cargaImages[]` via `setTimeout(100)`.
- **Individual Error path**: When no modal is open → picks the FIRST `image/*` item from clipboard → creates `FormData` → `POST /api/control-errores/{errorId}/imagenes`.

Has early `return;` after the carga modal block, so both paths never execute in the same event.

#### Handler 2: Textarea-specific paste (line 1808)
```javascript
document.getElementById('cargaTextarea').addEventListener('paste', function(e) { ... })
```
Only fires when user is focused on the `cargaTextarea`. Picks the FIRST `image/*` item → calls `preguntarImagenCarga(file)` → `setTimeout(100)` → `addCargaImageFile()`.

#### Image upload flow
- **Individual error**: `uploadImages(errorId, files)` iterates over all selected files, creates one `POST` per file.
- **Carga Masiva**: `submitCargaMasiva()` first POSTs error records, then iterates over `createdIds × cargaImages` (nested loops), uploading each image to each created error.

#### Backend
- Route: `POST /api/control-errores/<error_id>/imagenes`
- Service: `guardar_imagen()` in `app/utils/errores_storage.py`
- Saves to filesystem at `app/data/imagenes/{error_id}/file_{n}.{ext}`
- Max 3 images per error, max 20MB, allowed: `.jpg .jpeg .png .gif .webp .pdf`
- No database — purely filesystem-based

### Key Bugs Found

**BUG 1 (DOUBLE ADD — one image becomes two)**: When user pastes in `cargaTextarea` while in Step 2, BOTH handlers fire for the same event:
1. Textarea handler fires → `preguntarImagenCarga(file)` → schedule `setTimeout(100)`
2. Event bubbles to document → Global handler fires → schedule another `setTimeout(100)` with the SAME file reference
3. Both callbacks execute ~100ms later → same image added **twice** to `cargaImages[]`
4. During bulk submit, image gets uploaded twice to each created error

**BUG 2 (FIRST ITEM, NOT LAST)**: Both handlers use `break` after the first `image/*` match. When clipboard has multiple images (from multi-file copy or certain apps), the code picks index 0 (first) instead of the last/most recent image.

**BUG 3 (MISSING preventDefault)**: The textarea handler and the global handler's carga path do NOT call `e.preventDefault()`. This allows the browser's default paste action (inserting text into textarea) alongside the image upload, causing UI confusion.

### Affected Areas

- `app/templates/control_errores.html` — **Lines 1550-1609**: Global paste handler (double-add bug on line 1550, first-item bug on line 1582)
- `app/templates/control_errores.html` — **Lines 1808-1824**: Textarea paste handler (first-item bug on line 1820, missing stopPropagation on line 1808)
- `app/routes/control_errores.py` — **Lines 123-132**: Image upload endpoint (backend — no changes needed, works correctly)
- `app/utils/errores_storage.py` — **Lines 244-265**: `guardar_imagen()` (backend — no changes needed)
- `app/constants/base.py` — **Lines 122-125**: Image constants (limits and allowed types)
- `tests/` — **No existing tests** for clipboard/image/paste functionality

### Approaches

1. **Fix double-add + pick last image (frontend-only)** — Minimal JS changes
   - **Pros**: Low effort, addresses both bugs, no backend changes
   - **Cons**: Still doesn't handle the edge case of truly wanting multiple images
   - **Effort**: Low

2. **Rewrite paste handling with unified architecture** — Consolidate into a single paste manager
   - **Pros**: Clean separation, testable, maintainable
   - **Cons**: Higher effort, touches more lines, riskier without tests
   - **Effort**: Medium

3. **Add backend deduplication** — Check duplicate image content on the server
   - **Pros**: Safety net even if frontend bugs persist
   - **Cons**: Doesn't fix the root cause, adds complexity, false positives on legit duplicates
   - **Effort**: Medium

### Recommendation

**Approach 1: Fix the frontend JS.** The bugs are contained to the paste handlers in a single HTML file.

Specific changes needed:
1. **Prevent double image add**: Add `e.stopPropagation()` in the textarea paste handler so the global handler doesn't also fire.
2. **Pick the last image, not the first**: Iterate clipboard items and track the LAST image match (or iterate in reverse), so the most recently added image is used.
3. **Add `e.preventDefault()`** in both handlers to prevent browser default paste action.

No backend changes needed — the `guardar_imagen` and route logic are correct as-is.

### Risks

- **Frontend has no tests** for this code — every fix needs manual testing in browser
- **The `preguntarImagenCarga()` function name** suggests it was meant to ask the user before adding, but it currently adds silently — might be a separate UX concern
- **React version exists** (`frontend/src/pages/control-novedades/`) but is NOT deployed yet — any fix to the Jinja2 template may be thrown away if/when the React version takes over
- **Clipboard behavior varies by OS/browser** — testing should cover Chrome, Edge, and Firefox on Windows

### Ready for Proposal

**Yes.** The bugs are clearly identified, the fix approach is straightforward, and affected files are well understood. Tell the user: "Found the root cause — two paste handlers fire for the same event causing duplicate image uploads, plus the code picks the first image instead of the last. Both are frontend-only JS fixes in `control_errores.html`. Ready for SDD proposal."
