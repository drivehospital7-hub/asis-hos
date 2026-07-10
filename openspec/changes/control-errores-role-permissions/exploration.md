## Exploration: control-errores-role-permissions

### Current State

**Permission model (WHAT exists today):**

The system uses a **flat permission list** (`session["permisos"]`) — NOT role-based access control. Every user has a list of string permissions (e.g., `["control_urgencias"]`, `["control_urgencias:write"]`, `["*"]`). There are two tiers:

1. **Full write**: user has `*` or `control_urgencias:write` in permisos → can edit ALL fields on any record
2. **Partial write**: user has `control_urgencias` only → can ONLY edit `estado` and `observacion_facturador` on PUT; all other fields (tipo_error, factura, observacion, responsable) return 403
3. **No control_urgencias perm at all**: 403 on everything

**Who has what (from `users.json` defaults):**

| User | Role | Permisos | Write access? |
|------|------|----------|---------------|
| admin | admin | `*` | Full |
| urgencias | usuario | `control_urgencias`, ... | Partial |
| auditor | usuario | `control_urgencias:write`, ... | Full |

**Role exists in session but is NEVER used for decision-making** in control-errores routes or services. `session.get("rol")` is never read in any control_errores code. Roles are: `admin`, `usuario`, `medico`, `facturador` — but they're purely informational today.

**How frontend guards work (`control_errores.html`):**

```javascript
window._canWrite = {{ 'true' if '*' in session.get('permisos', []) or 'control_urgencias:write' in session.get('permisos', []) else 'false' }};
```

This boolean gates:
- `addNewRow()` → disabled
- `deleteError()` → disabled
- `exportToCSV()` → disabled
- `openCargaMasiva()` → disabled
- Image upload/delete → disabled
- `openEditor()` for fields other than `estado` and `observacion_facturador` → disabled

**Record structure (JSON storage):**

```python
{
    "id": "uuid",
    "tipo_error": str,
    "factura": str,
    "observacion": str,
    "observacion_facturador": str,
    "estado": str,          # "S" (pendiente) or "N" (resuelto)
    "responsable": str,     # nombre_completo of ASSIGNED person
    "validador": str,       # display name of CREATOR (primer_nombre + apellido_1)
    "creado_en": str,       # ISO datetime
    "actualizado_en": str,  # ISO datetime
}
```

**CRITICAL MISSING DATA**: There is NO `created_by_username` or `created_by_rol` in the record. The `validador` field stores only a display name (e.g., "Juan Pérez"), not a system identifier. This makes it IMPOSSIBLE today to:
- Know which username created a record (for "facturador can't edit records created by write users")
- Know the creator's role at creation time
- Reliably look up the creator's current permisos (name collisions possible)

**Who sees what (current behavior):**

Every user with `control_urgencias` sees ALL records unfiltered. Filters exist for tipo, estado, responsable, rol — but they're optional and user-applied. Nothing is filtered server-side by role.

**Affected code paths:**

| Layer | File | Role today |
|-------|------|------------|
| Route decorator | `app/routes/control_errores.py` | `@permiso_requerido("control_urgencias", "control_urgencias:write")` — flat check |
| Service: get_errores() | `app/services/control_errores_service.py` | Returns ALL records; enriches with `responsable_rol`; filter by rol only if query param |
| Service: update_error() | same file | Field-level check: full write if `*` or `:write`, else only estado/obs_facturador |
| Service: add_error() | same file | Always allowed (route decorator already requires `:write`) |
| Service: delete_error() | same file | Always allowed (route decorator already requires `:write`) |
| Storage | `app/utils/errores_storage.py` | No filtering, no permission awareness |
| Auth decorator | `app/utils/auth.py` | `permiso_requerido()` — flat check, no role awareness |
| Frontend | `app/templates/control_errores.html` | `window._canWrite` boolean; no role-based rendering |
| Users store | `app/utils/users_store.py` | `get_facturadores()` filters by role; `get_user()` by username |

---

### Affected Areas

