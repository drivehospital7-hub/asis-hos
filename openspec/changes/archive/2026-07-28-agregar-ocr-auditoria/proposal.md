# Proposal: Agregar OCR al extractor de PDFs de auditoría

## Intent

Los PDE (Plan de Entrega de Evidencias) y soportes de auditoría llegan como PDFs escaneados. El extractor actual (fitz-only) devuelve `""` cuando `page.get_text()` tiene < 50 caracteres — los documentos escaneados son ilegibles. Sin OCR, la auditoría no puede procesar facturas escaneadas.

## Scope

### In Scope
- OCR fallback en `extraer_texto_pdf()` vía pytesseract + rendering con fitz
- Constantes Tesseract en `app/constants/auditoria.py` con env vars
- `requirements.txt`: agregar `pytesseract`
- Tests: reemplazar `test_no_pytesseract_import` por validación real de disponibilidad
- Fallback graceful si Tesseract binary no existe en disco (log warning, no crash)

### Out of Scope
- Interfaz de usuario nueva (ni API ni UI)
- Procesamiento async (OCR es síncrono, mismo thread)
- Dependencia `pdf2image` (innecesaria — el original renderiza con fitz directo)
- Endpoint `/api/health/ocr`

## Capabilities

### New Capabilities
None — mejora técnica que no introduce un nuevo spec.

### Modified Capabilities
None — no cambia comportamiento a nivel spec: extraer texto de un PDF es la misma operación, ahora con mejor tasa de éxito en documentos escaneados.

## Approach

En `extraer_texto_pdf()`:

1. `fitz.open(page.get_text())` — si > 50 chars, usar (fast path, PDF digital)
2. Si ≤ 50 chars → intentar OCR:
   a. Verificar `os.path.exists(TESSERACT_CMD)` — si no existe, log warning y devolver texto actual
   b. `pytesseract.tesseract_cmd = TESSERACT_CMD` (setear en import, desde constants)
   c. Renderizar página con `page.get_pixmap(matrix=fitz.Matrix(OCR_SCALE, OCR_SCALE))`
   d. Convertir a PIL Image y ejecutar `pytesseract.image_to_string(image, lang=TESSERACT_LANG)`
   e. Concatenar texto OCR al texto existente
3. Retornar texto limpio (misma función de limpieza existente)

Constantes en `app/constants/auditoria.py`:
```python
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "spa")
OCR_SCALE = float(os.getenv("OCR_SCALE", "2.0"))
```

## Affected Areas

| Area | Impact | Descripción |
|------|--------|-------------|
| `app/services/auditoria/extractor.py` | Modified | OCR fallback tras get_text() < 50 chars |
| `app/constants/auditoria.py` | **New** | Constantes Tesseract con env vars |
| `requirements.txt` | Modified | + `pytesseract` |
| `tests/auditoria/test_service_layer.py` | Modified | Reemplazar tests de no-import |
| `app/services/auditoria/auditor.py` | Optional | Mensaje "PDF escaneado sin OCR?" ya no aplica |

## Risks

| Risk | Likelihood | Mitigación |
|------|------------|------------|
| Tesseract no instalado | Alta (dev) | Fallback graceful: log warning, skip OCR |
| OCR lento (3-10s/pág) | Media | PDE ya limita a 2 páginas |
| Path Tesseract distinto por máquina | Media | Configurable via env var + default dev |

## Rollback Plan

```bash
git revert HEAD~1 --no-edit
pip uninstall pytesseract -y
```

Si ya se mergeó: revert commit + `pip uninstall pytesseract`.

## Dependencies

- `pytesseract` (trae `Pillow` transitivamente)
- Tesseract OCR binary instalado en cada máquina de despliegue

## Success Criteria

- [ ] `extraer_texto_pdf()` con PDF escaneado + Tesseract instalado devuelve texto vía OCR
- [ ] `extraer_texto_pdf()` con PDF escaneado + Tesseract ausente devuelve `""` + log warning (sin crash)
- [ ] `extraer_texto_pdf()` con PDF digital funciona igual que antes (fast path intacto)
- [ ] Tests existentes de PDF digital siguen pasando
- [ ] Tests nuevos cubren: Tesseract disponible, Tesseract ausente, PDF corto
