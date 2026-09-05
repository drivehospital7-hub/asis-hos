# Archive Report — Unified Permission Model

**Change**: En permisos usuarios siento que se quedó un poco como estaba antes, ahora las rutas apuntan a un solo que es /procesar donde se unifican hechale un revisada y acomoda los checks de permisos, lo mismo con los cronogramas
**Archived**: 2026-06-16
**Status**: All 21 tasks completed — 855 tests passing, frontend build clean

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| admin-users-permissions | Updated | R6 extended (checkbox replacement table + 3 new scenarios); R12–R16 already present |
| odontologia-equipos-basicos | Deprecation notice added | Superseded by `openspec/specs/procesar/spec.md` — spec retained for historical reference |
| procesar | Created at full spec path | New unified processing specification |
| cronogramas | Created at full spec path | Granular cronograma permissions specification |

## Source of Truth Updated

- `openspec/specs/admin-users-permissions/spec.md` — R6 extended with checkbox replacement details
- `openspec/specs/odontologia-equipos-basicos/spec.md` — deprecation notice added (already present before archive)
- `openspec/specs/procesar/spec.md` — new spec (already created at full path)
- `openspec/specs/cronogramas/spec.md` — new spec (already created at full path)

## Archive Contents

- proposal.md ✅ (recreated after Move-Item truncation)
- exploration.md ✅ (recreated)
- design.md ✅ (recreated)
- tasks.md ✅ (21/21 tasks complete)
- specs/admin-users-permissions/spec.md ✅ (delta spec)
- specs/odontologia-equipos-basicos/spec.md ✅ (deprecation delta)

## Verification

- [x] Main specs updated correctly
- [x] Change folder moved to archive (`openspec/changes/archive/2026-06-16-.../`)
- [x] Archive contains all artifacts
- [x] Active changes directory no longer has this change

## Notes

- The original change folder name exceeded Windows MAX_PATH (255 chars), causing the folder name to be stored as two parts on disk. The Move-Item operation during archiving split the folder — files were recovered and recreated from known content.
- 855 tests pass with no CRITICAL issues.