- `app/services/control_errores_service.py` — **IN FOCUS**: get_errores() needs role-based filtering; update_error() needs record-level ownership checks; add_error() needs creator tracking
- `app/utils/errores_storage.py` — Needs `created_by` (username) field added to record schema; new filter-by-creator-role logic
- `app/routes/control_errores.py` — Route decorators may need role-aware versions; new endpoints for "my records" if separate route approach
- `app/templates/control_errores.html` — `window._canWrite` → role-aware equivalents; conditional form fields; "create for medico" dropdown
- `app/constants/base.py` — Possible new permission constants for role-scoped operations
- `app/utils/auth.py` — Possible new decorators (e.g., `roles_requerido`)
- `tests/services/test_control_errores_service.py` — New test classes for role-based access
- `tests/services/test_control_errores_integration.py` — New integration tests for role-scoped API behavior

---

### Approaches

#### Approach 1: Permission-aware enrichment (same page, backend-enforced)

Keep the existing single page `/control-errores`. Add role-based logic in the service layer:

- **Backend**: `get_errores()` checks `session["rol"]` and `session["username"]`:
  - `medico`: filter records where `responsable` matches session user's name, OR where the assigned person's role is "medico"
  - `facturador`: return all records, but `update_error()` checks record ownership — facturador can edit records assigned to "medico" or themselves; CANNOT edit records where `validador_username` corresponds to a user with `:write` perm
  - `admin` / users with `*`: full access (unchanged)
  - Users with `control_urgencias:write`: full access (unchanged)
- **Frontend**: `window._canWrite` becomes richer — `window._userRole`, `window._currentUserName`, plus per-record permissions from the API response
- **Data change**: Add `created_by` (username) to error records

| Pros | Cons | Effort |
|------|------|--------|
| Single URL, minimal UI changes | Complex backend permission logic | High |
| Consistent UX for all users | Record-level checks in update_error get complex | |
| Leverages existing polling/filter pattern | Need to store username alongside validador | |
| All user types coexist on same data set | Per-record perm flags in API response needed | |

#### Approach 2: Multi-tab with same template

Keep the same template and URL but add role-filtered tabs (like month tabs exist today):

- Add tabs: "Todas", "Mis Novedades" (for facturador), "Asignadas a Médicos" (for facturador)
- Each tab calls same `/api/control-errores` with different filter params
- Backend applies semantic filters based on role + username
- Separate "create" flow for facturador → can select "create for medico" from dropdown

| Pros | Cons | Effort |
|------|------|--------|
| Familiar UX pattern (tabs already exist) | Might confuse users with too many tabs | Medium |
| Same API endpoints with filter params | Tab logic in JS adds complexity | |
| No new routes needed | Need to decide if tabs are persistent based on role | |

#### Approach 3: New mini-module at separate route

Create a sub-route like `/control-errores/medicos` or a filter query param:

- `/control-errores?mode=medico` renders same template with different default filters
- Or add a Flask blueprint sub-route `/control-errores/revision` for medico-specific view
- Different `window._canWrite` logic per route
- Same service layer, different entry points

| Pros | Cons | Effort |
|------|------|--------|
| Clean URL separation | Duplicate route definitions | High |
| Each route has simple permission model | Navigation confusion — how do users switch? | |
| Easy to test independently | Template sharing vs duplication decision | |

#### Approach 4: Hybrid — same page + backend-enforced + new create modal

**RECOMMENDED**: Keep the main listing as-is but change behavior based on role. The key insight: the page already shows ALL records (with filters). Role-based access should be transparent:

- **View**: All users see all records (or filtered server-side for medicos). The page looks the same.
- **Edit**: Backend enforces who can edit what. Facturadores see edit controls for medicos' records + their own. Medicos only see estado/obs_facturador (current limited behavior).
- **Create**: A NEW sub-section or modal for facturadores to "crear novedad para médico" — dropdown lists only users with rol "medico".
- **Data**: Add `created_by` (username) and optionally `created_by_rol` to each record.
- **Backend permission matrix**:

  | Action | Admin (`*`) | Write user (`:write`) | Facturador (rol facturador) | Medico (rol medico) | Read user (`control_urgencias`) |
  |--------|-------------|----------------------|----------------------------|-------------------|-------------------------------|
  | View record | All | All | All | Only assigned to medico | All (current) |
  | Edit any field | ✅ | ✅ | Only own + medicos' | ❌ | ❌ |
  | Edit estado/obs_fact | ✅ | ✅ | ✅ | ✅ (current) | ✅ (current) |
  | Create new | ✅ | ✅ | ✅ (for medico only) | ❌ | ❌ |
  | Delete | ✅ | ✅ | ❌ | ❌ | ❌ |
  | Export | ✅ | ✅ | ✅ | ❌ | ✅ (current) |

