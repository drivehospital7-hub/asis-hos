# Archive Report: reglas-multi-dominio

**Change**: Reglas multi-dominio (explicit domain list + `'transversal'` wildcard)
**Archived**: 2026-09-24
**Verdict**: PASS

## Summary

Rules now support an explicit list of dominios via the `regla_dominios`
bridge table (migration 023, additive + backfilled, legacy column kept as a
write-through mirror). Engine resolution funnels through one shared EXISTS
helper across the 4 former OR-transversal sites with exact-first ordering
preserved. CRUD validates against centralized `REGLA_DOMINIOS_VALIDOS`;
admin-reglas edits scope via checkboxes with stacked badges and ∈ filters.
Evidence format untouched. Delivered as 2 independent slices (backend,
frontend) under `auto-chain`; no commits per user safety rule.

## Files changed (implementation, uncommitted on feat/reglas-multi-dominio)

| File | Action |
|---|---|
| `migrations/023_regla_dominios.sql` | NEW (bridge + index + guarded backfill) |
| `migrations/023_regla_dominios_rollback.sql` | NEW (`DROP TABLE` only) |
| `app/models.py` | MODIFIED (`ReglaDominio`, relationship, `to_dict.dominios`) |
| `app/constants/base.py` | MODIFIED (`REGLA_DOMINIOS_VALIDOS`) |
| `app/services/reglas/rule_service.py` | MODIFIED (validation, mirror, scope copy, ∈ listing) |
| `app/services/engine/rule_resolver.py` | MODIFIED (shared helper) |
| `app/services/engine/domain_detection.py` | MODIFIED (shared helper) |
| `app/services/engine/engine.py` | MODIFIED (EXISTS + exact-first + fallback) |
| `app/routes/reglas_api.py` | UNCHANGED (passthrough + 400 envelope covered it) |
| `frontend/src/lib/api-reglas.ts` | MODIFIED (`dominios` types + normalization) |
| `frontend/src/pages/admin-reglas/page.tsx` | MODIFIED (editor, badges, filters) |
| `frontend/src/pages/admin-reglas/page.test.tsx` | NEW (14 cases) |
| `tests/reglas/test_regla_dominios.py` | NEW (20 tests) |
| `tests/engine/test_multi_dominio_resolution.py` | NEW (11 tests) |
| `app/static/react-dist` | REBUILT (generated) |

## Delta composition

- `openspec/specs/multi-dominio-scope/spec.md` (new capability, copied from
  this change's spec verbatim).

## Pending (user-owned)

1. Apply 023 to dev/prod databases.
2. Manual rule-75 check against a migrated DB.
3. Commit/push/PR of `feat/reglas-multi-dominio`.
