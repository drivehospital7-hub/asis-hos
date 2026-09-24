# Tasks: Reglas multi-dominio

## Phase 1 — Data (migration + model)

- [ ] 1.1 Write `migrations/023_regla_dominios.sql` (CREATE TABLE + guarded
      backfill + index, PG/SQLite portable) and `023_regla_dominios_rollback.sql`
      (~40 lines SQL)
- [ ] 1.2 Add `ReglaDominio` model + `Regla.dominios` relationship
      (`cascade="all, delete-orphan"`, `lazy="selectin"`) + `to_dict`
      `dominios` sorted in `app/models.py` (~40 lines)
- [ ] 1.3 SQL-text test for 023 (precedent: `test_migration_022`) — file
      exists, ordered after 022, backfill shape, no hardcoded ids
      (~60 lines)

## Phase 2 — Backend (constants + service + API)

- [ ] 2.1 Add `REGLA_DOMINIOS_VALIDOS` to `app/constants/base.py` (~15 lines)
- [ ] 2.2 `rule_service.py`: accept/validate `dominios` on create/update
      (non-empty + vocabulary, atomic bridge write + legacy mirror),
      legacy single-`dominio` fallback, scope copy in `duplicate_rule` /
      `create_version`, ∈ semantics in `list_rules` (~90 lines + docstrings)
- [ ] 2.3 `reglas_api.py`: accept `dominios` on POST/PUT, 400 envelope on
      validation errors (~30 lines)
- [ ] 2.4 Service tests: validation rejects, rollback clean, duplicate/version
      copy scope, list filter ∈, legacy caller compat
      (extend `tests/reglas/test_rule_service.py` or new file, ~150 lines)

## Phase 3 — Engine (resolution)

- [ ] 3.1 Shared `rule_matches_domain` EXISTS helper + replace the 4
      OR-transversal sites (`rule_resolver.py`, `domain_detection.py` ×1
      active path, `engine.py:_load_rule_by_name` with exact-first ordering);
      replace stray `'transversal'` literals with `ENGINE_DOMAIN_TRANSVERSAL`
      (~60 lines)
- [ ] 3.2 Engine tests: multi match, transversal-all, single unaffected,
      exact-beats-transversal, scope-less legacy fallback
      (~140 lines)

## Phase 4 — Frontend (admin-reglas)

- [ ] 4.1 `api-reglas.ts`: `dominios: string[]` types (+ legacy `dominio`)
      (~15 lines)
- [ ] 4.2 Scope checkbox editor in create/edit forms with empty-save guard;
      stacked badges; ∈ filters; unknown-value preservation
      (~120 lines tsx)
- [ ] 4.3 Vitest: save payload, badge render, filter ∈
      (~90 lines)

## Phase 5 — Verification

- [ ] 5.1 Full `pytest` green + `vitest` admin-reglas green + `tsc` clean
- [ ] 5.2 Manual: rule 75 scoped `['urgencias','hospitalizacion']` fires in
      both runs, hidden in `odontologia`; transversal unchanged
- [ ] 5.3 Rebuild `app/static/react-dist` so the served bundle carries the UI

## Review Workload Forecast

- Estimated changed lines (code, excl. generated dist): ~850.
- 400-line budget risk: **High**.
- Chained PRs recommended: **Yes** (natural split: Phase 1–3 backend PR,
  Phase 4 frontend PR).
- Decision needed before apply: **Yes** — delivery strategy is `single-pr`,
  so explicit `size:exception` acceptance is required before `sdd-apply`
  (per Review Workload Guard). Alternative: switch to `auto-chain` and split
  backend/frontend.
