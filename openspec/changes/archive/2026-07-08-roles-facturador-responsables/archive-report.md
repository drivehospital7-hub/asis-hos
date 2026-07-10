# Archive Report: roles-facturador-responsables

## Change Archived

**Change**: roles-facturador-responsables
**Archived to**: `openspec/changes/archive/2026-07-08-roles-facturador-responsables/`
**Archived on**: 2026-07-08

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| admin-users-permissions | Updated | R1 expanded to 4 roles, 3 new scenarios added, validation rule updated, acceptance criteria updated, R12 added for React role select |
| facturadores-dynamic-responsables | Created | New main spec (5 requirements, 4 constraints) — was a full spec (not delta) |

## Archive Contents

- exploration.md ✅
- proposal.md ✅
- specs/admin-users-permissions/spec.md ✅
- specs/facturadores-dynamic-responsables/spec.md ✅
- design.md ✅
- tasks.md ✅ (9/9 tasks complete)
- apply-progress.md ✅
- verify-report.md ✅ (PASS WITH WARNINGS — 3 non-blocking warnings)
- archive-report.md ✅

## Source of Truth Updated

The following specs now reflect the new behavior:

- `openspec/specs/admin-users-permissions/spec.md` — Rol validation expanded to 4 roles (admin, usuario, medico, facturador); React role select requirement added as R12
- `openspec/specs/facturadores-dynamic-responsables/spec.md` — New spec for dynamic responsables from facturadores via API

## Merge Details

### admin-users-permissions

- **R1**: Title updated to "Actualización Parcial y Validación de Rol Expandida". Added `rol` validation statement for 4 roles. Added 3 new scenarios (Update to medico, Update to facturador, Invalid rol).
- **Validation Rules**: Rol field updated to accept 4 values with new error message.
- **Acceptance Criteria**: Updatd existing criteria to show 4 roles. Added 4 new criteria (accepts medico/facturador, rejects unknown, create_user accepts, React dropdown shows 4).
- **Template Specs**: Edit modal `<select>` updated with 4 options (Usuario, Admin, Médico, Facturador).
- **R12 (new)**: React usuarios page role select requirement with 2 scenarios.

### facturadores-dynamic-responsables

- Copied as-is from delta spec (no existing main spec). Contains R1-R5 covering store query, API endpoint, service layer, fallback, and frontend consumption.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. Ready for the next change.

## Key Verification Results

- **Tests**: 66/66 passed
- **Verdict**: PASS WITH WARNINGS (3 warnings: missing integration tests, unused facturadores state in React, duplicated nombres_completos computation)
- **No critical issues** found
