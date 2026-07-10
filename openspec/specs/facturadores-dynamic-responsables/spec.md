# Facturadores — Responsables Dinámicos

## Purpose

Reemplazar responsables hardcodeados (duplicados en 3 lugares del sistema) por una lista dinámica: usuarios con rol `"facturador"` servida por un endpoint único. El admin define quién es facturador desde la UI de usuarios; control-errores, carga masiva y abiertas-urgencias se sincronizan automáticamente. Si no hay facturadores, el sistema degrada gracefulmente a los valores hardcodeados.

## Requirements

### R1: `users_store.get_facturadores()` — Store Query

`users_store` MUST exponer `get_facturadores()` que retorne todos los usuarios con `rol == "facturador"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Returns facturadores | store has 2 facturadores + 3 otros roles | `get_facturadores()` | returns list of 2 user dicts |
| Empty result | no user has rol="facturador" | `get_facturadores()` | returns `[]` |
| Fields returned | facturador exists | `get_facturadores()` | each dict incluye `username`, `primer_nombre`, `apellido_1`, `rol` |
| Non-destructive | store has users | `get_facturadores()` | other users unaffected |

### R2: `GET /api/users/facturadores` — API Endpoint

The system MUST exponer `GET /api/users/facturadores` decorado con `@login_requerido` que retorne la lista de facturadores.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Success | authenticated, 2 facturadores | `GET /api/users/facturadores` | `{"status":"success","data":{"facturadores":[...]}}` |
| Empty | authenticated, 0 facturadores | `GET /api/users/facturadores` | `{"status":"success","data":{"facturadores":[]}}` |
| Unauthenticated | no session | `GET /api/users/facturadores` | 401 or redirect |

### R3: `control_errores_service.get_opciones()` — Responsables Dinámicos

`get_opciones()` MUST reemplazar las constantes hardcodeadas por `get_facturadores()`. SHALL retornar `error_responsable`, `responsable_nombres_completos`, `cronograma_nombre_map` en el mismo formato que hoy.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Facturadores exist | 3 facturadores en store | `get_opciones()` | `responsables` tiene 3 entries mapeados desde users |
| Same response shape | facturadores exist | `get_opciones()` | response keys `error_responsable`, `responsable_nombres_completos`, `cronograma_nombre_map` presentes |
| Name format | facturador with `primer_nombre="Ana"`, `apellido_1="López"` | `get_opciones()` | entry name = `"ANA LÓPEZ"` (uppercase) |

### R4: Fallback a Hardcodeados

If `get_facturadores()` returns `[]`, the system MUST usar los valores hardcodeados de `app/constants/urgencias.py` como fallback.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| No facturadores | store vacío, constants tiene 4 hardcodeados | `get_opciones()` | responsables = hardcodeados |
| Partial fallback | 0 facturadores | `get_opciones()` | `RESPONSABLE_NOMBRES_COMPLETOS` y `CRONOGRAMA_NOMBRE_MAP` también caen a hardcodeados |
| Transition | admin crea 1er facturador | next `get_opciones()` call | ahora retorna el facturador, no hardcodeados |

### R5: Abiertas-urgencias — Consumir `/api/users/facturadores`

`frontend/src/pages/abiertas-urgencias/` MUST reemplazar `constants.ts` hardcodeados por fetch a `/api/users/facturadores` al montar el componente.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Fetch on mount | page loads | `useEffect` | `GET /api/users/facturadores` called; response sets state |
| Facturadores OK | 3 facturadores returned | `handleSendToControl()` | `responsable` string from dynamic list |
| Fallback applied | empty response | component mounts | uses hardcoded values as fallback |
| Loading state | fetch in progress | component renders | no crash; renders empty or loading placeholder |

## Constraints

- `get_opciones()` output format MUST remain identical — no breaking changes for existing frontend JS
- Fallback hardcodeados SHOULD emit `logger.warning("No hay facturadores en users.json, usando fallback hardcodeado")`
- `get_facturadores()` SHALL NOT modify `_save_users()` or any write path
- Abiertas-urgencias SHALL cache the facturadores list in component state (not localStorage) and re-fetch on mount
