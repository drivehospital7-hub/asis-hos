# Vincular Procedimientos a EPS

## Purpose

Completar la cadena EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento desde `/catalogo`. Crear NotaHoja, vincular procedimientos CUPS a EPS con tarifa, exponer `id_nota_hoja` en cadena.

---

## Requirements

### R1: Tab "Notas Hoja" — CRUD (SQLite)

The `/catalogo` MUST have a 4th tab "Notas Hoja" with CRUD on table `NotaHoja` (single field: `nota`).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List | tab selected | renders | table of all `id` + `nota` rows |
| Create | valid non-empty `nota` | POST | row persisted; tab refreshed |
| Edit | existing row | updates `nota` | row updated |
| Delete | existing row | deletes | row removed |
| Empty nota | `nota=""` | create/edit | rejected "La nota no puede estar vacía" |
| FK constraint | NotaHoja referenced by EpsNota | delete | blocked with error |

### R2: `POST /api/eps/<id>/vincular-procedimiento`

MUST accept `{ id_nota_hoja, id_procedimiento, tarifa }`. Atomic transaction: (1) create EpsNota, (2) create NotasTecnicas. MUST rollback on any failure.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Happy path | valid EPS, NotaHoja, Procedimiento, tarifa>0 | POST | 201; both rows created; same `id_nota_hoja` link |
| Duplicate | `(id_nota_hoja, id_eps_contratado)` exists | POST | 400; no insert |
| Missing field | any field absent/null | POST | 400 |
| Bad tarifa | non-numeric or ≤0 | POST | 400 |
| EPS not found | `<id>` not in EpsContratado | POST | 404 |
| Atomicity | second insert fails | first succeeded | full rollback; no orphan rows |

### R3: "Ver Procedimientos" — Formulario Vincular

Modal MUST include: NotaHoja dropdown, Procedimiento dropdown, tarifa input, "Vincular" button.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Form renders | modal opens | view | both dropdowns populated; button enabled |
| Submit valid | all filled, tarifa>0 | click Vincular | POST succeeds; toast success; table refreshes |
| Empty form | no selections | submit | validation blocks; inline error |
| Missing tarifa | dropdowns set, tarifa blank | submit | blocks; "Ingrese una tarifa válida" |
| Duplicate | server 400 | submit rejected | error toast |
| Network error | server unreachable | submit | error toast; form intact |

### R4: `id_nota_hoja` en Chain Response

`GET /api/eps/<id>/procedimientos` MUST include `id_nota_hoja` per procedimiento.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Linked | procedimiento has NotasTecnicas | GET | `id_nota_hoja` (integer) present |
| Unlinked | no NotasTecnicas | GET | `id_nota_hoja` is `null` |
| Back compat | existing clients | GET | all prior fields preserved |

---

## Validation Rules

| Field | Rule | Error |
|-------|------|-------|
| `id_nota_hoja` | MUST reference existing NotaHoja | "NotaHoja no encontrada" |
| `id_procedimiento` | MUST reference existing Procedimiento | "Procedimiento no encontrado" |
| `tarifa` | MUST be numeric, > 0 | "Tarifa inválida" |
| `(id_nota_hoja, id_eps_contratado)` | MUST be unique in EpsNota | "Combinación ya existe" |

---

## Non-Functional

- **Atomicity**: Compound endpoint SHALL use a SQLite transaction; any failure → full rollback.
- **Frontend validation**: Form SHALL validate locally (required, tarifa>0) before calling API.
- **TDD strict**: Backend tests SHALL be written before implementation code.
