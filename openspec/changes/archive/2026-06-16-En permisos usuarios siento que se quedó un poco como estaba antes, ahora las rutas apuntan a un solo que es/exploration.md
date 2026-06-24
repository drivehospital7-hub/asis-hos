# Exploration: Unified Permission Model

## Context

The user reported: "En permisos usuarios siento que se quedó un poco como estaba antes, ahora las rutas apuntan a un solo que es /procesar donde se unifican hechale un revisada y acomoda los checks de permisos, lo mismo con los cronogramas."

This means:
1. Permissions still reference old per-route values (`odontologia`, `urgencias`, `odontologia_equipos_basicos`) when all routes now go through `/procesar`
2. Cronogramas are gated by `"*"` (admin-only) but should have their own granular permissions
3. Several route files lack permission decorators entirely, leaving security gaps

## Findings

- `ALLOWED_PERMISOS` in `app/constants/base.py` still had the three old permisos
- `DEFAULT_USERS` had old permission names
- `DEFAULT_TEMPLATES` referenced old perms
- Sidebar nav items used old perm names
- Cronograma routes used `@permiso_requerido("*")` — admin-only
- `derechos.py`, `procedimientos.py`, `notas_api.py`, `import_csv.py` had routes with zero permission decorators
- Frontend usuarios page `ALL_PERMISOS` had old checkboxes

## Recommendation

Proceed with the SDD process: constants update → migration logic → route decorators → frontend → tests.
