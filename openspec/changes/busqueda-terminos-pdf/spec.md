# Búsqueda de Términos en PDF — Specification

## Purpose

User selects a server folder via visual navigation, chooses a Condición and Transporte pair, and the system searches all PDFs in that folder for any OTHER unselected options, including custom synonyms.

## Requirements

### R1: Visual folder explorer

`GET /busqueda-pdf/listar-directorios?ruta={path}` MUST return subdirectories of the given path, scoped to `PDF_BASE_PATH` (env var, default `D:\`).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Happy — subdirectories listed | path exists with subdirs | GET `?ruta=D:\PDFs` | status=success, data.directorios has entries with nombre and ruta_completa |
| Invalid path | path does not exist | GET with bad path | status=error, HTTP 400 |
| Path traversal blocked | path contains `..` | GET with `?ruta=D:\..\Windows` | status=error, HTTP 400 |

### R2: React SPA shell

`GET /busqueda-pdf/` MUST serve the React shell with folder selector, Condición/Transporte dropdowns, custom synonyms input, and results table.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Shell loads | browser navigates | GET `/busqueda-pdf/` | 200 OK, HTML with Vite entry point, no JS errors |
| Folder selector | user clicks "Seleccionar carpeta" | modal opens with breadcrumb | fetches `/listar-directorios` for current path |

### R3: PDF text extraction

System MUST extract text from PDFs via PyMuPDF (`fitz`). Scanned/image-only PDFs MUST return empty string without raising.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Text-based PDF | PDF with selectable text layer | extractor processes | non-empty string returned |
| Scanned PDF | image-only PDF | extractor processes | empty string, no exception |

### R4: Term search with synonyms

`POST /busqueda-pdf/buscar` MUST accept `{ruta, condicion, transporte, sinonimos?}` and search all PDFs for unselected Condiciones and Transportes including their synonyms.

Condiciones: Conductor, Ciclista, Peatón, Ocupante.
Transportes: Automóvil, Bus, Buseta, Camión, Camioneta, Campero, Microbus, Tractocamion, Motocicleta, Motocarro, Mototriciclo, Cuatrimoto, Moto extranjera, Vehiculo extranjero, Volqueta, No aplica.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Happy — finds other terms | folder with PDFs containing "Peatón" and "Bus"; user selected Conductor+Moto | POST | resultados lists those PDFs with matched terms and tipo |
| Selected term ignored | PDF contains "Conductor" | user selected Conductor | NOT reported in resultados |
| Default synonyms searched | user selected Ciclista | POST | "Acompañante" and "Pasajero" searched for Ocupante |
| Custom synonyms merged | user sends `sinonimos: {"Ocupante":["Acompaniante2"]}` | POST | "Acompaniante2" added to search; defaults also included |
| Custom override | user sends `sinonimos: {"Ocupante":["Custom"]}` | POST | "Custom" replaces defaults for Ocupante |
| No PDFs in folder | folder with only .txt files | POST | data.resultados empty, message "No se encontraron archivos PDF" |
| All PDFs scanned | folder with 3 image-only PDFs | POST | resultados empty, resumen.pdfs_sin_texto=3 |
| Empty folder | folder with no files | POST | data.resultados empty |

### R5: Error isolation

Batch errors MUST NOT crash the entire request. Each PDF MUST be wrapped in try/except. The system MUST continue processing remaining files.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Corrupt PDF in batch | 5 PDFs, 1 corrupt/unreadable | POST | 4 processed OK, corrupt file listed in errores |
| No read permission | unreadable folder outside base | POST | status=error, HTTP 500 |
| Path not found | nonexistent ruta | POST | status=error, HTTP 400 |
| All PDFs corrupt | all PDFs in folder fail extraction | POST | resultados empty, errores lists all, resumen.pdfs_error=N |

### NF1: Performance

The request SHOULD timeout after 60s (configurable). Each PDF extraction SHOULD log duration at DEBUG level.

## Data Contracts

### GET /busqueda-pdf/listar-directorios

**Success (200):**
```json
{
  "status": "success",
  "data": {
    "directorios": [
      {"nombre": "Enero 2024", "ruta_completa": "D:\\PDFs\\Enero 2024"}
    ]
  },
  "errors": []
}
```

**Error (400):**
```json
{"status": "error", "data": {}, "errors": ["Ruta inválida o fuera de base"]}
```

### POST /busqueda-pdf/buscar

**Request:**
```json
{
  "ruta": "D:\\PDFs\\Enero 2024",
  "condicion": "Conductor",
  "transporte": "Motocicleta",
  "sinonimos": {
    "Ocupante": ["Acompaniante", "Pasajero"]
  }
}
```

**Success (200):**
```json
{
  "status": "success",
  "data": {
    "resultados": [
      {
        "pdf": "factura_001.pdf",
        "ruta_completa": "D:\\PDFs\\Enero 2024\\factura_001.pdf",
        "terminos": [
          {"termino": "Peatón", "tipo": "condicion", "contexto": "...texto alrededor de 40 chars..."}
        ]
      }
    ],
    "resumen": {
      "pdfs_procesados": 10,
      "pdfs_con_hallazgos": 3,
      "pdfs_sin_texto": 1,
      "pdfs_error": 0
    },
    "errores": []
  },
  "errors": []
}
```

**Error (400/500):**
```json
{"status": "error", "data": {}, "errors": ["Ruta no encontrada: D:\\PDFs\\inexistente"]}
```

## Constants

```
CONDICIONES = [
    "Conductor", "Ciclista", "Peatón", "Ocupante"
]

TRANSPORTES = [
    "Automóvil", "Bus", "Buseta", "Camión", "Camioneta",
    "Campero", "Microbus", "Tractocamion", "Motocicleta",
    "Motocarro", "Mototriciclo", "Cuatrimoto",
    "Moto extranjera", "Vehiculo extranjero", "Volqueta",
    "No aplica"
]

SINONIMOS_DEFAULT = {
    "Ocupante": ["Acompañante", "Pasajero"]
}

PDF_BASE_PATH = os.getenv("PDF_BASE_PATH", "D:\\")
```

## Acceptance Criteria

- [ ] R1: Folder listing returns subdirectories for valid paths, 400 for invalid/traversal
- [ ] R2: React shell renders without JS errors; folder selector uses server-side navigation
- [ ] R3: Text-based PDFs extracted; scanned PDFs return empty without crash
- [ ] R4: Search finds unselected Condiciones/Transportes in PDFs
- [ ] R4: Selected term NOT reported
- [ ] R4: Default synonyms (Acompañante, Pasajero) searched for Ocupante
- [ ] R4: Custom sinonimos merged with defaults; overrides applied
- [ ] R4: Empty folder → message, not error
- [ ] R5: Corrupt/scanned PDFs skipped batch continues
- [ ] Response envelope always `{status, data, errors}`
- [ ] All PDFs processed via fitz (PyMuPDF), no new dependencies
- [ ] `<select>` native with Tailwind only — no @radix-ui
- [ ] Tests pass: `python -m pytest -v`
