# Proposal: Optimizar Escaneo

## Intent

El escaneo de carpetas UNC es lento (~7500+ directorios, SMB round-trips). El usuario indicó que **no hace falta validar los PDFs individuales** — el nombre de la carpeta ES el código de factura (ej: `FEV416488`). Basta verificar que la carpeta no esté vacía. Esto elimina el 80% del trabajo actual (enumeración de PDFs + regex por archivo).

## Scope

### In Scope
- Escaneo a nivel de carpeta: verificar `os.listdir()` no vacío en vez de enumerar PDFs
- Escaneo paralelo de raíces con `ThreadPoolExecutor` (usa `MAX_CONCURRENT_SCANS=3` ya definido)
- Pre-filtro `startswith(("FEV","CAP"))` sobre nombre de carpeta antes del regex
- Remover campos muertos `doc_type`/`doc_number` de `InvoiceRecord`

### Out of Scope
- Caché de resultados de escaneo (TTL)
- Modo quick vs full (dos modos de escaneo)
- Reemplazo de `os.walk()` por `os.scandir()` manual
- Cambios en el frontend o API contract

## Capabilities

### Modified Capabilities
- **folder-scanner**: R1 (scan semantics — carpeta-level en vez de PDF-level, raíces paralelas). R3 (structural tolerance — sin cambios en tolerancia, pero semántica de profundidad cambia). Se agrega nuevo requirement para escaneo paralelo.
- **invoice-validator**: R4 (empty folder detection — ahora verifica carpeta no vacía en vez de contar PDFs FEV/CAP). R1-R2 (validación aplicada a nombre de carpeta, no a nombre de archivo PDF).

## Approach

1. **Paralelizar raíces**: `scan_all()` usa `ThreadPoolExecutor(max_workers=MIN(MAX_CONCURRENT_SCANS, len(roots)))` con `SCAN_TIMEOUT_PER_FACTURADOR=30s` por future. Resultados agregados al final.

2. **Escaneo a nivel de carpeta**: `os.walk()` recorre hasta el nivel invoice (profundidad ~4 desde raíz). En ese nivel, verifica `len(os.listdir(path)) > 0`. Si el nombre de carpeta matchea FEV/CAP → `InvoiceRecord` con `invoice_code = folder_name`.

3. **Pre-filtro `startswith`**: Antes del `validate_name()` (regex), verifica `folder_name.upper().startswith(("FEV","CAP"))`. Elimina regex para carpetas no-factura (CRC_, HAU_, etc.).

4. **Limpieza de dataclass**: Remover `doc_type`/`doc_number` de `InvoiceRecord` y del código que los asigna en `_scan_root_walk()`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/monitoreo_carpetas/folder_scanner.py` | Modified | Escaneo paralelo + nivel carpeta + pre-filtro |
| `app/services/monitoreo_carpetas/name_validator.py` | Modified | Validación sobre folder names (misma lógica regex) |
| `app/services/monitoreo_carpetas/__init__.py` | Modified | Remover `doc_type`/`doc_number` de InvoiceRecord |
| `app/services/monitoreo_carpetas/duplicate_detector.py` | None | Sigue usando `filename` — sin cambios |
| `app/services/monitoreo_carpetas/detect_all.py` | None | Solo consume `scan_all()` — sin cambios |
| `tests/services/monitoreo_carpetas/test_folder_scanner.py` | Modified | Actualizar tests a nueva semántica |
| `tests/services/monitoreo_carpetas/test_name_validator.py` | None | Regex patterns sin cambios |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Carpeta invoice vacía pero legítima (sin archivos aún) | Low | Se marca como vacía — igual que antes |
| Timeout en thread paralelo deja raíz sin escanear | Low | `future.result(timeout=30)`; raíz con timeout se registra como error |
| Nombre de carpeta no sigue patrón FEV/CAP | Low | Se marca como Unknown — el pre-filtro `startswith` igual deja pasar solo FEV/CAP |
| Thread safety al agregar resultados | None | Cada thread produce resultados independientes; agregación secuencial post-join |

## Rollback Plan

Revertir cambios en `folder_scanner.py`, `__init__.py` y `name_validator.py` al commit anterior. Los tests existentes (`test_folder_scanner.py`, `test_name_validator.py`) validan que la funcionalidad previa funciona. El cambio es autocontenido en el módulo `monitoreo_carpetas/` — no afecta a `odontologia/`, `urgencias/` ni otros servicios.

## Dependencies

- `MAX_CONCURRENT_SCANS` y `SCAN_TIMEOUT_PER_FACTURADOR` ya existen en `app/constants/monitoreo_carpetas.py` — no se crean constantes nuevas.

## Success Criteria

- [ ] Tiempo de escaneo reducido ≥ 60% vs baseline actual (7500+ dirs)
- [ ] Misma cantidad de facturas detectadas (zero data loss vs baseline)
- [ ] Tests existentes pasan (ajustados a nueva semántica)
- [ ] Sin regresión en carpetas vacías y detección de duplicados
