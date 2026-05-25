# Specification: Perfiles de Usuarios — Plantillas

---

## 1. user-templates (New Domain)

### Purpose

Proveer plantillas reutilizables de permisos que un admin pueda asignar al crear o editar usuarios. Las plantillas son perfiles predefinidos (sin password, no loguean) almacenados en un archivo JSON separado.

---

### 1.1 Requirements

#### R1: Templates Store — CRUD Operations

`templates_store.py` MUST implement `list_templates()`, `get_template(name)`, `create_template(name, descripcion, permisos)`, `update_template(name, updates)`, and `delete_template(name)`. All operations MUST use `instance/templates.json` with atomic writes (temp file + `os.replace()`).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List templates | file has 3 templates | `list_templates()` | returns list of 3 `{nombre, descripcion, permisos}` dicts |
| Get existing | template "odontologia" exists | `get_template("odontologia")` | returns full template dict |
| Get missing | template does not exist | `get_template("ghost")` | returns `None` |
| Create | new name, valid permisos | `create_template("auditoria", "...", ["control_urgencias", "equipos_basicos"])` | template saved; `list_templates()` includes it |
| Create duplicate | existing name | `create_template("odontologia", "...", [...])` | returns `(False, "La plantilla 'odontologia' ya existe")` |
| Update name | existing template | `update_template("odontologia", {"nombre": "odonto_v2"})` | template renamed; old name no longer valid |
| Update permisos | existing template | `update_template("odontologia", {"permisos": ["odontologia", "equipos_basicos"]})` | permisos updated |
| Delete | existing, non-default template | `delete_template("mi_plantilla")` | template removed from store |
| Delete missing | non-existent name | `delete_template("ghost")` | returns `(False, "Plantilla no encontrada")` |
| Atomic write | any mutation | write to `templates.json.tmp` → `os.replace()` | no file corruption on crash |

#### R2: Default Template Creation on First Run

The system MUST create 3 default templates on first boot (when `templates.json` does not exist), matching the historical DEFAULT_USERS permissions.

| Template Name | Permisos | Descripcion |
|--------------|----------|-------------|
| `odontologia` | `["odontologia"]` | "Solo /odontologia" |
| `urgencias` | `["urgencias", "control_urgencias", "facturas_abiertas"]` | "/urgencias + control urgencias (solo lectura) + facturas abiertas" |
| `auditor` | `["control_urgencias", "control_urgencias:write", "facturas_abiertas", "facturas_abiertas:write", "equipos_basicos"]` | "Control urgencias + facturas abiertas + cruce reportes (con modificación)" |

The 3 default template names MUST be defined as `DEFAULT_TEMPLATES` in `templates_store.py`. Admin MUST NOT be a template — admin is a real account only.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| First boot | `templates.json` missing, `users.json` missing | `_load_templates()` called | 3 default templates created; 4 default users created (admin stays, others preserved) |
| Reboot | `templates.json` exists | `_load_templates()` called | existing templates loaded; no duplicates created |
| Upgrade from v1 | old DEFAULT_USERS in `users.json`, no `templates.json` | first boot after update | `templates.json` created with defaults; existing `users.json` preserved (no overwrite) |

#### R3: GET /api/templates — List Templates for React

The system MUST expose `GET /api/templates` decorated with `@admin_requerido`, returning JSON in the standard response format.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List templates | admin authenticated, 3 templates exist | `GET /api/templates` | `{"status": "success", "data": {"templates": [...]}, "errors": []}` |
| Unauthenticated | no session | `GET /api/templates` | 401 or redirect |
| Non-admin | session without `*` | `GET /api/templates` | 403 |

#### R4: Template Integrity — Default Templates Cannot Be Deleted

The 3 default templates (`odontologia`, `urgencias`, `auditor`) MUST NOT be deletable. They SHALL be deletable only if the admin explicitly removes them (MAY be implemented as a delete guard similar to admin user protection).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Delete default | template "odontologia" is a default | `delete_template("odontologia")` | returns `(False, "No se puede eliminar la plantilla por defecto")` |
| Delete custom | template "mi_perfil" is custom | `delete_template("mi_perfil")` | returns `(True, "Plantilla eliminada")` |

---

### 1.2 Data Schema

#### `instance/templates.json`

```json
[
  {
    "nombre": "odontologia",
    "descripcion": "Solo /odontologia",
    "permisos": ["odontologia"]
  },
  {
    "nombre": "urgencias",
    "descripcion": "/urgencias + control urgencias (solo lectura) + facturas abiertas",
    "permisos": ["urgencias", "control_urgencias", "facturas_abiertas"]
  },
  {
    "nombre": "auditor",
    "descripcion": "Control urgencias + facturas abiertas + cruce reportes (con modificación)",
    "permisos": ["control_urgencias", "control_urgencias:write", "facturas_abiertas", "facturas_abiertas:write", "equipos_basicos"]
  }
]
```

