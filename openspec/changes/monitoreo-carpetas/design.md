# Design: Monitoreo de Carpetas

## Technical Approach

Paquete standalone `app/services/monitoreo_carpetas/` siguiendo el patrón SRP + orchestrator de `odontologia/detect_all.py`. Escaneo sincrónico con semáforo de concurrencia (`processor_gate.py`), timeout por facturador. Rutas de red configurables por variable de entorno. Resultados en memoria (dict), sin DB — los datos del scan son efímeros. Reporte Excel con openpyxl usando helpers de `app/utils/formatting.py`. Blueprint Flask para trigger y descarga. Frontend React mínimo (trigger + tabla de resultados + download button). Sin cambios en pipeline existente.

## Architecture Decisions

### Decision: Network path configuration
**Choice**: `MONITOREO_CARPETAS_ROOTS` env var (JSON list de rutas UNC)
**Alternatives**: config file YAML, DB table, hardcoded list
**Rationale**: Las rutas de red cambian por entorno (dev/prod). Env var sigue el patrón Flask (ya se usa para `DATABASE_URL`, `SECRET_KEY`). No requiere schema migration ni archivo extra. JSON parseable con `json.loads`.

### Decision: Scan execution model
**Choice**: Sync with `processor_gate` semaphore, per-facturador timeout (30s each)
**Alternatives**: async with asyncio, background thread pool, subprocess per folder
**Rationale**: El proyecto actual es 100% sync con semáforo. 15 facturadores × 30s max = 450s (7.5min) — razonable para un trigger manual. Timeout evita que una carpeta inaccesible bloquee todo. El semáforo (`MAX_CONCURRENT=3`) limita la carga del servidor.

### Decision: Data model for scan results
**Choice**: In-memory dataclasses → list[dict] al final
**Alternatives**: SQLAlchemy models (persistent), JSON file cache
**Rationale**: Los resultados del scan son efímeros — se muestran en frontend y se exportan a Excel. No hay caso de uso para histórico cross-session (out of scope). Usar DB metería schema migration, ORM overhead y cleanup de datos viejos sin beneficio.

### Decision: Excel report format
**Choice**: openpyxl Workbook + `formatting.py` helpers, 2 sheets (Detalle + Indicadores)
**Alternatives**: Polars write_excel, single sheet, CSV
**Rationale**: El proyecto ya usa openpyxl para escritura con estilos consistentes. Dos sheets: (1) Detalle — una factura por fila con estado, ruta, facturador; (2) Indicadores — tabla resumen (total por estado, top anomalías). Usa `PatternFill` y `Border` de `formatting.py`, headers con `create_header_style()`.

### Decision: Frontend scope
**Choice**: React page with trigger button + results table + download button
**Alternatives**: Jinja2 template only, no frontend (just download link)
**Rationale**: El proyecto ya tiene React + Vite + Tailwind + shadcn/ui como estándar. Un trigger en Jinja2 sería inconsistente. La página muestra resultados del scan en tabla, con botón "Exportar Excel" y métricas inline (total por estado, errores). Sin dashboard persistente ni histórico (out of scope).

| Decision | Choice | Key Tradeoff |
|----------|--------|-------------|
| Rutas de red | Env var JSON | Simple vs gestión centralizada |
| Ejecución | Sync + semaphore | Predictible vs lento con 15 carpetas |
| Almacenamiento | In-memory | Simple vs sin histórico |
| Excel | openpyxl + 2 sheets | Consistente vs más boilerplate |
| Frontend | React page | Consistente vs overhead Vite |

## Data Flow

