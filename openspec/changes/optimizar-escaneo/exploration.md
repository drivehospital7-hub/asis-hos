# Exploration: Performance Optimization for Folder Scanner

## Current State

`folder_scanner.py` uses `os.walk()` to recursively traverse network UNC paths (~15 facturadores with deep nesting). For each `.pdf` file found, it calls `validate_name()` (which runs full regex via `fullmatch` on both FEV and CAP patterns). It then constructs an `InvoiceRecord` per valid match and, at the end, detects "empty" first-level dirs by comparing against found facturadores.

### Measured Bottlenecks

| Bottleneck | Impact | Evidence |
|---|---|---|
| **`os.walk()` over SMB** | HIGH | Walks ALL directories (est. ~7500+ dirs for 15 facturadores × 5 companies × 100 invoices). Each `opendir` on UNC is a network round-trip (50-200ms). `os.walk` is implemented in C but still pays network latency per directory. |
| **Validating ALL PDFs** | MEDIUM | Each invoice folder has ~6 files (FEV416488.pdf + CRC_*, HAU_*, OPF_*, PDE_*, etc.) but only 1 matches FEV/CAP. That's ~6 regex calls per valid invoice — 80% wasted work. |
| **Single-threaded** | HIGH | Filesystem I/O on network paths is latency-bound. Processing roots sequentially means waiting for each root's full traversal before starting the next. SMB connections are independent per root, so there's zero contention. |
| **`full_path` via Path objects** | LOW | `str(dir_path / pdf_name)` creates a Path per file. Negligible vs. network I/O, but avoidable. |
| **`doc_type`/`doc_number` parsing** | ZERO (dead code) | Computed for every CAP file but **never read** by any consumer (route, report, duplicate_detector, detect_all). Zero impact on speed, but unnecessary complexity. |

### Data Flow (what actually consumes what)

```
scan_all() → InvoiceRecord[]
  ├── route: {filename, facturador, full_path, status, invoice_type, invoice_code}
  ├── report: {invoice_code, invoice_type, status, full_path, facturador, filename}
  ├── duplicate_detector: {filename, facturador, full_path}
  └── doc_type, doc_number → 🔴 NEVER READ
```

## Affected Areas

- `app/services/monitoreo_carpetas/folder_scanner.py` — Primary target: scanning logic
- `app/services/monitoreo_carpetas/name_validator.py` — May need `startswith` fast-path or remain unchanged
- `app/services/monitoreo_carpetas/__init__.py` — `InvoiceRecord.dataclass`: remove dead `doc_type`/`doc_number` fields
- `app/services/monitoreo_carpetas/detect_all.py` — May need cache integration
- `app/constants/monitoreo_carpetas.py` — `MAX_CONCURRENT_SCANS` and `SCAN_TIMEOUT_PER_FACTURADOR` already defined (parallel infrastructure exists in config but is unused)
- `tests/services/monitoreo_carpetas/test_folder_scanner.py` — Tests must remain green
- `tests/services/monitoreo_carpetas/test_integration.py` — Tests must remain green

## Approaches

### 1. `startswith()` Pre-filter Before Regex

**Description**: Add a fast-path check in `validate_name()` or in `folder_scanner.py` that first checks `filename.upper().startswith(("FEV", "CAP"))` before running the full regex. Filters out CRC_*, HAU_*, OPF_*, PDE_* files at O(1) cost.

- **Pros**: Trivially safe, impossible to break existing behavior (regex still runs on actual matches), eliminates ~80% of regex calls, ~5 lines of code
- **Cons**: Marginal gain — regex was never the bottleneck, network I/O is
- **Effort**: Low (~15 min)
- **Risk**: Near-zero

### 2. `os.scandir()` with Depth Limiting

**Description**: Replace `os.walk()` with manual `os.scandir()` recursion that limits depth to 4 levels (root/facturador/company/invoice_folder/files). Skip hidden dirs, `.tmp` dirs, and non-directory entries at upper levels. At leaf level, only look for files whose names start with the parent directory name (e.g., `FEV416488` → look for `FEV416488.pdf`).

- **Pros**: Avoids descending into unrelated directories, eliminates filesystem touches for non-invoice dirs, can skip `.tmp`/hidden dirs, more control over traversal
- **Cons**: More complex code, manual recursion in Python (slower per-iteration than C `os.walk`), edge cases with non-standard directory structures
- **Effort**: Medium (2-4 hours)
- **Risk**: Low-Medium — must handle directory structure variations

### 3. Parallel Scanning via `ThreadPoolExecutor`

**Description**: Scan each root path in a separate thread using `concurrent.futures.ThreadPoolExecutor`. The constants already define `MAX_CONCURRENT_SCANS = 3` and `SCAN_TIMEOUT_PER_FACTURADOR = 30` — the infrastructure exists in config but is never used.

- **Pros**: **BIGGEST win for UNC paths** — network I/O is latency-bound, threads let us overlap SMB round-trips. With 3 concurrent scans, 3 roots are scanned in parallel. Scales to more roots.
- **Cons**: Thread management overhead (minimal for 3-5 threads), error handling slightly more complex, need to aggregate results from concurrent workers
- **Effort**: Low-Medium (1-2 hours)
- **Risk**: Low — roots are independent (no shared state within a root), Python's GIL doesn't block I/O-bound threads

### 4. Cache Scan Results

**Description**: Store the last `ScanResult` in memory (or a JSON file) with a TTL of 30-60 seconds. Subsequent calls to `/scan` return cached data without re-scanning.

