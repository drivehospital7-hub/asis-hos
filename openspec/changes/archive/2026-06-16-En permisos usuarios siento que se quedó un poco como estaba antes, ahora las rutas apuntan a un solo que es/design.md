# Design: Unified Permission Model — /procesar, cronogramas, and security gating

## Architecture Decision: Unified `/procesar` Permission

### Problem

Three area-specific permissions (`odontologia`, `urgencias`, `odontologia_equipos_basicos`) each gated separate routes that now all point to a single `/procesar` endpoint. This creates confusion — a user with `odontologia` can't access `/procesar` even though that's where their work happens.

### Decision

Replace the three old permissions with a single `procesar` permission. Add `procesar:write` for write operations (mutually exclusive with `procesar`). Add granular `cronograma_bacteriologas` and `cronograma_urgencias` permissions for cronograma access.

### Migration Strategy

`_load_users()` in `app/utils/users_store.py` performs automatic migration:
- `odontologia` → `procesar`
- `urgencias` → `procesar`
- `odontologia_equipos_basicos` → `procesar`
- Deduplication: if a user has multiple old perms, they get a single `procesar`
- `equipos_basicos` (Ordenado y Facturado) is preserved unchanged — it's a different permission
- Admin (`"*"`) is untouched

### Route Security Gating

| Route | Old Decorator | New Decorator |
|-------|--------------|---------------|
| `/procesar/` GET+POST | `@permiso_requerido("odontologia")` or `@permiso_requerido("urgencias")` | `@permiso_requerido("procesar")` |
| `/cronograma-bacteriologas/` (4 endpoints) | `@permiso_requerido("*")` | `@permiso_requerido("cronograma_bacteriologas")` |
| `/cronograma-urgencias/` (3 endpoints) | `@permiso_requerido("*")` | `@permiso_requerido("cronograma_urgencias")` |
| `/derechos/` API | None (unprotected) | `@permiso_requerido("derechos")` |
| `/procedimientos/` (5 endpoints) | None | `@admin_requerido` |
| `/notas-api/` (~30 endpoints) | None (2 protected) | `@admin_requerido` |
| `/import-csv/` (5 endpoints) | None | `@admin_requerido` |

### Constants Changes

```python
# ALLOWED_PERMISOS — removed 3, added 4
ALLOWED_PERMISOS = frozenset({
    "*", "procesar", "procesar:write", "control_urgencias",
    "control_urgencias:write", "facturas_abiertas", "facturas_abiertas:write",
    "equipos_basicos", "cruce_facturas", "derechos",
    "cronograma_bacteriologas", "cronograma_urgencias",
})

# PERMISO_MUTUAL_EXCLUSION — added procesar pair
PERMISO_MUTUAL_EXCLUSION = {
    "control_urgencias": "control_urgencias:write",
    "control_urgencias:write": "control_urgencias",
    "facturas_abiertas": "facturas_abiertas:write",
    "facturas_abiertas:write": "facturas_abiertas",
    "procesar": "procesar:write",
    "procesar:write": "procesar",
}
```

### Frontend

Sidebar `ALL_NAV` updates the Procesar entry's permiso from `"urgencias"` to `"procesar"` and cronograma entries from `"*"` to their respective new permisos. The usuarios page `ALL_PERMISOS` array replaces old permisos with new ones. Frontend pages for old areas (`odontologia/`, `urgencias/`, `odontologia-equipos-basicos/`) are deleted.
