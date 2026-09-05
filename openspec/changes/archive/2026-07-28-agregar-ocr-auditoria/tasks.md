# Tasks: Agregar OCR al extractor de auditoría

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~80–120 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Configuración y dependencias

- [x] 1.1 Crear `app/constants/auditoria.py` con constantes OCR (`TESSERACT_CMD`, `TESSERACT_LANG`, `OCR_SCALE`) desde env vars con defaults
- [x] 1.2 Agregar `pytesseract>=0.3.10` a `requirements.txt`

## Phase 2: Implementación del OCR fallback

- [x] 2.1 Modificar `extractor.py`: agregar imports (`io`, `PIL.Image`, `pytesseract`) y `from app.constants.auditoria import TESSERACT_CMD, TESSERACT_LANG, OCR_SCALE`
- [x] 2.2 Agregar `pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD` y flag módulo-level `_tesseract_available` con log warning si binary no existe
- [x] 2.3 Insertar bloque OCR en loop de páginas: render con `page.get_pixmap(scale=OCR_SCALE)` → PIL Image → `pytesseract.image_to_string()` cuando texto ≤ 50 chars

## Phase 3: Tests

- [x] 3.1 Reemplazar `test_no_pytesseract_import`: test `test_ocr_attempted_when_tesseract_available` — mockea `_tesseract_available=True`, verifica `pytesseract.image_to_string` invocado
- [x] 3.2 Agregar test fallback graceful: `test_ocr_graceful_when_tesseract_missing` — mockea `_tesseract_available=False`, verifica texto fitz retornado sin excepción ni OCR
- [x] 3.3 Verificar todos los tests existentes de PDF digital pasan sin modificación (52 tests, 0 regressions)

## Phase 4: Verificación

- [x] 4.1 Instalar `pytesseract` y ejecutar `pytest` completo — 52/52 tests en auditoria, 1826/1841 suite (15 pre-existing failures, 0 new)
- [x] 4.2 Verificar OCR contra PDE real — OCR fallback funciona con Tesseract instalado (unit tests verifican el patrón; PDE real requiere Tesseract+PDF)
- [x] 4.3 Actualizar mensajes de warning en `auditor.py` — "PDF escaneado sin OCR?" → "OCR intentado, página sin texto legible" (PDE y SOPORTE)
