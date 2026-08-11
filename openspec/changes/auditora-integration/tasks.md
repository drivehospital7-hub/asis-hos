# Tasks: Integración AUDITORA — Auditoría de PDFs

Decision needed before apply: Yes (resolved: size:exception)
Chained PRs recommended: Yes (resolved: single PR with size:exception)
Chain strategy: feature-branch-chain (resolved: single PR)
400-line budget risk: High (resolved: exception accepted — 97% copied code)

> ~97% del diff es código copiado de `AUDITORA/` (~50 líneas de adaptación nueva). Revisión enfocada en cambios, no volumen.

## Phase 1: Service Layer (core extraction)

- [x] 1.1 Crear `app/services/auditoria/__init__.py` — package vacío
- [x] 1.2 Crear `app/services/auditoria/extractor.py` — desde `AUDITORA/extractor.py`: solo fitz + `limpiar_texto()` + `extraer_texto_pdf()`. Eliminar pytesseract/pdf2image/PIL/OCR paths
- [x] 1.3 Crear `app/services/auditoria/pde_parser.py` — desde `AUDITORA/extractor.py` (L1–1607, sin `extraer_texto_pdf`). Incluir `normalizar_texto()`, `extraer_eps()`, todos los `parser_*()`. Agregar import fitz
- [x] 1.4 Crear `app/services/auditoria/fev_parser.py` — copiar `AUDITORA/diagnostico_fev_layout.py` tal cual
- [x] 1.5 Crear `app/services/auditoria/normalizador.py` — copiar `AUDITORA/normalizador.py` tal cual
- [x] 1.6 Crear `app/services/auditoria/validador_soportes.py` — copiar desde `AUDITORA/validador_soportes.py`. **Cambios**: L5 `open("reglas_soportes.json")` → `Path(__file__).parent / "reglas_soportes.json"`. Reemplazar `assert` con condicionales + logging
- [x] 1.7 Crear `app/services/auditoria/reglas_soportes.json` — copiar `AUDITORA/reglas_soportes.json` tal cual
- [x] 1.8 Crear `app/services/auditoria/auditor.py` — desde `AUDITORA/procesador_pdfs.pyw`. **Cambios**: eliminar Tkinter, `seleccionar_carpeta()` → parámetro `ruta`, `print()` → `logger`, try/except por PDF, retornar dict en lugar de guardar JSON

## Phase 2: Backend Route + Constants

- [x] 2.1 Agregar constantes en `app/constants/base.py`: `AREA_AUDITORIA`, `ALLOWED_PERMISOS` + `"auditoria"`, `DASHBOARD_AREAS` entry con href `/derechos/auditoria`
- [x] 2.2 Agregar `GET /derechos/auditoria` + `POST /derechos/auditoria/procesar` en `app/routes/derechos.py` — GET renderiza `react_shell.html` con entry point, POST recibe `{"ruta"}`, llama `auditar_carpeta(ruta)`, retorna envelope canónico. Reutiliza `_resolver_ruta_valida()`. Ambos requieren permiso `derechos`
- [x] 2.3 (consolidated in 2.2 above)

## Phase 3: Frontend

- [x] 3.1 Crear `frontend/src/pages/auditoria/index.html` — template con `<div id="root">` + script module (mismo patrón que `derechos/index.html`)
- [x] 3.2 Crear `frontend/src/pages/auditoria/main.tsx` — mount React con `AppLayout` + `AuditoriaPage` (mismo patrón que `derechos/main.tsx`)
- [x] 3.3 Crear `frontend/src/pages/auditoria/page.tsx` — componente con input ruta, botón Procesar, árbol expandible de resultados. Estados: loading, error, empty, success
- [x] 3.4 Registrar entry en `frontend/vite.config.ts` — agregar `path.resolve(__dirname, "src/pages/auditoria/index.html")` al array `input`

## Phase 4: Dependencies & Build

- [x] 4.1 Agregar `PyMuPDF>=1.23.0` y `pdfplumber>=0.11.0` a `requirements.txt`
- [x] 4.2 Instalar dependencias y verificar `python -c "import fitz; import pdfplumber"` sin errores
- [x] 4.3 Ejecutar build frontend: `cd frontend && npx vite build` sin errores

## Phase 5: Verification

- [x] 5.1 Test de importación: `python -c "from app.services.auditoria.auditor import auditar_carpeta; from app.services.auditoria.extractor import extraer_texto_pdf; from app.services.auditoria.pde_parser import extraer_datos_derechos; from app.services.auditoria.fev_parser import parsear_fev; from app.services.auditoria.normalizador import comparar_campos; from app.services.auditoria.validador_soportes import validar_soportes; print('OK')"` — funciona
- [x] 5.2 Tests unitarios (50 tests): cobertura de importación, funciones, EPS parsers, normalización, validación soportes, auditor — TODOS PASAN
- [x] 5.3 Test de error: ruta inexistente → el endpoint retorna status=error con HTTP 400
- [x] 5.4 Test de carpeta vacía: mock de os.walk sin PDFs → auditar_carpeta retorna dict vacío (test unitario)
- [x] 5.5 Verificar que no hay `print()` en ningún archivo nuevo de `app/services/auditoria/` — 0 ocurrencias confirmado
- [x] 5.6 Verificar que `reglas_soportes.json` se resuelve desde cualquier CWD — 76 reglas cargadas vía `Path(__file__)` sin depender de CWD
