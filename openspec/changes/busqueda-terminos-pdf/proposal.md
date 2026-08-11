# Proposal: Búsqueda de Términos en PDFs

## Intent

Usuario selecciona visualmente una carpeta del servidor, elige par Condición + Transporte, y el sistema busca en todos sus PDFs si aparecen las OTRAS opciones (incluyendo sinónimos custom). Sin escribir rutas a mano.

## Scope

### In Scope
- Visual folder selector (navegación server-side por directorios)
- PDF text extraction (PyMuPDF — ya instalado)
- Búsqueda de términos Condición (5) + Transporte (15) con sinónimos custom
- Endpoints: `GET /`, `GET /listar-directorios`, `POST /buscar`
- Permiso nuevo `busqueda_pdf` + dashboard + sidebar
- Sinónimos default + custom por request (sesión in-memory, v1 sin DB)

### Out of Scope
- OCR para PDFs escaneados
- Búsqueda recursiva en subcarpetas
- Exportación a Excel
- Validación de facturas/derechos

## Capabilities

### New Capabilities
- `busqueda-terminos-pdf`: Búsqueda de términos Condición y Transporte en PDFs de una carpeta seleccionable visualmente.

### Modified Capabilities
- None

## Approach

### Backend
| Layer | Archivo | Rol |
|-------|---------|-----|
| Route | `app/routes/busqueda_pdf.py` | Blueprint `busqueda_pdf_bp`, 3 endpoints |
| Service | `app/services/busqueda_pdf/extractor.py` | Extrae texto vía PyMuPDF (`fitz`) |
| Service | `app/services/busqueda_pdf/buscador.py` | Orquestador: recorre PDFs, busca términos, clasifica |
| Service | `app/services/busqueda_pdf/sinonimos.py` | Mapa default + merge con custom del payload |
| Constants | `app/constants/busqueda_pdf.py` | `CONDICIONES`, `TRANSPORTES`, `SINONIMOS_DEFAULT` |

Endpoints:
- `GET /busqueda-pdf/` → React shell (mismo patrón que `/derechos/auditoria`)
- `GET /busqueda-pdf/listar-directorios?ruta=` → lista subdirectorios (para navegación)
- `POST /busqueda-pdf/buscar` → `{ruta, condicion, transporte, sinonimos}` → resultados

### Frontend
| Archivo | Rol |
|---------|-----|
| `frontend/src/pages/busqueda-pdf/index.html` | Entry HTML |
| `frontend/src/pages/busqueda-pdf/main.tsx` | React mount + AppLayout |
| `frontend/src/pages/busqueda-pdf/page.tsx` | Componente principal |

UI flow:
1. Botón "Seleccionar carpeta" → modal con árbol navegable (fetch a `/listar-directorios`)
2. Selectores nativos (`<select>`) para Condición y Transporte
3. Input de sinónimos custom por término (textarea clave:valor)
4. Botón "Buscar" → tabla de resultados con PDF, término encontrado, tipo

### Folder selector
Backend lista subdirectorios de una ruta base configurable (`PDF_BASE_PATH` en config o env). Frontend muestra breadcrumb navegable. Sin `<input type="file">` del browser — es navegación server-side.

### Synonyms
Defaults hardcodeados en `constants/busqueda_pdf.py`. Usuario puede sobrescribir/extender vía payload. El frontend los envía en cada request. V1 sin persistencia.

### PDF library: PyMuPDF
Ya en `requirements.txt`, usado en `app/services/auditoria/extractor.py`. Texto plano rápido. Sin nuevas dependencias.

## Costo estimado (~628 líneas)

| Archivo | Líneas |
|---------|--------|
| `app/routes/busqueda_pdf.py` | 120 |
| `app/services/busqueda_pdf/__init__.py` | 1 |
| `app/services/busqueda_pdf/extractor.py` | 40 |
| `app/services/busqueda_pdf/buscador.py` | 100 |
| `app/services/busqueda_pdf/sinonimos.py` | 40 |
| `app/constants/busqueda_pdf.py` | 30 |
| `frontend/src/pages/busqueda-pdf/page.tsx` | 250 |
| `frontend/src/pages/busqueda-pdf/main.tsx` | 15 |
| `frontend/src/pages/busqueda-pdf/index.html` | 12 |
| Modificaciones (vite.config.ts, base.py, sidebar, dashboard) | 20 |
| **Total** | **~628** |

## Escenarios

### Happy path
Usuario: selecciona carpeta → Condición=Conductor, Transporte=Moto → sistema encuentra 3 PDFs con "Peatón", 1 con "Ciclista", 2 con "Bus" → tabla coloreada

### Edge cases
- Carpeta vacía: "No se encontraron PDFs"
- PDF sin texto (escaneado): reporta "sin texto extraíble", no crashea
- Sinónimos vacíos: usa defaults sin merge
- Sinónimo duplicado: prioriza el del usuario

### Error cases
- Ruta inválida/no existe: error 400
- Sin permisos de lectura: error 500 con mensaje claro
- PDF corrupto: try/except por archivo, continúa con los demás

## Riesgos

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| PDFs escaneados sin OCR | Media | Reportar por archivo, no fallar batch |
| Listados de >100 subdirectorios | Baja | Paginación si necesario |
| Sinónimos colisionan con términos exactos | Baja | Priorizar coincidencia exacta en reporte |

## Rollback Plan
- `git revert` del merge commit
- Quitar entrada en `vite.config.ts` rollupOptions y rebuild
- Quitar permiso `busqueda_pdf` de `constants/base.py`, dashboard y sidebar

## Dependencies
- PyMuPDF (`fitz`) — ya instalado
- Ninguna nueva

## Success Criteria
- [ ] Usuario navega y selecciona carpeta sin escribir rutas
- [ ] Búsqueda encuentra términos en PDFs de texto plano
- [ ] Sinónimos custom se aplican correctamente
- [ ] PDFs sin texto se reportan sin crash
- [ ] Tests pasan: `python -m pytest -v`

## Preguntas para el usuario

1. **Base path**: Carpeta raíz desde donde se navega? (ej: `D:\PDFs\` configurable vía env `PDF_BASE_PATH`)
2. **Sinónimos**: Persistencia en DB o solo por request/sesión?
3. **Select UI**: Usar `<select>` nativo con Tailwind (sin nueva dependencia) o instalar `@radix-ui/react-select`?
