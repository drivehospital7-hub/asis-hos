## Exploration: roles-facturador-responsables

### Current State

#### 1. User/Role Management (`app/utils/users_store.py`)
- Users stored in `instance/users.json` (JSON file, **NOT** SQLAlchemy). The `User` model in `app/models.py` exists but auth/sessions use the JSON store exclusively.
- Roles stored as a string field `rol` → currently only `"admin"` or `"usuario"`.
- Rol validation is strict: `update_user()` checks `if rol not in ("admin", "usuario")`.
- Default users: admin (rol=admin), odontologia (rol=usuario), urgencias (rol=usuario), auditor (rol=usuario).
- User CRUD via `app/routes/auth.py` — creates/edits/deletes via the JSON store.
- React UI at `frontend/src/pages/usuarios/page.tsx` — dropdown has only "Usuario" / "Admin" options.
- **No concept of "medico" or "facturador" roles exists yet.**

#### 2. Control-errores (Control de Novedades)
- **Jinja2 template** at `app/templates/control_errores.html` (semi-SPA with inline JS).
- Route: `GET /control-errores` → `app/routes/control_errores.py` → renders `control_errores.html`.
- **Responsables are HARDCODED** in `app/constants/urgencias.py`:
  ```python
  ERROR_RESPONSABLE_URGENCIAS = [
      "ALEJANDRA ESPAÑA", "CARLOS OMAR", "DANIELA PAEZ", "MARINEY DIAZ",
  ]
  ```
  With companion maps: `RESPONSABLE_NOMBRES_COMPLETOS` and `CRONOGRAMA_NOMBRE_MAP`.
- These constants are served via `GET /api/control-errores/opciones` → `control_errores_service.get_opciones()`.
- The `responsable` field in error records is a **free-text string**, not a foreign key to any user table.
- **Carga Masiva** modal (embedded in the same template) uses these same hardcoded lists to match pasted names via `_matchResponsable()`.
- **React prototype** at `frontend/src/pages/control-novedades/` exists but is NOT connected to any route.

#### 3. Abiertas-urgencias (`frontend/src/pages/abiertas-urgencias/`)
- React page served at `/abiertas-urgencias` (via `react_shell.html`).
- Uses its own **separate** hardcoded name maps in `frontend/src/pages/abiertas-urgencias/constants.ts`:
  ```typescript
  export const NOMBRE_MAP: Record<string, string> = {
    CARLOS: "CARLOS OMAR",
    ALEJANDRA: "ALEJANDRA ESPAÑA",
    YULIETH: "DANIELA PAEZ",
    MARINEY: "MARINEY DIAZ",
  };
  ```
- The `handleSendToControl()` function posts directly to `/api/control-errores` with a `responsable` string.
- Utils (`calcularResponsable`, `masDeDosTurnosMismoResponsable`) use the schedule to determine which responsable is assigned.
- The responsables reported here come from **processed Excel data**, not from a user registry.

#### 4. Key Architectural Fact
**There is NO link between "Users" and "Responsables" today.** The responsables are hardcoded strings shared across three places:
- `app/constants/urgencias.py` (Python, backend)
- `frontend/src/pages/abiertas-urgencias/constants.ts` (TypeScript, frontend)
- Inline in `app/templates/control_errores.html` JS (accessed via API)

---

### Affected Areas

| File | Why Affected |
|------|-------------|
| `app/constants/urgencias.py` | `ERROR_RESPONSABLE_URGENCIAS`, `RESPONSABLE_NOMBRES_COMPLETOS`, `CRONOGRAMA_NOMBRE_MAP` — need dynamic generation from users |
| `app/services/control_errores_service.py` | `get_opciones()` needs to fetch users with facturador role instead of constants |
| `app/routes/control_errores.py` | No change needed if service layer handles it |
| `app/templates/control_errores.html` | Carga Masiva JS (`_matchResponsable`, `parseCargaMasiva`) uses `opciones.responsables` — will auto-adapt from API |
| `app/utils/users_store.py` | Needs new role values "medico" and "facturador" added + validation updated |
| `app/routes/auth.py` | User creation/editing forms need the new roles in the dropdown |
| `frontend/src/pages/usuarios/page.tsx` | Rol dropdown needs "Médico" and "Facturador" options |
| `frontend/src/pages/abiertas-urgencias/constants.ts` | `NOMBRE_MAP` should come from backend instead of being hardcoded |
| `frontend/src/pages/abiertas-urgencias/utils.ts` | `REVERSE_NOMBRE_MAP` and `getUniqueResponsables` — may need to reference backend users |
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Responsable assignment should validate against facturadores list |
| `app/models.py` | `User.rol` column default comment mentions only "admin o usuario" |
| `app/constants/base.py` | `ALLOWED_PERMISOS` might need updating if new permissions are needed |
| `app/data/control_errores.json` | Existing error records with old responsable strings — migration strategy needed |
| `tests/utils/test_users_store.py` | Tests hardcode rol validation — need to add "medico" and "facturador" |
| `tests/services/test_control_errores_service.py` | May need updates if responsable logic changes |

