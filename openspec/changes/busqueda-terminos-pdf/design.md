# Design: Búsqueda de Términos en PDFs

## Technical Approach

Navegación server-side de directorios + búsqueda de términos Condición/Transporte en PDFs vía PyMuPDF. Frontend SPA con Vite (mismo patrón que auditoría). Sin nuevas dependencias.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Folder navigation | Server-side via `os.listdir()` | `<input type="file" webkitdirectory>` | No expone sistema de archivos server al browser; control total sobre path base |
| Synonyms storage | Payload-only, no DB | SQLite, sesión persistente | V1 simple; datos cambian por request; sin overhead de migración |
| PDF lib | PyMuPDF (`fitz`) | `pypdf`, `pdfplumber` | Ya instalado, usado en `auditoria/extractor.py`, más rápido que alternativas |
| Result matching | Termino exacto (case-insensitive) | fuzzy matching, regex | Simplicidad; datos controlados (Condiciones/Transportes son vocabulario cerrado) |

## Data Flow

```
Frontend                          Backend
─────────                         ───────
FolderBrowser ──GET /listar-directorios?ruta=──→ busqueda_pdf.py
                                                    │
                                                    └→ os.listdir(ruta)
                                                    │
                 ←── {directorios, pdfs} ───────────┘

SelectorPanel + SynonymsInput
        │
POST /buscar {ruta, condicion, transporte, sinonimos}
        │
        ↓
   busqueda_pdf.py → buscador.buscar_en_carpeta(...)
                        ├→ listar PDFs en ruta
                        ├→ por cada PDF: extractor.extraer_texto(pdf)
                        │                    └→ fitz.open() → get_text()
                        ├→ sinonimos.merge_sinonimos(custom)
                        ├→ generar "otros términos" (excluir seleccionado)
                        └→ buscar cada otro término en texto
        │
   ←── [{pdf, terminos_encontrados: [{termino, tipo, contexto}]}] ──→ ResultsTable
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/routes/busqueda_pdf.py` | Create | Blueprint con 3 endpoints (shell, listar, buscar) |
| `app/services/busqueda_pdf/__init__.py` | Create | Package init vacío |
| `app/services/busqueda_pdf/extractor.py` | Create | Wrapper sobre `fitz.open()` — texto plano, sin OCR |
| `app/services/busqueda_pdf/buscador.py` | Create | Orquestador: recorre PDFs, busca términos, clasifica |
| `app/services/busqueda_pdf/sinonimos.py` | Create | Mapa default + merge con custom del payload |
| `app/constants/busqueda_pdf.py` | Create | `CONDICIONES`, `TRANSPORTES`, `SINONIMOS_DEFAULT` |
| `app/constants/base.py` | Modify | Agregar `"busqueda_pdf"` a `ALLOWED_PERMISOS` + entrada `DASHBOARD_AREAS` |
| `app/__init__.py` | Modify | Import + `register_blueprint(busqueda_pdf_bp)` |
| `frontend/src/pages/busqueda-pdf/index.html` | Create | Entry HTML |
| `frontend/src/pages/busqueda-pdf/main.tsx` | Create | React mount + AppLayout |
| `frontend/src/pages/busqueda-pdf/page.tsx` | Create | Componente principal con 4 sub-componentes |
| `frontend/vite.config.ts` | Modify | Agregar entrada en `rollupOptions.input` |
| `frontend/src/components/app-sidebar.tsx` | Modify | Agregar item en `ALL_NAV` |

## Interfaces / Contracts

### Endpoints

```python
# GET /busqueda-pdf/listar-directorios?ruta=D:\some\path
Response 200: {
    "status": "success",
    "data": {
        "ruta": "D:\\some\\path",
        "directorios": ["sub1", "sub2"],
        "pdfs": ["doc1.pdf", "doc2.pdf"]
    },
    "errors": []
}

# POST /busqueda-pdf/buscar
Request: {
    "ruta": "D:\\some\\path",
    "condicion": "Conductor",
    "transporte": "Automóvil",
    "sinonimos": {"Ocupante": ["Acompanante", "Pasajero"]}
}
Response 200: {
    "status": "success",
    "data": {
        "ruta": "D:\\some\\path",
        "total_pdfs": 15,
        "total_encontrados": 3,
        "resultados": [
            {
                "pdf": "informe.pdf",
                "terminos_encontrados": [
                    {"termino": "Peatón", "tipo": "condicion", "contexto": "...texto circundante..."}
                ]
            }
        ]
    },
    "errors": []
}
```

### Internal functions

```python
# extractor.py
def extraer_texto(ruta_pdf: str) -> str:
    """Extrae texto plano de un PDF. Retorna "" si no se puede leer."""

# sinonimos.py
def merge_sinonimos(sinonimos_custom: dict | None) -> dict:
    """Combina SINONIMOS_DEFAULT + custom. Custom gana en colisión."""

# buscador.py
def buscar_en_carpeta(
    ruta: str, condicion: str, transporte: str, sinonimos: dict
) -> list[dict]:
    """Busca términos de otras condiciones/transportes en PDFs de la carpeta."""
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit: sinonimos | Merge vacío, merge con colisión, merge parcial | parametrize + fixtures |
| Unit: extractor | PDF válido → texto, PDF corrupto → "" | mock fitz.open con side_effect |
| Unit: buscador | Carpeta sin PDFs, PDFs sin términos, PDFs con términos | mock extractor + os.listdir |
| Integration | Endpoint `/listar-directorios` con temp dir, `/buscar` con PDF de prueba | Flask test client + tempfile |
| Frontend | N/A (sin framework de testing frontend en el proyecto) | — |

Usar `tmp_path` de pytest para crear directorios/PDFs temporales. No depender de rutas reales del server.

## Error Handling

| Layer | Estrategia |
|-------|-----------|
| Route | validar ruta ⊆ `PDF_BASE_PATH` → 400 si no; try/except alrededor de buscador → 500 |
| Buscador | PDF corrupto → `extraer_texto()` retorna "" → loguea y continúa con siguiente PDF |
| Extractor | `fitz.open()` en try/except → retorna "" siempre, nunca propaga |

## Open Questions

None — todas resueltas en proposal.