```
Flask Blueprint
     │
     ▼
detect_all() ─── acquire_semaphore()
     │
     ├──► folder_scanner.scan_all(roots[])
     │       │
     │       ├──► por facturador: scandir + timeout 30s
     │       │       ├──► status_inferrer.infer(parent_folder_name)
     │       │       │       └── "Verificada" | "Por corregir" | "En revisión"
     │       │       ├──► name_validator.validate(filename)
     │       │       │       └── FEV regex | CAP regex | INVALID
     │       │       └──► empty_folder.detect(subfolder_list)
     │       │
     │       └──► duplicate_detector.find(invoices_by_facturador)
     │               └── misma factura en >1 facturador
     │
     ├──► report_generator.generate(results)
     │       └── openpyxl Workbook → data/output/
     │
     └──► release_semaphore()
     │
     ▼
Return JSON {facturas, indicadores, excel_download_path}
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/monitoreo_carpetas/__init__.py` | Create | Re-export public functions |
| `app/services/monitoreo_carpetas/detect_all.py` | Create | Orchestrator: scan + detect + build results dict |
| `app/services/monitoreo_carpetas/folder_scanner.py` | Create | `scan_all(roots)` → iterates network dirs, yields invoice records |
| `app/services/monitoreo_carpetas/status_inferrer.py` | Create | `infer_status(folder_path: str) → str` |
| `app/services/monitoreo_carpetas/name_validator.py` | Create | `validate_name(filename) → ("FEV"\|"CAP"\|"INVALID")` |
| `app/services/monitoreo_carpetas/duplicate_detector.py` | Create | `find_duplicates(invoices_by_facturador) → list[dict]` |
| `app/services/monitoreo_carpetas/empty_folder_detector.py` | Create | `detect_empty(facturador_folders) → list[dict]` |
| `app/services/monitoreo_carpetas/report_generator.py` | Create | `generate_excel(results) → Path` (openpyxl) |
| `app/constants/monitoreo_carpetas.py` | Create | Routes config, regex patterns, status keywords, Excel config |
| `app/routes/monitoreo_carpetas.py` | Create | Blueprint: `POST /scan`, `GET /download/<filename>` |
| `app/__init__.py` | Modify | Register `monitoreo_carpetas_bp` |
| `frontend/src/pages/monitoreo-carpetas/index.html` | Create | HTML entry point |
| `frontend/src/pages/monitoreo-carpetas/main.tsx` | Create | React mount |
| `frontend/src/pages/monitoreo-carpetas/page.tsx` | Create | Scan trigger + results table + download |
| `frontend/vite.config.ts` | Modify | Add input entry for `monitoreo-carpetas` |

## Interfaces / Contracts

```python
# Result shape returned by detect_all()
@dataclass
class InvoiceRecord:
    filename: str
    facturador: str
    full_path: str
    status: str          # "Verificada" | "Por corregir" | "En revisión"
    invoice_type: str    # "FEV" | "CAP" | "INVALID"
    invoice_code: str    # parsed invoice number or full filename
    doc_type: str | None # CAP only: CC, TI, etc.
    doc_number: str | None

@dataclass
class ScanResult:
    facturas: list[InvoiceRecord]
    indicadores: dict[str, int | float]
    duplicados: list[dict]
    vacias: list[dict]
    errores_scan: list[dict]  # facturadores inaccesibles
    excel_path: str | None

# detect_all signature
def detect_all(root_paths: list[str]) -> ScanResult
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `status_inferrer.infer_status()` | Parametrized with known folder names → expected enum |
| Unit | `name_validator.validate_name()` | Regex tests for FEV/CAP/INVALID, edge cases |
| Unit | `duplicate_detector.find_duplicates()` | Same invoice in 2+ facturadores → flagged |
| Unit | `empty_folder_detector.detect_empty()` | Empty vs non-empty subfolder lists |
| Unit | `folder_scanner` with `pathlib.Path` mock | Mock filesystem with `tmp_path` fixture |
| Integration | `folder_scanner` + real temp dirs | Create temp dirs, scan them, verify InvoiceRecord |
| Integration | `detect_all()` full pipeline | Create fixture folder tree, run orchestrator, assert result shape |
| E2E | Flask route + React page | `app_client` fixture, POST `/monitoreo-carpetas/scan`, assert JSON + Excel file |

## Migration / Rollout

No migration required. Los facturadores existentes no se modifican. Las rutas de red se configuran vía `MONITOREO_CARPETAS_ROOTS` env var antes del deploy. Rollback: eliminar blueprint registration + borrar el package.

## Open Questions

- [x] Ninguna — las decisiones clave están resueltas arriba