| Pros | Cons | Effort |
|------|------|--------|
| Most natural UX — role impacts capability not layout | Need new permission decorator or richer checks | Medium-High |
| Same URL, same template | Data migration for existing records (add created_by) | |
| Clean separation of concerns | Per-record permission flags needed in API | |
| Backend is the single source of truth | | |

---

### Recommendation

**Approach 4 — Hybrid same-page with backend-enforced permissions**, with these specifics:

1. **Same page, same URL**. One template, one set of routes. The page adapts based on `session["rol"]` + `session["permisos"]`.

2. **Extend `window._canWrite` to `window._userRole`**. Pass both role and permisos to the frontend. Keep `window._canWrite` as-is (it maps to permisos) but add role-aware rendering.

3. **Add `created_by` (username) to error records**. This is the minimal data change needed. Look it up at creation time from `session["username"]`. Existing records without `created_by` get `"-"` fallback (like validador).

4. **Record-level permission in `update_error()`**:
   - If user has `*` or `:write` → full access (current behavior, unchanged)
   - If user's rol is `facturador`:
     - Can edit records where `responsable_rol == "MEDICO"` (assigned to a medico)
     - Can edit records where `validador_username == session["username"]` (own records)
     - CANNOT edit records where the creator has `:write` perm (look up via users_store)
   - If user's rol is `medico`:
     - Only see records assigned to them (`responsable == currentUserName`)
     - Only can edit `estado` and `observacion_facturador` (current partial behavior)
   - Everyone else: current behavior unchanged

5. **New create UI for facturadores**: When role is `facturador`, the "Agregar Novedad" button opens a form where one field selects the medico (dropdown from `list_users()` filtered to role `medico`). The `responsable` field auto-populates to the selected medico's name.

6. **Permission decorator flexibility**: Keep the current `permiso_requerido("control_urgencias", "control_urgencias:write")` — it still works correctly because we're adding role-aware checks INSIDE the service, not at the route level.

### Questions to resolve before proposal

| # | Question | Why it matters |
|---|----------|----------------|
| Q1 | What does "medicos only see their own" mean? By `responsable` field? By `validador_username`? Or by role of the assigned person? | Determines filter logic in `get_errores()` |
| Q2 | Should "facturador can't edit records created by write users" be enforced at the record level or should we prevent the UI from allowing it? | Both — backend MUST enforce, frontend is UX convenience |
| Q3 | Are the "medicos" in the dropdown only those with rol "medico", or any user that can be assigned as responsible? | Determines the dropdown source |
| Q4 | Can a facturador CREATE a record for themselves? Or only for medicos? | Affects the create form flow |
| Q5 | Should existing records (before this change) be editable by facturadores? They have no `created_by` so we can't determine ownership. | Migration strategy for ~400 existing records |
| Q6 | Is the `responsable` dropdown today limited to `facturador + medico` roles. Should it now also include `usuario`? | Affects `_build_user_data()` filter |

### Risks

- **Data migration**: ~400 existing records lack `created_by`. Decision needed: mark them as "admin-created" (full editability) or "unknown" (read-only for facturadores). The latter is safer but may block operations.
- **Name collision**: Looking up users by `nombre_completo` is fragile (two users could have same first name + last name). Adding `created_by` (username) is essential.
- **Race condition**: If a facturador opens edit UI for a record and in the meantime an admin changes the record's `responsable`, the edit might succeed on a now-forbidden record. Mitigate by re-checking permissions inside `update_error()` in the same transaction.
- **Frontend complexity**: `updateDisabledState()` is already 80+ lines. Role-aware rendering will make it significantly more complex. Consider extracting to a dedicated JS function or using data attributes.
- **Polling + permission changes**: If a user's role changes mid-session, they'd need to refresh to get new permissions. Acceptable for now — Flask session changes require re-login anyway.

### Ready for Proposal

**Yes**, with caveats. The exploration reveals:

1. The permission model is well-understood
2. The key data gap (`created_by`) is identified with a clear fix
3. Four approaches are documented with tradeoffs
4. The recommended approach (hybrid same-page) is viable

**However**, the orchestrator MUST resolve the 6 open questions (Q1-Q6) with the user before the proposal phase. These fundamentally shape the permission matrix and data model. Without them, any proposal would make assumptions that could invalidate the design.
