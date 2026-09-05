# Proposal: Integrar AUDITORA al sistema — Auditoría de PDFs

## Intent

El módulo `AUDITORA/` audita PDFs (FEV, PDE, soportes) pero está fuera del sistema
web — requiere Tkinter, cambio de contexto, cruce manual. Integrarlo al Flask app
unifica el flujo: dashboard → ingresa ruta → obtiene resultados de auditoría en el
mismo lugar donde ya gestionan derechos.

## Scope

### In Scope
- Extraer core a `app/services/auditoria/` (8 archivos)
- Endpoints bajo blueprint `/derechos` existente (permiso `derechos`)
- Frontend React en `frontend/src/pages/auditoria/`
- Sincrónico (POST bloqueante), solo fitz + pdfplumber (sin OCR)
- Dependencias: `PyMuPDF`, `pdfplumber`
- Fix hardcoded paths, `print()` → `logging`

### Out of Scope
- OCR/Tesseract/poppler, async polling, permiso nuevo, blueprint separado
- Modificar `AUDITORA/` original, persistencia en DB

## Capabilities

### New Capabilities
- `pdf-audit`: Auditoría de PDFs FEV, PDE y soportes — carga folder, parsea, normaliza,
  compara FEV↔PDE, valida soportes vía reglas JSON

### Modified Capabilities
- `evidencia-auditoria`: No se modifica (no usa engine de reglas)

## Approach

1. **Extraer** `AUDITORA/` → `app/services/auditoria/` copiando (no mover):
   extractor.py, fev_parser.py, pde_parser.py, normalizador.py, validador_soportes.py,
   reglas_soportes.json, auditor.py.
2. **Adaptar**: `reglas_soportes.json` vía `__file__`, `print()` → `logger`, remover
   Tkinter/pytesseract/pdf2image, wrap en try/except.
3. **Ruta**: `GET /derechos/auditoria` (React shell) + `POST /derechos/auditoria/procesar`
   (sync, retorna estructura anidada).
4. **Frontend**: 3 archivos (`index.html`, `main.tsx`, `page.tsx`) con input de ruta +
   árbol expandible de resultados.
5. **Constantes**: `AREA_AUDITORIA`, entrada en `DASHBOARD_AREAS` y `ALLOWED_PERMISOS`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/auditoria/` | New | 8 archivos |
| `app/routes/derechos.py` | Modified | +2 endpoints |
| `app/constants/base.py` | Modified | +area, perm, dashboard |
| `frontend/src/pages/auditoria/` | New | 3 archivos React |
| `frontend/vite.config.ts` | Modified | +1 entry point |
| `requirements.txt` | Modified | +2 deps |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Timeout carpetas grandes | Medium | Sync aceptado; documentar límite práctico |
| PDFs escaneados sin OCR | High | Warning en UI; log por PDF sin texto |
| `reglas_soportes.json` no encontrado | Low | Resolución absoluta vía `__file__` |
| FEV con layout atípico | Medium | Try/except por PDF sin bloquear batch |

## Rollback Plan

1. `git revert` del commit de integración (limpiamente reversible)
2. Revertir `vite.config.ts`, `requirements.txt`, `base.py`; eliminar
   `app/services/auditoria/` y `frontend/src/pages/auditoria/` manualmente
3. Sin migraciones DB que revertir

## Dependencies

- `PyMuPDF>=1.23.0`, `pdfplumber>=0.11.0`

## Success Criteria

- [ ] `POST /derechos/auditoria/procesar` retorna estructura con FEV, PDE, soportes
- [ ] Frontend muestra resultados en árbol expandible
- [ ] Sin errores de importación (`fitz`, `pdfplumber`)
- [ ] `reglas_soportes.json` resuelto desde cualquier CWD
- [ ] Sin `print()` en código nuevo — solo `logging`
- [ ] Build frontend exitoso
