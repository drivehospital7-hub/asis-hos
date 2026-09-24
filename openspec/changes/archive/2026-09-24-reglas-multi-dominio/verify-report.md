# Verify Report: reglas-multi-dominio

**Change**: `reglas-multi-dominio` (slice 1 backend + slice 2 frontend)
**Verified**: 2026-09-24
**Verdict**: PASS

## Scope verified

- Slice 1 backend (migration 023, model, service, engine) — worker TDD + parent gate.
- Slice 2 frontend (api types, scope editor, badges, filters) — worker + parent gate.

## Evidence

| Check | Command | Result |
|---|---|---|
| Backend scoped | `python -m pytest tests/reglas/test_regla_dominios.py tests/engine/test_multi_dominio_resolution.py tests/reglas/test_rule_service.py tests/engine/test_dominio_scoped_loading.py tests/engine/test_domain_detection.py tests/engine/test_rule_based_detector_dominio.py` | 85 passed (parent re-run) |
| API routes | `python -m pytest tests/reglas/test_api_routes.py` | 21 passed after applying 023 to `asis_hos_test` (was 2 failed on stale schema) |
| Backend broad | `python -m pytest tests/reglas tests/engine -q` | 975 passed |
| Migration (test DB) | `TEST_DB_NAME=asis_hos_test python run_migrations.py --apply --confirm` | 27 ok, 0 errores |
| Frontend scoped | `vitest run src/pages/admin-reglas src/components/admin-reglas src/lib` (from `frontend/`) | 161 passed (parent re-run) |
| Types | `tsc --noEmit` (from `frontend/`) | clean |
| Bundle | `npm run build` | fresh admin-reglas bundle with the new UI |

## Known notes (not failures)

- `tests/pages/monitoreo-carpetas/useMoveFacturas.test.ts` (frontend): 1 failure,
  pre-existing and unrelated — verified failing with all change files stashed.
- Migration 023 applied ONLY to `asis_hos_test`. Dev/prod databases still pending
  (explicit user step).
- Manual rule-75 check (fires in urgencias + hospitalizacion, hidden in
  odontologia) pending a running app against a migrated DB.
- No commits made (user safety rule); work lives uncommitted on
  `feat/reglas-multi-dominio`.