**Schema constraints:**
- `nombre`: string, 3–50 chars, alphanumeric + underscores + hyphens. Unique across templates.
- `descripcion`: string, 0–200 chars. Optional.
- `permisos`: array of strings. Each MUST be in `ALLOWED_PERMISOS` (from `app/constants/base.py`). At least 1 element.

#### `instance/users.json` — No Changes

No new fields in users.json. Templates are separate storage. Existing real accounts `admin`, `odontologia`, `urgencias`, `auditor` remain in `users.json` unchanged.

#### `app/constants/base.py` — ADDED Constant

```python
DEFAULT_TEMPLATES = frozenset({"odontologia", "urgencias", "auditor"})
```

---

### 1.3 Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| `nombre` | MUST be 3–50 chars; regex `^[a-zA-Z0-9_-]+$` | `"Nombre de plantilla inválido: debe tener 3-50 caracteres alfanuméricos"` |
| `nombre` | MUST be unique | `"La plantilla '{name}' ya existe"` |
| `descripcion` | SHOULD be ≤ 200 chars | (silently truncated or rejected) |
| `permisos` | MUST be a non-empty list | `"Debe seleccionar al menos un permiso"` |
| `permisos[]` | Each MUST be in `ALLOWED_PERMISOS` | `"Permiso inválido: {value}"` |
| Delete guard | MUST NOT delete default templates | `"No se puede eliminar la plantilla por defecto '{name}'"` |
| Rename default | SHOULD NOT rename default templates (SHOULD warning) | (soft restriction) |

---

### 1.4 Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| All templates deleted (custom ones) | Only defaults remain. UI dropdown still shows defaults. |
| Template renamed while users have matching permissions | No impact — users store their own permisos list independently. Template is just a pre-fill shortcut. |
| Template edited after users created | Existing users are NOT retroactively updated. Template is only a pre-fill mechanism. |
| File `templates.json` manually corrupted | `_load_templates()` catches `json.JSONDecodeError`, logs error, returns empty list. Admin sees no templates in dropdown. |
| `templates.json` missing on existing system | Creates defaults (same as first boot). Safe — templates are additive. |
| Template with `*` (admin) permisos | Allowed — but presentation SHOULD show "Admin" role trivially. Edge case: template named "admin" conflicts with real user conceptually. |

---

## 2. admin-users-permissions (Delta)

### Purpose

Modified capabilities: user create/edit forms gain a "Basado en plantilla" dropdown that pre-fills permission checkboxes. User list filters out template-based accounts.

---

### 2.1 ADDED Requirements

#### R5: Template Dropdown in Create/Edit Form

The user create form and edit modal MUST include a "Basado en plantilla" `<select>` positioned ABOVE the permisos checkboxes. Selecting a template SHALL pre-fill the checkboxes (overwriting any current selection). The pre-filled values SHALL be editable manually by the admin.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Create form shows dropdown | admin on React Usuarios page, templates exist | opens create modal | dropdown "Basado en plantilla" visible above checkboxes, default "-- Seleccionar --" |
| Select template in create modal | create modal open, no permisos checked | selects "odontologia" from dropdown | checkboxes: only "Odontología" checked |
| Select different template | permissions already partially checked | selects "auditor" from dropdown | checkboxes: replaced with auditor permisos (previous selection cleared) |
| Template then manual edit | permisos pre-filled from template | admin unchecks one and checks another | final POST includes the manually edited set |
| Switch back to "-- Seleccionar --" | template selected, checkboxes filled | selects "-- Seleccionar --" | checkboxes cleared (all unchecked) |
| React vs Jinja2 parity | both UIs open | same template selection | identical checkbox pre-fill behavior |
| Edit modal with template | modal opens, user has existing permisos | template dropdown visible | dropdown "-- Seleccionar --" selected; user's current permisos loaded |

#### R6: Template Dropdown — Admin Role Guard

When rol is "admin" (`"*"` permisos), the template dropdown SHALL be hidden (or disabled). Admin has all permissions by definition — no template needed.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Rol switched to admin | dropdown visible, template selected | selects "Admin" in rol dropdown | permisos section + template dropdown hidden |
| Rol switched back to usuario | hidden template dropdown | selects "Usuario" | template dropdown shown again; permisos checkboxes shown |

#### R7: User List — Filter Out Templates

`users_store.list_users()` MUST return ONLY real user accounts. Template entries from `templates.json` SHALL NOT appear in the user list.

This is achieved by keeping templates in a separate store (`templates.json`) — `list_users()` only reads `users.json`. No filtering logic needed.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List users | `users.json` has 4 users, `templates.json` has 3 templates | `list_users()` | returns 4 users; templates not in result |
| Template with same name as user | "odontologia" exists in both stores | `list_users()` | returns the real user "odontologia" (from users.json); template not included |

#### R8: Migration — DEFAULT_USERS Split

`_create_default_users()` in `users_store.py` SHALL create ONLY the admin user in `users.json` and let `templates_store._load_templates()` create the 3 templates.

