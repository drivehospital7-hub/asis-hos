# Design: Agregar OCR al extractor de PDFs de auditoría

## Technical Approach

Se agrega OCR como fallback por página dentro de `extraer_texto_pdf()` cuando `page.get_text()` devuelve ≤ 50 caracteres (PDF escaneado). Se usa `pytesseract` + renderizado con `fitz.get_pixmap()` — sin dependencia `pdf2image`. Si Tesseract binary no existe en disco, se loguea un warning y se retorna el texto fitz original sin crash.

## Architecture Decisions

| Option | Tradeoff | Decision |
|--------|----------|----------|
| OCR per-page vs. post-loop global | Global: más simple pero pierde páginas mixtas (digital + escaneado). Per-page: más preciso, mismo loop. | **Per-page** — misma estructura que el original `AUDITORA/extractor.py` |
| pdf2image vs. fitz.render | pdf2image requiere binario poppler. fitz.render ya disponible (PyMuPDF). | **fitz.render** — cero dependencias nuevas de sistema |
| Async OCR | Mejoraría UX en batch, pero agrega complejidad de threading/sync. | **Síncrono** — la función ya es síncrona; el batch processa un PDF a la vez |
| Health endpoint / API | Útil para monitoreo, pero out of scope. | **No se agrega** — el log warning es suficiente |
| Umbral OCR por documento vs. página | Documento: evaluar texto total post-loop. Página: evaluar por iteración. | **Página** — captura PDFs mixtos (digital + escaneado) |

## Data Flow

```
extraer_texto_pdf(ruta)
  │
  ├─ fitz.open(ruta)
  │
  └─ for each page:
       │
       ├─ page.get_text()
       │    │
       │    ├─ len(texto) > 50  ──→ append texto (fast path)
       │    │
       │    └─ len(texto) ≤ 50  ──→ ¿Tesseract disponible?
       │                              │
       │                              ├─ Sí:
       │                              │   page.get_pixmap(scale=OCR_SCALE)
       │                              │   → PNG bytes → PIL Image
       │                              │   → pytesseract.image_to_string()
       │                              │   → append texto_ocr
       │                              │
       │                              └─ No:
       │                                  log warning (una vez)
       │                                  → append texto original
       │
       └─ (PDE early-exit si datos completos)
            │
            └─ doc.close()
                 │
                 └─ return limpiar_texto(texto_total)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/constants/auditoria.py` | **Create** | Constantes Tesseract: `TESSERACT_CMD`, `TESSERACT_LANG`, `OCR_SCALE` vía env vars con defaults |
| `app/services/auditoria/extractor.py` | **Modify** | Agregar imports `io`, `PIL`, `pytesseract` + OCR fallback por página + `_tesseract_available` check |
| `requirements.txt` | **Modify** | Agregar `pytesseract>=0.3.10` (Pillow viene como transitiva) |
| `tests/auditoria/test_service_layer.py` | **Modify** | Reemplazar `test_no_pytesseract_import` / `test_no_pdf2image_import` por tests de OCR real |

## Interfaces / Contracts

### Nuevas constantes (`app/constants/auditoria.py`)

```python
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "spa")
OCR_SCALE = float(os.getenv("OCR_SCALE", "2.0"))
```

### Módulo-level flag en extractor

```python
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
_tesseract_available = os.path.exists(TESSERACT_CMD)
if not _tesseract_available:
    logger.warning("Tesseract no encontrado en %s. OCR desactivado.", TESSERACT_CMD)
```

### OCR fallback (dentro del loop de páginas)

```python
if len(texto.strip()) > 50:
    texto_total += "\n" + texto
    continue
if _tesseract_available:
    mat = fitz.Matrix(OCR_SCALE, OCR_SCALE)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    imagen = Image.open(io.BytesIO(img_bytes))
    texto_ocr = pytesseract.image_to_string(imagen, lang=TESSERACT_LANG)
    texto_total += "\n" + texto_ocr
else:
    texto_total += "\n" + texto
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | OCR invocado cuando Tesseract disponible | `mock.patch("os.path.exists")` → True, `mock.patch("pytesseract.image_to_string")` → verificar que se llama |
| Unit | Fallback graceful cuando Tesseract ausente | `mock.patch("os.path.exists")` → False, verificar log warning, sin crash, texto fitz intacto |
| Unit | Fast path digital intacto | PDF con > 50 chars/página → OCR nunca se invoca |
| Unit | Constantes desde env vars | Monkeypatch `TESSERACT_CMD` → ver que se usa el valor del env |

## Threat Matrix

N/A — no se modifican routing, shell commands, subprocesses, VCS/PR automation, executable-file classification ni process-integration boundaries. El OCR se ejecuta en el mismo proceso mediante pytesseract, que internamente invoca el binario de Tesseract vía subprocess; pero este es un detalle interno de pytesseract encapsulado, no una integración directa nuestra.

## Migration / Rollout

No se requiere migración de datos. Feature flag implícito vía `_tesseract_available`: si Tesseract no está instalado, el sistema sigue funcionando como antes.

## Open Questions

- [ ] Confirmar que Pillow está disponible como dependencia transitiva de pytesseract (debería, pero verificar `pip install pytesseract` en entorno limpio)
- [ ] El mensaje "PDF escaneado sin OCR?" en `auditor.py` — ¿debería cambiar ahora que OCR existe?