- **Pros**: Eliminates re-scan entirely for rapid refreshes, very simple to implement (decorator or `lru_cache` with timeout), no changes to scanning logic
- **Cons**: Stale data for up to TTL duration, cache invalidation on explicit demand, memory overhead for the result object
- **Effort**: Low (1 hour)
- **Risk**: Low — data freshness is bounded by TTL, and the scan endpoint can accept a `?force=true` param

### 5. Remove Dead Fields (`doc_type` / `doc_number`)

**Description**: Remove `doc_type` and `doc_number` from `InvoiceRecord` dataclass and from the scanner's CAP parsing logic. These fields are set but NEVER read by any consumer.

- **Pros**: Cleaner code, less confusion, removes dead branches
- **Cons**: Zero performance impact (they were computed anyway), breaking change if any external code reads these fields (none found)
- **Effort**: Low (30 min)
- **Risk**: Near-zero — grep confirms no reads

### 6. Two-Mode Scan: Quick vs Full

**Description**: Add a `mode=quick` parameter that only lists first-level directories and infers status from folder names, without recursing into invoices. Returns facturadores + status + empty flags, but no individual invoice data or counts.

- **Pros**: Near-instant for dashboard-like views, gives user a choice between speed and detail
- **Cons**: Frontend changes needed, more surface area, two code paths to maintain, may confuse users
- **Effort**: High (4-6 hours + frontend)
- **Risk**: Medium — API contract changes, frontend dependency

## Comparison Matrix

| Approach | Speed Impact | Complexity | Risk | Effort |
|---|---|---|---|---|
| 1. `startswith` pre-filter | Marginal | Trivial | Near-zero | ~15 min |
| 2. `os.scandir` depth-limit | Medium | Medium | Low-Med | 2-4 hr |
| 3. **Parallel scanning** | **HIGH** | Low-Med | Low | 1-2 hr |
| 4. Cache results | High (repeat scans) | Low | Low | 1 hr |
| 5. Remove dead fields | Zero | Trivial | Zero | 30 min |
| 6. Two-mode scan | High (quick mode) | High | Medium | 4-6 hr |

## Data That Can Be Omitted Safely

| Field | Consumers | Can Omit? |
|---|---|---|
| `doc_type` | **None** | ✅ Yes — never read |
| `doc_number` | **None** | ✅ Yes — never read |
| `full_path` | Route, Report, DupDetector | ❌ No — used by all three |
| Full recursion (quick mode) | Route needs individual invoices | ❌ No — breaks API contract |

## Recommendation

**Primary**: Combine **Approach 3 (Parallel Scanning)** with **Approach 1 (`startswith` pre-filter)** and **Approach 5 (Remove dead fields)**.

Rationale:
- **Parallel scanning** gives the biggest actual speedup for UNC paths (network I/O is the real bottleneck, not CPU). The config constants (`MAX_CONCURRENT_SCANS`, `SCAN_TIMEOUT_PER_FACTURADOR`) already exist but are unused — this is clearly the intended path.
- **`startswith` pre-filter** is trivial insurance that costs nothing and eliminates wasted regex calls.
- **Remove dead fields** is cleanup — zero risk, makes the code honest.

**Secondary/optional**: Add **Approach 4 (Cache)** if users report rapid-reload scenarios. Implement after the primary changes.

**Not recommended now**: `os.scandir` depth-limiting (adds complexity for marginal gain since `os.walk` is already C-implemented) and Two-mode scan (too much scope, needs frontend work).

## Risks

| Risk | Approach | Mitigation |
|---|---|---|
| Thread contention on SMB | Parallel scanning | SMB connections are per-root, independent; use `MAX_CONCURRENT_SCANS=3` (already defined) |
| Stale cache data | Cache | TTL + `?force=true` param |
| `startswith` false negatives | Pre-filter | Rare but possible if a valid invoice file doesn't start with FEV/CAP (none known) — the regex fallback still catches it |
| Parallel scan timeout | Parallel scanning | Already have `SCAN_TIMEOUT_PER_FACTURADOR=30` in constants; use `timeout=` in `ThreadPoolExecutor` |
| Dead field removal is breaking | Cleanup | Only breaking if external code imports `InvoiceRecord` and accesses `.doc_type` — not the case in this project |

### 7. No Validar PDFs — Solo Verificar Carpeta No Vacía

**Description**: En lugar de enumerar archivos PDF individuales y validar regex FEV/CAP, solo verificar que la carpeta de factura (nombrada FEV\* o CAP\*) tenga al menos un archivo. El nombre de la carpeta YA es el código de factura (ej: `FEV416488`). No hay necesidad de validar los PDFs adentro — con que la carpeta exista y no esté vacía, es suficiente.

- **Pros**: **Elimina el 80% del trabajo** — no más `validate_name()` por PDF, no más regex, no más enumerar archivos. Reduce la profundidad de escaneo (no entramos a las carpetas de factura). Escala a miles de facturas sin penalidad.
- **Cons**: No detecta si el PDF tiene nombre inválido (pero eso no es relevante para el monitoreo operativo). Datos de factura vienen del nombre de carpeta, no del archivo.
- **Effort**: Medium (reestructura el scanner)
- **Risk**: Low — el nombre de la carpeta es la fuente de verdad

## Ready for Proposal

**Yes**. The bottlenecks are clearly understood, the approaches are scoped and compared, and the recommended path (parallel scanning + startswith filter + dead field removal) is well-bounded. The orchestrator should present these findings to the user and propose the implementation plan.
