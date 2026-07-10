# Design: Roles Facturador y Responsables Dinámicos

## Technical Approach

Pipeline minimal: `users_store.get_facturadores()` → `GET /api/users/facturadores` → `control_errores_service.get_opciones()` (reemplaza constantes) → auto-propaga a control-errores filter, carga masiva, y abiertas-urgencias vía el mismo endpoint. Fallback a constantes hardcodeadas si no hay facturadores.

## Architecture Decisions

### Decision: Fallback strategy

| Option | Tradeoff |
|--------|----------|
| Error si no hay facturadores | Rompe filter existente |
| **Fallback silent a hardcode** | Cero regresión, migración segura |

**Choice**: Si `get_facturadores()` retorna vacío, `get_opciones()` sirve `ERROR_RESPONSABLE_URGENCIAS` / `RESPONSABLE_NOMBRES_COMPLETOS` (actuales constantes).

### Decision: Composición del nombre de facturador

**Choice**: `primer_nombre + " " + apellido_1` (mayúsculas). Refleja el formato de los responsables actuales y coincide con `validador` en `add_error()`.

### Decision: CRONOGRAMA_NOMBRE_MAP se queda hardcodeado

**Choice**: El map de abreviaciones del cronograma a nombres completos NO se deriva de usuarios. Es un dominio distinto (schedule names ≠ user names). Sigue en `urgencias.py` y `constants.ts` como constantes. Si el admin crea un facturador nuevo, debe actualizar ambos maps manualmente.

## Data Flow

```
users_store JSON
      │
      ├── get_facturadores()  ← filtra rol=="facturador"
      │       │
      │       ▼
      │  GET /api/users/facturadores   ← auth.py
      │       │
      │       ├── control_errores_service.get_opciones()
      │       │       │
      │       │       ▼
      │       │  GET /api/control-errores/opciones
      │       │       │
      │       │       ├── Filter dropdown (control_errores.html)
      │       │       ├── Carga masiva _matchResponsable()
      │       │       └── Abiertas-urgencias validation
      │       │
      │       └── GET /auth/api/facturadores (React, si se necesita)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/utils/users_store.py` | Modify | Expand rol validation, add `get_facturadores()`, `FACTURADOR_ROLES` constant |
| `app/routes/auth.py` | Modify | Add `GET /api/users/facturadores` endpoint |
| `app/services/control_errores_service.py` | Modify | `get_opciones()` pulls from `get_facturadores()`, fallback a constants |
| `app/constants/urgencias.py` | None (logic) | Constants remain as fallback values — no code changes |
| `app/templates/control_errores.html` | None (auto) | JS reads `opciones.responsables` — se actualiza solo |
| `app/templates/usuarios.html` | Modify | Role dropdown: +"Médico", +"Facturador" (si existe — no encontrado en FS) |
| `frontend/src/pages/usuarios/page.tsx` | Modify | Role `<select>`: add `medico` and `facturador` options |
| `frontend/src/pages/abiertas-urgencias/constants.ts` | None | `NOMBRE_MAP` stays (schedule domain, out of scope) |
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modify | Fetch facturadores on mount, validate responsable against list |
| `frontend/src/pages/abiertas-urgencias/utils.ts` | None | Functions use NOMBRE_MAP which stays unchanged |
| `tests/utils/test_users_store.py` | Modify | Add rol tests for `medico`/`facturador`, `get_facturadores()` tests |
| `tests/services/test_control_errores_service.py` | Modify | `get_opciones()` now depends on facturadores |

## Interfaces / Contracts

### `GET /api/users/facturadores`

```python
# Response
{
    "status": "success",
    "data": {
        "facturadores": [
            {
                "username": "jperez",
                "primer_nombre": "JUAN",
                "segundo_nombre": "",
                "apellido_1": "PEREZ",
                "apellido_2": "",
                "nombre_completo": "JUAN PEREZ"       # ← compuesto
            }
        ],
        "responsables_nombres_completos": {
            "JUAN PEREZ": "JUAN FELIPE PEREZ GOMEZ"   # ← primer_nombre segundo_nombre apellido_1 apellido_2
        }
    },
    "errors": []
}
```

### `get_opciones()` modified contract

```python
# Return shape (unchanged from current):
{
    "tipos_error": [...],                    # unchanged
    "estados": [...],                        # unchanged
    "responsables": [str, ...],              # was ERROR_RESPONSABLE_URGENCIAS, now get_facturadores()
    "responsables_nombres_completos": {...},  # was RESPONSABLE_NOMBRES_COMPLETOS, now from facturadores
}
```

### `users_store.get_facturadores()`

```python
def get_facturadores() -> list[dict]:
    """Returns users with rol == 'facturador', with nombre_completo."""
    users = _load_users()
    return [
        {
            "username": u["username"],
            "primer_nombre": u.get("primer_nombre", ""),
            "segundo_nombre": u.get("segundo_nombre", ""),
            "apellido_1": u.get("apellido_1", ""),
            "apellido_2": u.get("apellido_2", ""),
            "nombre_completo": f"{u.get('primer_nombre', '')} {u.get('apellido_1', '')}".strip().upper(),
        }
        for u in users
        if u["rol"] == "facturador" and u.get("primer_nombre", "").strip()
    ]
```

## Error Handling

| Edge Case | Behavior |
|-----------|----------|
| No users have `rol=facturador` | `get_facturadores()` retorna `[]` → `get_opciones()` usa fallback (hardcode) |
| Facturador sin `primer_nombre` | Excluido del listado (no se puede renderizar nombre) |
| JSON store corrupto | `_load_users()` retorna `[]` → `get_facturadores()` retorna `[]` → fallback |
| Endpoint llamado sin auth | `GET /api/users/facturadores` requiere admin (decorador `@admin_requerido`) |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `update_user()` rol validation for `medico`/`facturador` | Patch `_load_users`, call `update_user()`, assert `(True, msg)` |
| Unit | `get_facturadores()` returns only `rol=facturador` | Patch `_load_users` with mixed roles, assert filtered result |
| Unit | `get_facturadores()` excludes users without `primer_nombre` | Patch with facturador that has empty `primer_nombre`, assert excluded |
| Unit | `get_opciones()` fallback when no facturadores | Mock `get_facturadores()` → `[]`, assert response from constants |
| Unit | `get_opciones()` returns facturadores data | Mock `get_facturadores()` → sample list, assert response matches |
| Integration | `GET /api/users/facturadores` returns correct JSON | Flask test client, login as admin, assert 200 + facturadores list |
| Integration | Unauthorized access returns 401/403 | Flask test client without admin, assert 302/401 |

## Migration / Rollout

No migration required. El archivo `instance/users.json` no se modifica automáticamente. Los admins deben editar usuarios existentes y asignar rol "facturador". Mientras no haya facturadores, el sistema opera con fallback (constantes actuales).

Rollback: revertir `users_store.py` → `get_opciones()` a constantes → remover endpoint → frontend a constantes originales. Sin pérdida de datos.

## Open Questions

- [ ] ¿Queremos que `GET /api/users/facturadores` exponga nombre completo compuesto (primer_nombre + apellido_1) o los 4 campos separados para que el frontend decida? — Resuelto: ambas (nombre_completo para display, campos sueltos para flexibilidad).
- [ ] En abiertas-urgencias, ¿validar que el responsable calculado coincida con un facturador conocido y mostrar warning? — Se implementa como validación soft (sin bloqueo).
