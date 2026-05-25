# Delta for Admin — Usuarios y Permisos

## ADDED Requirements

### R9: Permiso `odontologia_equipos_basicos` en ALLOWED_PERMISOS

`ALLOWED_PERMISOS` MUST include `odontologia_equipos_basicos` as a valid permiso value alongside the existing ones.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| New permiso accepted | `odontologia_equipos_basicos` in user permisos list | `update_user("u", {"permisos": ["odontologia_equipos_basicos"]})` | accepted — permiso validated against ALLOWED_PERMISOS |
| Legacy `equipos_basicos` still valid | `equipos_basicos` in user permisos list | `update_user("u", {"permisos": ["equipos_basicos"]})` | accepted — `equipos_basicos` remains in ALLOWED_PERMISOS |
| Both simultaneous | both permisos in list | `update_user("u", {"permisos": ["odontologia_equipos_basicos", "equipos_basicos"]})` | accepted — both validated |

## MODIFIED Requirements

### R6: Checkbox Distincto por Permiso

The permisos form MUST have distinct checkboxes for `cruce_facturas` (label: "Cruce de Reportes"), `equipos_basicos` (label: "Ordenado y Facturado"), and `odontologia_equipos_basicos` (label: "Equipos Básicos") in BOTH the create form and the edit modal.
(Previously: `equipos_basicos` had label "Equipos Básicos"; `odontologia_equipos_basicos` did not exist)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Create form | admin on `/auth/usuarios` | views permisos section | `value="cruce_facturas"`, `value="equipos_basicos"`, and `value="odontologia_equipos_basicos"` are distinct checkboxes with labels "Cruce de Reportes", "Ordenado y Facturado", "Equipos Básicos" |
| Edit modal | admin editing user | views edit modal | same distinct checkboxes as create form |

## REMOVED Requirements

None.

---

## Acceptance Criteria (Additions)

The following criteria supplement the existing list:

- [ ] `odontologia_equipos_basicos` added to `ALLOWED_PERMISOS` in `app/constants/base.py`
- [ ] `equipos_basicos` label in templates changed from "Equipos Básicos" to "Ordenado y Facturado"
- [ ] `odontologia_equipos_basicos` checkbox shown in both create form and edit modal with label "Equipos Básicos"
- [ ] `update_user()` validation accepts `odontologia_equipos_basicos` and still accepts `equipos_basicos`
