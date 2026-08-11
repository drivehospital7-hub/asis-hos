# Design: Integración AUDITORA — Auditoría de PDFs

## Enfoque Técnico

Extraer el core de `AUDITORA/` a `app/services/auditoria/` copiando (no mover), dividiendo el monolito `extractor.py` en dos archivos (extracción + PDE parsers), y conectándolo vía endpoints sync bajo el blueprint `/derechos` existente. Frontend React con 3 archivos siguiendo el patrón de `frontend/src/pages/derechos/`.

## Decisiones de Arquitectura

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| `extractor.py` monolítico (1690 líneas) vs dividido | Monolito mezcla extracción PDF con parsers PDE de 6 EPS; dividir da SRP y facilita testing | **Dividir**: `extractor.py` (solo fitz) + `pde_parser.py` (todo lo de parsers + normalización de texto) |
| OCR con pytesseract/pdf2image vs solo fitz | OCR captura texto en escaneados pero agrega 2 dependencias pesadas + paths hardcodeados | **Solo fitz** (PyMuPDF). PDFs sin texto → warning en UI, no crash |
| Ruta `reglas_soportes.json` relativa vs `Path(__file__)` | Relativa falla según CWD | **`Path(__file__).parent / "reglas_soportes.json"`** — resolución absoluta, funciona desde cualquier CWD |
| Tkinter `seleccionar_carpeta()` vs parámetro | Tkinter no funciona headless/sin display | **Parámetro de función**: `auditar_carpeta(ruta: str)` — la UI web reemplaza al diálogo |
| `print()` vs `logger` | print no da estructura ni niveles | **`logging.getLogger(__name__)`** — estándar del proyecto |
| Catch en cada PDF vs catch global | Error en un PDF no debe matar el batch | **try/except por PDF**, coleccionar errores por archivo, retornar parcial |

## Flujo de Datos

```
Cliente React ──POST ruta──→ /derechos/auditoria/procesar
                                  │
                                  ▼
                         auditor.auditar_carpeta(ruta)
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              extractor.py  fev_parser.py  pde_parser.py
              (extraer      (pdfplumber,   (fitz solo,
               texto fitz)   FEV layout)    PDE parsers)
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                                  ▼
                         normalizador.py
                         (FEV ↔ PDE, comparar_campos)
                                  │
                                  ▼
                         validador_soportes.py
                         (reglas_soportes.json)
                                  │
                                  ▼
                    ┌─────────────┐
                    ▼             ▼
              JSON response    React tree view
```

## Cambios de Archivos

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `app/services/auditoria/__init__.py` | Crear | Package vacío |
| `app/services/auditoria/extractor.py` | Crear | L1-12 (imports fitz), L15-19 (`limpiar_texto`, `PALABRAS_MEDICAS`), L1609-1690 (`extraer_texto_pdf` sin OCR). NO incluir pytesseract/pdf2image/PIL |
| `app/services/auditoria/pde_parser.py` | Crear | L1-1607 de `extractor.py` original (todo excepto la función `extraer_texto_pdf`). Incluye `normalizar_texto()`, `extraer_eps()`, todos los `parser_*()` |
| `app/services/auditoria/fev_parser.py` | Crear | Renombrar `diagnostico_fev_layout.py` completo. Sin cambios. |
| `app/services/auditoria/normalizador.py` | Crear | Copia directa de `normalizador.py`. Sin cambios. |
| `app/services/auditoria/validador_soportes.py` | Crear | Copia desde `validador_soportes.py`. **Cambio**: L5 `open("reglas_soportes.json")` → `Path(__file__).parent / "reglas_soportes.json"`. Reemplazar `assert` con condicionales. |
| `app/services/auditoria/reglas_soportes.json` | Crear | Copia directa. |
| `app/services/auditoria/auditor.py` | Crear | Desde `procesador_pdfs.pyw`. **Cambios**: reemplazar `seleccionar_carpeta()` con parámetro `ruta`, eliminar Tkinter, `print()` → `logger`, try/except por PDF, retornar dict en lugar de guardar JSON |
| `app/routes/derechos.py` | Modificar | +2 endpoints (`GET /derechos/auditoria`, `POST /derechos/auditoria/procesar`) |
| `app/constants/base.py` | Modificar | `AREA_AUDITORIA`, `ALLOWED_PERMISOS` + `"auditoria"`, `DASHBOARD_AREAS` + entrada |
| `frontend/src/pages/auditoria/index.html` | Crear | Template HTML con `<div id="root">` + script module |
| `frontend/src/pages/auditoria/main.tsx` | Crear | Mount React con `AppLayout` + `AuditoriaPage` |
| `frontend/src/pages/auditoria/page.tsx` | Crear | Componente con input ruta, submit, árbol expandible de resultados |
| `frontend/vite.config.ts` | Modificar | +1 entry point `src/pages/auditoria/index.html` |
| `requirements.txt` | Modificar | +`PyMuPDF>=1.23.0`, +`pdfplumber>=0.11.0` |

## Interfaces / Contratos

### POST /derechos/auditoria/procesar

**Request**:
```json
{ "ruta": "/ruta/a/carpeta" }
```

**Response success**:
```json
{
  "status": "success",
  "data": {
    "ruta": "/ruta/a/carpeta",
    "resultados": {
      "CAP447148": {
        "archivos": [
          { "tipo": "FEV", "archivo": "FEV447148.pdf", "data": { "encabezado": {}, "servicios": {} } },
          { "tipo": "PDE", "archivo": "PDE447148.pdf", "data": { "EPS": "EMSSANAR", ... } }
        ],
        "validacion": {
          "fev_normalizado": {},
          "pde_normalizado": {},
          "diferencias": {}
        },
        "validacion_soportes": {
          "validacion_soportes": [],
          "codigos_sin_regla": []
        },
        "error": null
      }
    },
    "resumen": {
      "total_carpetas": 5,
      "con_fev": 3,
      "con_pde": 4,
      "con_alertas": 1,
      "errores_procesamiento": 0
    }
  },
  "errors": []
}
```

## Estrategia de Testing

| Capa | Qué probar | Enfoque |
|------|-----------|---------|
| Unit | `extractor.extraer_texto_pdf()` | PDFs de prueba con texto digital conocido |
| Unit | `pde_parser.parser_emssanar()`, `parser_mallamas()`, etc. | Texto simulado de cada EPS, verificar campos extraídos |
| Unit | `normalizador.comparar_campos()` | Pares FEV↔PDE con diferencias conocidas |
| Unit | `validador_soportes.validar_soportes()` | Mock de FEV + soportes, verificar coincidencias |
| Integration | `POST /derechos/auditoria/procesar` | Carpeta real con PDFs de prueba, verificar respuesta JSON estructura |
| Frontend | `page.tsx` | Render con estado loading, success, error, empty |

## Migración / Rollout

No requiere migración. Rollout directo: feature completa en un solo PR. Rollback: `git revert` + eliminar `app/services/auditoria/` y `frontend/src/pages/auditoria/`.

## Preguntas Abiertas

- [ ] ¿Timeout máximo aceptable para carpetas con muchos PDFs? Sync puede bloquear varios segundos. Alternativa: mantener sync pero documentar límite práctico (~100 PDFs).
- [ ] ¿Mantener `_resolver_ruta_valida()` de `derechos.py` en el nuevo endpoint o duplicar la lógica? Reutilizar importándola.
