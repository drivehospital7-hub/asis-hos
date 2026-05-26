# Tipo Factura Registry Specification

## Purpose

Central registry that maps `"Tipo Factura Descripcion"` Excel column values to their detector function lists, replacing hand-maintained detector calls in each orchestrator. Enables dispatch by business type rather than HTTP route.

## Requirements

### R1: Registry Mapping

The registry MUST map each known tipo_factura value to its complete detector list (transversal + domain-specific). Mappings SHALL use string keys matching exact Excel column values.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Urgencias entry | registry queried | `get_detectors("Urgencias")` | returns Urgencias + transversal detectors |
| Hospitalización entry | registry queried | `get_detectors("Hospitalización")` | returns Hospitalización + transversal detectors |
| Intramural entry | registry queried | `get_detectors("Intramural")` | returns Intramural + transversal detectors |
| Ambulatoria entry | registry queried | `get_detectors("Ambulatoria")` | returns Ambulatoria + transversal detectors |
| Odontología entry | registry queried | `get_detectors("Odontología")` | returns Odontología + transversal detectors |

### R2: Unknown Tipo Factura

The system MUST return an empty list when queried with an unrecognized or missing tipo_factura value. It MUST NOT raise exceptions or attempt fallback dispatch.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Unknown value | registry | `get_detectors("Farmacia")` | `[]` — no detectors, no error |
| Empty string | registry | `get_detectors("")` | `[]` — no detectors, no error |
| None value | registry | `get_detectors(None)` | `[]` — no detectors, no error |

### R3: Single Source of Truth

Detector-to-tipo_factura assignments MUST live exclusively in the registry. Orchestrators SHALL NOT hardcode their own detector lists — they MUST delegate to the registry. Adding a new detector to a tipo_factura SHALL require changing only the registry.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Add detector | new detector `detect_x` for Urgencias | append to registry entry | all orchestrators for Urgencias see it |
| Remove detector | obsolete detector for Hospitalización | remove from registry | all orchestrators stop calling it |

### R4: Transversal Inclusion

Every tipo_factura entry SHALL include the full set of transversal detectors (`decimales`, `tipo_documento_edad`, `codigo_entidad_vs_entidad_afiliacion`, `tipo_usuario`). No tipo_factura SHALL skip transversal rules.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Urgencias transversals | registry | `get_detectors("Urgencias")` | includes all transversal detectors |
| Hospitalización transversals | registry | `get_detectors("Hospitalización")` | includes all transversal detectors |
| Intramural transversals | registry | `get_detectors("Intramural")` | includes all transversal detectors |
| Ambulatoria transversals | registry | `get_detectors("Ambulatoria")` | includes all transversal detectors |

### R5: Registry Structure

The registry MUST be a Python module at `app/services/tipo_factura_registry.py`. It SHALL expose a single public function `get_detectors(tipo_factura: str) -> list[Callable]` returning detector functions (not strings). Internal mappings SHALL be a private constant dictionary.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Importable module | project | `from app.services.tipo_factura_registry import get_detectors` | succeeds |
| Returns callables | any valid tipo_factura | `get_detectors("Urgencias")` | list of detector function references |
| No side effects | import or call | `import tipo_factura_registry` | no DB connections, no file I/O |
