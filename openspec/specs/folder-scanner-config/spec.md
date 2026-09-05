# Folder Scanner Config Specification

## Purpose

Administrar rutas raíz de escaneo desde la UI con persistencia JSON atómica y fallback a variable de entorno. Los módulos consumidores leen desde este store — nunca acceden a `os.environ` directamente.

---

## Requirements

### R1: Read Roots with Fallback

The system MUST return root directories in priority order: manual JSON > env var > empty list. The `fuente` field SHALL indicate which source was used.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Manual JSON exists | `monitoreo_carpetas_config.json` has `["//srv/a", "//srv/b"]` | `get_roots()` called | returns `["//srv/a", "//srv/b"]`, `fuente = "manual"` |
| Fallback to env var | JSON absent, `MONITOREO_CARPETAS_ROOTS` set to `["//srv/env"]` | `get_roots()` called | returns `["//srv/env"]`, `fuente = "env"` |
| Neither configured | no JSON, no env var | `get_roots()` called | returns `[]`, `fuente = "env"` |
| JSON corrupt | JSON file contains `{bad syntax}` | `get_roots()` called | logs corruption warning, falls back to env var or empty |

### R2: Save Roots Atomically

The system MUST persist roots to JSON using `tempfile.mkstemp` + `Path.replace()`. The file SHALL include `roots`, `fuente: "manual"`, and `ultima_actualizacion` ISO timestamp.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| First save | no JSON exists | `save_roots(["//ruta1"])` | JSON created; `get_roots()` returns `["//ruta1"]`, `fuente = "manual"` |
| Overwrite existing | JSON has `["//old"]` | `save_roots(["//new"])` | JSON has only `["//new"]`; no stale content visible |
| Write failure | disk full during write | `save_roots(...)` | exception raised; original JSON unmodified |

### R3: Reset to Env Default

The system MUST delete the JSON file so the next `get_roots()` falls back to env var.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Reset from manual | JSON exists with 2 manual roots | `reset_roots()` called | JSON deleted; `get_roots()` returns env var value |
| Reset with no JSON | no JSON file | `reset_roots()` called | succeeds silently (no-op) |

### R4: Env Var Parsing

The system SHALL parse `MONITOREO_CARPETAS_ROOTS` as JSON array first, with semicolon-separated fallback (matching the existing `POST /scan` behavior).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| JSON array env | env var = `["//a", "//b"]` | fallback read | returns `["//a", "//b"]` |
| Semicolon env | env var = `//a;//b` | fallback read | returns `["//a", "//b"]` |
| Empty env | env var = `""` | fallback read | returns `[]` |