For EXISTING installs where `users.json` already has all 4 users: the system SHALL create `templates.json` on first boot without modifying the existing `users.json`. This preserves active sessions.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Clean install | no `users.json`, no `templates.json` | first `_load_users()` | `users.json`: admin only (3 real accounts preserved). `templates.json`: 3 defaults |
| Upgrade (users.json exists) | `users.json` has 4 real users, no `templates.json` | first `_load_templates()` | `templates.json` created with 3 defaults. `users.json` untouched. All 4 users log in as before |
| Upgrade (both exist) | both files exist from previous run | boot | nothing changes — additive migration |

---

### 2.2 MODIFIED Requirements

#### R9: React UI — Create Form (previously R0 in existing spec — Create User)

(Previously: React create form was a simple inline form with username/password/rol/permisos. Now gains template dropdown before permisos.)

The React create form MUST include a "Basado en plantilla" dropdown positioned between the rol selector and the permisos checkboxes.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Create user with template | admin, 3 templates exist | selects "urgencias", fills username+password, submits | user created with permisos = ["urgencias", "control_urgencias", "facturas_abiertas"] |
| Create user without template | admin, any state | leaves dropdown on "-- Seleccionar --", manually checks permisos, submits | user created with manual permisos only |

---

### 2.3 UI Specification

#### React Modal — Dropdown Position

```
┌──────────────────────────────────┐
│  Crear Usuario / Editar Usuario   │
├──────────────────────────────────┤
│  [Usuario input]                  │
│  [Contraseña input]               │
│  [Rol select]                     │
│                                    │
│  ── Template section ──           │
│  Basado en plantilla: [select ▼]  │  ← NEW
│  ─────────────────────────        │
│                                    │
│  Permisos:                        │
│  ☐ Odontología                    │
│  ☐ Urgencias                      │
│  ☐ Control de Urgencias (lectura) │
│  ...                              │
│                                    │
│  [Crear] [Cancelar]               │
└──────────────────────────────────┘
```

**Dropdown behavior:**
- Default value: `""` (empty, shows "-- Seleccionar --")
- Options: "odontologia", "urgencias", "auditor" + any custom templates
- `onChange`: clears current `formPermisos`, replaces with template's `permisos`
- No API call needed on selection — templates loaded once at page init via `GET /api/templates`

#### Jinja2 HTML — Dropdown Position

Same position: between rol select and the permisos fieldset. JavaScript `onchange` handler for checkbox pre-fill.

#### initial_data for React Shell

The `/auth/usuarios` route MUST include `templates` in `initial_data`:

```python
initial_data={
    "username": session.get("username", ""),
    "permisos": permisos,
    "usuarios": usuarios,
    "templates": templates_store.list_templates(),
    "session_username": session.get("username", ""),
}
```

---

### 2.4 Validation Rules (Templates in User Context)

| Rule | Behavior |
|------|----------|
| Template selection + manual edit | Manual changes override template pre-fill. Template is a convenience, NOT a binding. |
| Template deleted after user created | User's permisos are unaffected (stored in users.json independently) |
| Creating user with empty template | `create_user()` requires at least 1 permiso for non-admin — template or manual. |
| Edit modal: changing template | Selecting a template in edit mode OVERWRITES existing permisos. Confirmation SHOULD warn. |

---

## 3. Non-Goals

| Not Covered | Why |
|-------------|-----|
| Permission inheritance (template inherits from another template) | Out of scope per proposal. Templates are flat lists. |
| Ghost permisos cleanup (`cruce_facturas`, `derechos`) | Separate change — no modification to ALLOWED_PERMISOS here |
| Database migration (SQLite/Postgres) | Plan is to stay with JSON files for now |
| New permission values or roles | Only organizing existing permissions into templates |
| Retroactive template update (changing template updates all users who used it) | Templates are pre-fill shortcuts only; users own their permisos list |
| Audit log (who created which user from which template) | Out of scope; may be added later |
| RBAC / role hierarchy | Templates are not roles; they are pre-fill profiles |
| Template assignment tracking (which users were created from a template) | No schema for this — templates are ephemeral pre-fill tools |

---

## 4. Edge Cases Summary

| # | Edge Case | Resolution |
|---|-----------|------------|
| EC1 | Template renamed after creation | No impact on existing users. Old template name still present in users' permisos if that permiso string existed. |
| EC2 | All custom templates deleted | Defaults remain. Dropdown shows defaults only. |
| EC3 | Admin creates template named "admin" | Name conflict with real admin user conceptually, but different stores. Allowed. |
| EC4 | User with same username as template e.g. "odontologia" | Real account in `users.json`, template in `templates.json`. `list_users()` shows real account only. No conflict. |
| EC5 | Template with `"*"` permisos | Allowed but unusual. Admin creating a user with this template: rol should auto-switch to admin. |
| EC6 | Edit modal: template dropdown pre-selected | In edit mode, dropdown stays on "-- Seleccionar --". No template auto-detection from user's current permisos (would be fragile — user's permisos may have drifted from template). |
| EC7 | `templates.json` file deleted manually at runtime | Next `_load_templates()` regenerates defaults. Real users unaffected. Any in-flight UI state loses unsaved changes. |
