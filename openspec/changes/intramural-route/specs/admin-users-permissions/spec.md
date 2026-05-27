# Delta for Admin — Usuarios y Permisos

## ADDED Requirements

### R12: Permiso `intramural` en ALLOWED_PERMISOS

`ALLOWED_PERMISOS` MUST include `"intramural"` as a valid permiso value.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| New permiso accepted | user with `intramural` permiso | `update_user("u", {"permisos": ["intramural"]})` | accepted — validates against ALLOWED_PERMISOS |
| Existing permisos unchanged | user with `urgencias` | `update_user(..., permisos includes "urgencias")` | `urgencias` still valid alongside `intramural` |

### R13: Entrada `Intramural` en DASHBOARD_AREAS

`DASHBOARD_AREAS` MUST include an entry with `title: "Intramural"`, `slug: "intramural"`, `permiso: "intramural"`, `href: "/intramural"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Admin sees Intramural | session with `["*"]` | renders dashboard | "Intramural" card visible with link `/intramural` |
| User with permiso sees | session with `["intramural"]` | renders dashboard | "Intramural" card visible |
| User without permiso | session with `["odontologia"]` | renders dashboard | no "Intramural" card visible |

## MODIFIED Requirements

### R6: Checkbox Distincto por Permiso

The permisos form MUST have distinct checkboxes for each permiso value in `ALLOWED_PERMISOS` including `intramural` (label: "Intramural") in BOTH the create form and the edit modal.
(Previously: `intramural` checkbox did not exist)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Create form | admin on `/auth/usuarios` | views permisos section | checkbox with `value="intramural"` and label "Intramural" present alongside existing checkboxes |
| Edit modal | admin editing user | views edit modal | same `intramural` checkbox present |
| Assign Intramural | form submitted with `intramural` checked | POST crear/editar | permiso stored correctly |

## REMOVED Requirements

None.