---

### Approaches

#### 1. Minimal — Add roles + filter by rol via API
- Add "medico" and "facturador" to users_store role validation.
- Add an API endpoint: `GET /api/users/facturadores` or similar that returns users with `rol == "facturador"`.
- Modify `control_errores_service.get_opciones()` to call users_store instead of constants.
- Replace constants in abiertas-urgencias with API calls.
- **Pros**: Fast, backwards-compatible, no schema changes.
- **Cons**: Existing error records keep old responsable strings; free-text field means no referential integrity.
- **Effort**: Low-Medium

#### 2. Full — Replace constants with dynamic backend queries
- Everything in Approach 1, plus:
  - Create a `responsables_store` or extend users_store to map users with facturador role.
  - Add a new API endpoint `/api/responsables` that returns the same format as current constants.
  - Remove hardcoded constants from both Python and TypeScript.
  - Normalize existing `control_errores.json` responsable strings.
- **Pros**: Single source of truth, no duplication.
- **Cons**: More moving parts, data migration needed.
- **Effort**: Medium

#### 3. Hybrid — Backend-driven with fallback
- Add roles to users_store.
- Create a new service function `get_facturadores()` that queries users_store for `rol == "facturador"`.
- If no facturadores exist, fall back to the hardcoded constants (graceful degradation).
- Update `control_errores_service.get_opciones()` to use the new function.
- Add `GET /api/facturadores` route.
- Update abiertas-urgencias React to fetch from `/api/facturadores`.
- **Pros**: No breaking changes, backward-compatible, safe rollout.
- **Cons**: Slightly more complex due to fallback logic.
- **Effort**: Medium

---

### Recommendation

**Approach 1 (Minimal)** is the right starting point because:
1. The user asked specifically to add roles and have the responsables list match users with "facturador" role.
2. The current responsables are just 4 hardcoded names — a simple API endpoint replacing the constants solves the duplication immediately.
3. It avoids the complexity of data migration for existing `control_errores.json` records where responsable is a free-text field.
4. The existing flow (Carga Masiva, abiertas-urgencias send-to-control) all work through the same `opciones` API endpoint — changing the backend source auto-propagates.

**Recommended implementation order:**
1. Add "medico" and "facturador" to users_store role validation + default constants.
2. Add `GET /api/users/facturadores` endpoint.
3. Modify `control_errores_service.get_opciones()` to query facturadores from users_store.
4. Fallback to hardcoded constants if no facturadores exist (safe migration).
5. Update React usuarios page with new role options.
6. Update abiertas-urgencias to use the API for responsable data.

---

### Risks

1. **Existing data mismatch**: Current `control_errores.json` has responsable strings that may not match any user. The filter will work forward for new records but existing ones may have stale names.
2. **Name normalization**: The Carga Masiva matching logic (`_matchResponsable`) expects names to match the constant list. If facturador names come from users with different formatting, matching could break.
3. **Frontend hardcoding**: `abiertas-urgencias/constants.ts` has `NOMBRE_MAP` hardcoded. The `calcularResponsable()` function uses it to resolve short names from the schedule. This needs to be fetched from the backend adaptively or kept as a separate concern (schedule names vs user names).
4. **No proper role migration**: Existing users don't have "medico" or "facturador" roles. Admin must manually update them via the UI.
5. **Role vs Permissions confusion**: Currently roles (`rol`) are a single string, while permissions (`permisos`) are a list of module access rights. The "facturador" role is about user category, not module permissions — make sure they're treated as orthogonal concepts.

### Ready for Proposal
**Yes** — the exploration is complete and actionable. The user should be informed that:
- Roles "medico" and "facturador" will be added to the users store
- The responsables list in control-errores will dynamically reflect users with facturador role
- Carga Masiva and abiertas-urgencias will auto-adapt via the same API
- Existing data will be preserved but not retroactively migrated
