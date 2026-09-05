# Tasks: abiertas-urgencias horarios por mes con responsable coincidente

**Change**: `abiertas-urgencias-horarios` (verbatim: *en abiertas-urgencias quiero que podamos ir guardando los horarios...*)
**Project**: asis-hos
**Session**: auto | **Delivery strategy**: single-pr-default | **Review budget**: 800 lines | **Strict TDD**: true (pytest 9.0.3 + vitest 4.1.7)

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines (prod) | ~380 |
| Estimated test lines (new) | ~420 |
| **Total** | **~800** |
| Files touched (prod) | 5 (`abiertas_urgencias_service.py`, `abiertas_urgencias.py`, `control_errores_service.py`, `frontend/.../page.tsx`, `frontend/.../utils.ts`) |
| Files touched (tests) | 4 (`tests/test_abiertas_urgencias_service.py`, `tests/test_abiertas_urgencias_routes.py`, `tests/test_control_errores_sin_horario.py`, `frontend/.../__tests__/utils.test.ts`) |
| 400-line budget risk | Low — prod delta ~380 < 400 per-PR guideline; total with tests fits 800 single-PR budget exactly |
| Chained PRs recommended | **No** — single PR suffices |
| Chain strategy | `size-exception` not needed; falls within `single-pr-default` + 800 budget |
| Forecast verdict | **Fits budget — no exception required.** Test lines are reviewable but mechanical; prod review load ~380 dominates. Split only if reviewer requests isolation of T5 guard. |
| Decision needed before apply | No |

*If implementation exceeds 800 during apply, split at T5 (backend guard) as separate slice — T1-T4 in PR1, T5-T7 in PR2 — but current estimate avoids it.*

---

## Dependency Graph

```
T1 (service storage) ──► T2 (routes) ──► T3 (frontend state+selector) ─┐
                                         T4 (per-factura + Sin horario) ├─► T5 (control errores guard) ──► T6 (tests consolidation) ──► T7 (migration+docs polish)
                                          (T3 and T4 can run in parallel after T2)
```

All tasks keep individual file <50 lines of implementation logic (AGENTS.md SRP); helpers are <50 lines each.

---

## T1 — Backend service storage + helpers [BACK]

**Title**: File-per-month storage helpers and CRUD (mes/anio scoped)

**Description**: Replace single-file `HORARIO_FILE` with sharded layout `app/data/horarios/abiertas_urgencias_YYYY-MM.json`. Add `_horario_path(mes,anio)`, `_ensure_data_dir()`, `_migrate_legacy_if_needed()`, `list_horarios()`, and extend `get_horario(mes,anio)`, `save_horario(mes,anio,dias)`, `delete_horario(mes,anio)` with atomic temp+rename, range validation, and `[BACK]` logging.

**Files**:
- `app/services/abiertas_urgencias_service.py` (MODIFY)
- `app/data/horarios/` (NEW dir — created on demand, ensure git keeps placeholder `.gitkeep` if needed)

**Acceptance Criteria (Given/When/Then)**:
- **AC1 Save creates file**: GIVEN no file for 2026-09, WHEN `save_horario(9,2026,[{dia:1,manana:"CARLOS",tarde:"ALEJANDRA",noche:"YULIETH"}])`, THEN `app/data/horarios/abiertas_urgencias_2026-09.json` exists with `{mes:9, anio:2026, total_dias:1}` and `get_horario(9,2026)` returns same dias.
- **AC2 Get missing returns null**: GIVEN no file for 2026-07, WHEN `get_horario(7,2026)`, THEN `{"status":"success","data":{"horario":null,"total_dias":0},"errors":[]}` (no exception).
- **AC3 List sorted**: GIVEN files for 2026-08 and 2026-09, WHEN `list_horarios()`, THEN `data.meses == ["2026-08","2026-09"]` sorted ascending.
- **AC4 Delete scoped**: GIVEN files 2026-08 and 2026-09, WHEN `delete_horario(9,2026)`, THEN 2026-09 removed and 2026-08 still present; second delete is idempotent success.
- **AC5 Atomic write**: WHEN `save_horario` is called, THEN tmp file `.tmp.<pid>` is written then `rename()` — no torn read observable; logs contain `[BACK] Horario guardado: N dias para M/A`.
- **AC6 Range validation**: WHEN `save_horario(0,2026,...)` or `mes=13` or `anio=1999`, THEN `{"status":"error","errors":["mes invalido"]}` and no file created.
- **AC7 Legacy migration**: GIVEN legacy `app/data/horario_abiertas_urgencias.json` with `mes=8,anio=2026` and no sharded 2026-08, WHEN `list_horarios()` called, THEN sharded file created with same dias, legacy file retained, log `[BACK] Migrating legacy horario 8/2026 -> horarios/...`.

**Dependencies**: None (root).

**Estimate**: M (medium — ~80 lines prod, helpers each <30 lines).

**Test plan (strict TDD — RED before GREEN)**:
- Write failing `tests/services/test_abiertas_urgencias_service.py` covering AC1-AC7 (use `tmp_path` monkeypatch for `app/data/horarios`).
- Run `python -m pytest tests/services/test_abiertas_urgencias_service.py -v` — must FAIL before implementation, PASS after.
- Also verify `python -m pytest -v -k abiertas_urgencias` green; check logging capture contains `[BACK]`.

**Delivery slice**: Slice 1 — backend storage (no route exposure yet; service testable in isolation).

---

## T2 — Backend routes (thin delegators)

**Title**: GET /api/schedules, GET/POST/DELETE /api/schedule with mes/anio + legacy compat

**Description**: Add `GET /api/schedules` → `list_horarios()`. Extend `GET /api/schedule?mes=&anio=` to delegate to `get_horario(mes,anio)` when params present else legacy current-month compat. Extend `POST /api/schedule` to accept `{mes,anio,dias}` (legacy body with only `dias` defaults to `_mes_actual()`). Extend `DELETE /api/schedule?mes=&anio=` scoped delete (missing params → 400). All routes remain thin delegators per AGENTS.md (zero logic, just param parse + `jsonify(result)`), guarded by `@permiso_requerido("facturas_abiertas" | "facturas_abiertas:write")`.

**Files**:
- `app/routes/abiertas_urgencias.py` (MODIFY)

**Acceptance Criteria**:
- **AC1 List**: GIVEN sharded files for 2026-08/09, WHEN `GET /api/schedules`, THEN 200 `{"status":"success","data":{"meses":["2026-08","2026-09"]}}`.
- **AC2 Get with params**: WHEN `GET /api/schedule?mes=09&anio=2026` with auth, THEN returns horario for that month; WHEN missing file, THEN 200 with `horario:null` (not 404).
- **AC3 Legacy compat**: WHEN `GET /api/schedule` without params, THEN returns current-month horario (delegates to `get_horario()` with mes_actual) — keeps old frontend working.
- **AC4 Post new month**: WHEN `POST /api/schedule` with `{mes:9,anio:2026,dias:[...]}` and `can_write`, THEN 200 success and file created; WHEN body has only `dias` (legacy), THEN saves to current month.
- **AC5 Post validation**: WHEN `POST` with `mes=0` or missing `dias`, THEN 400 or `status:error` with `errors` containing validation message.
- **AC6 Delete scoped**: WHEN `DELETE /api/schedule?mes=09&anio=2026`, THEN 200 and file removed; WHEN missing params, THEN 400 `{"status":"error","errors":["mes y anio requeridos"]}`.
- **AC7 Auth**: WHEN `POST`/`DELETE` without `facturas_abiertas:write`, THEN 403 or redirect per `permiso_requerido` (existing behavior).

**Dependencies**: T1 (service helpers must exist).

**Estimate**: S (small — ~40-50 lines, 4 endpoints, each <15 lines).

**Test plan (strict TDD)**:
- Write failing `tests/routes/test_abiertas_urgencias_routes.py` (use `app_client` fixture, `tmp_path` patch for service dir) covering AC1-AC7.
- `python -m pytest tests/routes/test_abiertas_urgencias_routes.py -v` RED→GREEN.
- Integration: `python -m pytest tests/routes/test_abiertas_urgencias_routes.py tests/services/test_abiertas_urgencias_service.py -v` must pass together; envelope never `warning`.

**Delivery slice**: Slice 1 — backend vertical (T1+T2 ship together as first reviewable unit; frontend not yet changed).

---

## T3 — Frontend state + month selector (per-month edit reuse)

**Title**: Replace singleton schedule with horariosMap + selectedKey, loadSchedules parallel fetch, per-month selector and editable textarea flow

**Description**: In `frontend/src/pages/abiertas-urgencias/page.tsx`, replace `schedule: ScheduleDay[]|null` + single `loadSchedule()` with `horariosMap: Record<string, ScheduleDay[]>` (`"YYYY-MM"` zero-padded) + `selectedKey: string`. On mount: `loadSchedules()` fetches `GET /api/schedules` then parallel `GET /api/schedule?mes=&anio=` for each month (Promise.all) plus fallback legacy `GET /api/schedule` if list empty. Add month selector `<select>` listing `Object.keys(horariosMap).sort()` + current-month default (`new Date()` → `YYYY-MM`). Derive `schedule = horariosMap[selectedKey] ?? null` and `scheduleStatus` per selected month (`loading|loaded|empty`). Reuse `parseScheduleText(text)` unchanged; `handleGuardarHorario` becomes per-month `POST /api/schedule {mes,anio,dias}` split from `selectedKey`; delete becomes `DELETE ?mes=&anio=` scoped to selectedKey with fallback selection. Keep `showParseCard` scoped per selectedKey, copy/edit/cargar toggles reuse existing UI. Log `[FRONT]` for load/select/save/delete.

**Files**:
- `frontend/src/pages/abiertas-urgencias/page.tsx` (MODIFY)

**Acceptance Criteria**:
- **AC1 Load map**: GIVEN backend has 2026-08 and 2026-09, WHEN page mounts, THEN `horariosMap` equals `{"2026-08":[...],"2026-09":[...]}` and selector shows both options sorted, default `selectedKey` is current month (or first sorted if current absent).
- **AC2 Selector switch**: WHEN user selects `2026-08` in dropdown, THEN `Ver horario` table re-renders with August dias (not September), `[FRONT] Seleccionado mes 2026-08` logged.
- **AC3 Save scoped**: GIVEN `selectedKey=2026-09` with dias, WHEN user edits textarea and saves, THEN `POST /api/schedule {mes:9,anio:2026,dias}` called, `horariosMap["2026-09"]` updated, toast `Horario guardado — N dias para 09/2026`, and `GET /api/schedules` would include `2026-09` while `2026-08` unchanged.
- **AC4 Delete scoped**: GIVEN keys 2026-08/09, WHEN delete for 2026-09 confirmed, THEN `DELETE /api/schedule?mes=09&anio=2026` called, key removed from map, selector falls back to remaining key, toast `Horario eliminado`.
- **AC5 Legacy fallback**: GIVEN no sharded files but legacy `GET /api/schedule` returns horario for current month, WHEN `GET /api/schedules` returns `[]`, THEN `horariosMap` contains current month from legacy GET (compat path).
- **AC6 Edit reuse**: WHEN `selectedKey` changes, textarea parse via `parseScheduleText` still works per month — editing 2026-09 does not affect 2026-08 table.

**Dependencies**: T2 (routes must expose list + param get).

**Estimate**: M (medium — ~60 lines state + ~30 lines selector UI, each helper <50 lines).

**Test plan (strict TDD)**:
- Extend `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts` not needed for T3 (state is integration), but add `frontend/src/pages/abiertas-urgencias/__tests__/page.integration.test.tsx` (optional) mocking `fetch` for `GET /api/schedules` + parallel schedule fetches — RED: selector not rendered, GREEN: renders with mocked months.
- Manual/local: `npm run test -- --run` or `npx vitest run` — existing `utils.test.ts` must stay green.
- Verify: `npm run build` succeeds (`tsc -b && vite build`) — no type errors for `Record<string, ScheduleDay[]>`.

**Delivery slice**: Slice 2 — frontend state (can ship independently after T2; if chained, PR2).

---

## T4 — Frontend per-factura resolution + Sin horario + gating

**Title**: Month-coincident calcularResponsable, per-row horario lookup, Sin horario sentinel, filter and Envío disable

**Description**: Extend `calcularResponsable(fechaCrea, fechaEgreso, horarioForMonth: ScheduleDay[]|null): string` — if `!horarioForMonth || length===0` return `"Sin horario"` (new sentinel distinct from `"Sin Egreso"/"Sin cronograma"/"Dia N sin asignacion"`). Keep 30-min reception (06:30-12:29 manana, 12:30-18:29 tarde, else noche with `dia-1` correction) and `NOMBRE_MAP` unchanged. In `page.tsx` `handleProcesarFacturas`, REMOVE global early guard `if (!schedule || schedule.length===0) return` — instead for each factura row parse `fechaEgreso` via existing `parseDate` strict `dd/mm/yyyy hh:mm:ss`, derive `key = YYYY-MM(egreso)` (`padStart(2,"0")`), lookup `horarioForMonth = horariosMap[key] ?? null`, then `responsable = calcularResponsable(fechaCrea, fechaEgreso, horarioForMonth)`. Malformed egreso → `"Sin horario"` and `[FRONT][ERROR]` log. Extend `getSinEgresoButtonConfig(isSinEgreso, estado, isSinHorario?)` — when `isSinHorario=true` return `{disabled:true, title:"Sin horario: cargue horario de ese mes"}` (takes precedence). In results table, compute `isSinHorario = r.responsable === "Sin horario"` and pass to gating; filter dropdown via `getUniqueResponsables` automatically includes `"Sin horario"` as option; `copiarResultados` already generic. Keep `masDeDosTurnosMismoResponsable` same-month-as-egreso guard (documented intentional — historical months no vencida).

**Files**:
- `frontend/src/pages/abiertas-urgencias/utils.ts` (MODIFY — signature + Sin horario branch)
- `frontend/src/pages/abiertas-urgencias/page.tsx` (MODIFY — per-row lookup, remove abort, wire gating)

**Acceptance Criteria**:
- **AC1 Egreso month wins**: GIVEN `horariosMap` has 2026-08 manana CARLOS→CARLOS OMAR and 2026-09 manana ALEJANDRA→ALEJANDRA ESPAÑA, WHEN factura egreso `15/09/2026 14:00:00` processed, THEN `responsable === "ALEJANDRA ESPAÑA"` (not August).
- **AC2 Null schedule → Sin horario**: GIVEN `calcularResponsable("10/09/2026 08:00:00","10/09/2026 14:00:00", null)`, THEN returns `"Sin horario"`.
- **AC3 Malformed egreso → Sin horario**: WHEN egreso `"not-a-date"` or `"10-09-2026"`, THEN `"Sin horario"` (not crash), `[FRONT][ERROR] Parse fecha egreso fallo` logged.
- **AC4 Per-factura not abort**: GIVEN `horariosMap` lacks 2026-09 but has 2026-08, WHEN `handleProcesarFacturas` runs with factura A egreso `10/09/2026` and factura B `20/08/2026`, THEN results = `[{factura:A,responsable:"Sin horario"}, {factura:B,responsable:"...from August..."}]` — no early toast block, no exception.
- **AC5 Filter includes Sin horario**: GIVEN results contain `"Sin horario"`, WHEN `getUniqueResponsables(results)` called, THEN array includes `"Sin horario"` and `filterResultsByResponsable(results,"Sin horario")` returns that row.
- **AC6 Gating disables Envío**: WHEN `getSinEgresoButtonConfig(false,"Abierta", true)` or `isSinHorario=true` derived from `responsable==="Sin horario"`, THEN `{disabled:true, title:"Sin horario: cargue horario de ese mes"}` and rendered button has `disabled` + tooltip; click does not call `handleSendToControl`.
- **AC7 Night correction still works with per-month**: WHEN egreso `05/09/2026 03:00:00` (before 06:30), THEN lookup `dia=4` noche from September horario (not August).

**Dependencies**: T3 (horariosMap must exist); T1 signature change (utils) logically independent but needs map.

**Estimate**: M (medium — utils ~15 lines changed + page per-row loop ~25 lines; each function stays <50).

**Test plan (strict TDD)**:
- Vitest RED: add to `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts`:
  - `calcularResponsable` with `null` horario → `Sin horario`
  - `calcularResponsable` with malformed egreso → `Sin horario`
  - `calcularResponsable` month-coincident (two maps differing same day)
  - `getSinEgresoButtonConfig` with `isSinHorario=true` → disabled
  - `filterResultsByResponsable` includes `Sin horario`
  - `masDeDosTurnosMismoResponsable` historical month guard stays false
- Run `npx vitest run` — must fail before, pass after.
- Page integration: mock `horariosMap` lacking key, assert Envío button disabled attribute.
- Backend still isolated: `python -m pytest -v` unaffected.

**Delivery slice**: Slice 2 — frontend resolution (pairs with T3; can ship together).

---

## T5 — Control errores defense guard (backend)

**Title**: Reject Factura Abierta with Sin horario (defense-in-depth)

**Description**: In `app/services/control_errores_service.py` `add_error(data)`, before `crear_error`, add guard: if `tipo_error == "Factura Abierta"` and `responsable == "Sin horario"` (case exact, after `_resolve_responsable_identity` normalizes), return `{"status":"error","data":{},"errors":["No se puede enviar Factura Abierta sin horario: cargue el horario del mes de egreso"],"success":false}` (preserve envelope, never `warning`). Log `[BACK][ERROR] Rechazo Factura Abierta sin horario: factura={factura}`. Do NOT block other `tipo_error` with same responsable, nor other responsables (`Sin Egreso` already has separate guard elsewhere).

**Files**:
- `app/services/control_errores_service.py` (MODIFY — ~10 lines)

**Acceptance Criteria**:
- **AC1 Reject**: GIVEN `POST /api/control-errores` payload `{tipo_error:"Factura Abierta", factura:"FEV123", responsable:"Sin horario"}`, WHEN `add_error` called, THEN response `status:error, success:false, errors` mentions horario required and no error created in storage.
- **AC2 Accept real name**: GIVEN `responsable:"CARLOS OMAR"` with same tipo_error, THEN `status:success` and error created.
- **AC3 Accept other tipo**: GIVEN `tipo_error:"Otros"` with `responsable:"Sin horario"`, THEN success (only Factura Abierta blocked).
- **AC4 Accept Sin Egreso still routed**: `Sin Egreso` with Factura Abierta follows existing validation (not this guard) — not conflated.

**Dependencies**: T4 (defines `Sin horario` sentinel); logically independent of T3 UI but must match string literal.

**Estimate**: S (small — guard <15 lines).

**Test plan (strict TDD)**:
- New `tests/services/test_control_errores_sin_horario.py` with AC1-AC4 (mock `crear_error` to assert not called on reject; use `app_client` for route variant if needed).
- `python -m pytest tests/services/test_control_errores_sin_horario.py -v` RED→GREEN.
- Regression: `python -m pytest tests/services/test_control_errores_service.py -v` still green.

**Delivery slice**: Slice 3 — backend guard (smallest slice; can ship with T1-T2 or standalone if chained).

---

## T6 — Tests consolidation (strict TDD proof)

**Title**: Pytest service/route/guard + Vitest utils gating — strict TDD verification

**Description**: Consolidate and prove coverage for all new behavior per `strict_tdd true` and `pyproject.toml [tool.openspec] tdd=true`. Ensure every prod task above has a failing test written BEFORE implementation (preserve RED commits). Add missing edge tests: atomic write no torn read, invalid mes/anio 400, legacy compat with and without sharded file, malformed fechaEgreso, night previous-day across months, filter includes Sin horario, gating disabled. Keep `AGENTS.md` response envelope `{status,data,errors}` never `warning`, and logging prefixes `[BACK]`/`[BACK][ERROR]`/`[FRONT]` asserted via `caplog`.

**Files**:
- `tests/services/test_abiertas_urgencias_service.py` (NEW/MODIFY)
- `tests/routes/test_abiertas_urgencias_routes.py` (NEW)
- `tests/services/test_control_errores_sin_horario.py` (NEW — from T5)
- `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts` (MODIFY — from T4)
- `frontend/src/pages/abiertas-urgencias/__tests__/page.integration.test.tsx` (NEW optional — Envío disabled when Sin horario)

**Acceptance Criteria**:
- **AC1 Service suite green**: `python -m pytest tests/services/test_abiertas_urgencias_service.py -v` covers T1 AC1-AC7 plus edge `test_atomic_write_no_torn`, `test_save_empty_error`, `test_get_missing_returns_null`, `test_migrate_legacy_keeps_backup`.
- **AC2 Route suite green**: `python -m pytest tests/routes/test_abiertas_urgencias_routes.py -v` covers T2 AC1-AC7 plus invalid mes 400.
- **AC3 Guard suite green**: `python -m pytest tests/services/test_control_errores_sin_horario.py -v` covers T5 AC1-AC4.
- **AC4 Vitest green**: `npx vitest run` (or `npm run test` in `frontend/`) — all new cases in `utils.test.ts` pass: month-coincident, null→Sin horario, malformed→Sin horario, gating disabled, filter includes Sin horario.
- **AC5 Strict TDD evidence**: Git log shows RED commits (failing tests) before GREEN commits for each slice (reviewer can verify `git log --oneline` has `test: RED` then `feat: GREEN` pattern).
- **AC6 Envelope & logging**: `caplog` assertions for `[BACK] Horario guardado`, `[BACK] Migrating legacy`, `[BACK][ERROR] Rechazo Factura Abierta sin horario`.

**Dependencies**: T1-T5 (tests prove those tasks).

**Estimate**: M (medium — test code ~300 lines total but mechanical; implementation-prod lines 0).

**Test plan**:
- `python -m pytest -v` — full suite (expect ~1372+ new tests) green.
- `npx vitest run` — frontend suite green.
- `python -m pytest --cov=app.services.abiertas_urgencias_service --cov=app.routes.abiertas_urgencias --cov=app.services.control_errores_service` — optional coverage report (no threshold enforced but verify >80% on touched files).

**Delivery slice**: Slice 3 — verification (ships with prod code in same PR per strict TDD; not a separate PR).

---

## T7 — Migration + docs polish (optional, small)

**Title**: Legacy 2026-08 migration polish, data dir gitignore, docs and logging hygiene

**Description**: Ensure `app/data/horarios/` is created on demand and not ignored by `.gitignore` (verify `app/data/**/*.json` handling; add `!app/data/horarios/*.json` exception if needed or add `.gitkeep`). Verify legacy `app/data/horario_abiertas_urgencias.json` (2026-08) is migrated on first `list_horarios()` and retained as backup (idempotent, no overwrite). Update `CONVENTIONS.md` or inline docstring for new storage layout and `Sin horario` semantics. Clean up any `print()` → `logger.info("[BACK] ...")` per `asis-hos-logging` skill; ensure `frontend` logs use `[FRONT]` prefix. Keep `app/constants/` untouched (no new hardcoded constants beyond existing `columnas`).

**Files**:
- `app/data/horarios/.gitkeep` (NEW if gitignore would hide dir)
- `.gitignore` (VERIFY — no change if already allows)
- `CONVENTIONS.md` or `app/services/abiertas_urgencias_service.py` docstring (MODIFY — 1 paragraph)
- `app/data/horario_abiertas_urgencias.json` (RETAIN — backup)

**Acceptance Criteria**:
- **AC1 Migration idempotent**: GIVEN legacy file with `mes=8,anio=2026` and sharded `2026-08` already exists, WHEN `list_horarios()` called again, THEN sharded file NOT overwritten (keeps newer dias if manually edited), legacy still exists.
- **AC2 Dir persistence**: AFTER `git clean -fdx` (or fresh clone), `app/data/horarios/` dir is recreated on first `save_horario` without error.
- **AC3 Docs**: `CONVENTIONS.md` or service docstring mentions `app/data/horarios/abiertas_urgencias_YYYY-MM.json` layout and `Sin horario` gating.
- **AC4 Logging hygiene**: `grep -rn "print(" app/services/abiertas_urgencias_service.py` returns 0; `grep -rn "\[BACK\]" app/services/abiertas_urgencias_service.py` shows info/error logs for save/delete/migrate.

**Dependencies**: T1 (migration helper), T6 (tests must reflect idempotent behavior).

**Estimate**: S (small — <20 lines).

**Test plan**:
- `python -m pytest tests/services/test_abiertas_urgencias_service.py::test_migrate_legacy_idempotent -v` passes.
- Manual: `ls app/data/horarios/` after save shows `abiertas_urgencias_YYYY-MM.json`; `cat` matches expected JSON shape.
- `grep -rn "print(" app/` — zero hits in touched files.

**Delivery slice**: Slice 3 polish — can be folded into Slice 1 if budget allows (single commit `chore: migration polish`).

---

## Delivery Slices Summary

| Slice | Tasks | Prod lines | Test lines | Reviewable | PR |
|-------|-------|-----------|-----------|------------|----|
| Slice 1 — Backend storage | T1 + T2 + T7 | ~130 | ~180 | ~310 | PR1 (if chained) or part of single PR |
| Slice 2 — Frontend | T3 + T4 | ~115 | ~150 | ~265 | PR1 continued or PR2 |
| Slice 3 — Guard + verification | T5 + T6 | ~15 | ~90 | ~105 | PR1 continued or PR3 |
| **Total** | **T1-T7** | **~380 prod** | **~420 test** | **~800** | **Single PR (default)** |

Single-PR fits exactly at 800 — no exception needed. If reviewer prefers chained, split at slice boundaries (each slice <400 prod, review budget per PR <400).

---

## Skill Resolution

| Skill | Applied? | Why |
|-------|----------|-----|
| `asis-hos-detector-pattern` | **Not applied** — explicitly skipped | Abiertas-Urgencias is standalone paste-driven, not a `transversales/odontologia/urgencias` detector; per design decision, no `detect_all.py` pattern. |
| `asis-hos-excel-headers` | **Not applied** | No Excel headers involved; paste is TSV cronograma + facturas, not `get_column_indices` mapping. |
| `asis-hos-logging` | **Applied** — `[BACK]`/`[FRONT]`/`[BACK][ERROR]` prefixes | Service logs `Migating legacy`, `Horario guardado/eliminado`; route errors logged; frontend logs month select/edit/save with `[FRONT]`, parse failures with `[FRONT][ERROR]`. No `print()`/`console.log()` generics. |

---

## Commit Plan (per slice, strict TDD)

Each slice follows RED→GREEN:
1. `test: RED - <task> failing test (strict TDD)` — add failing pytest/vitest, run `python -m pytest -v` / `npx vitest run` to prove FAIL.
2. `feat: GREEN - <task> implementation (<50 lines)` — implement prod, run same verification to prove PASS.

Example for T1:
- `test: RED - abiertas_urgencias service sharded storage (T1)`
- `feat: GREEN - abiertas_urgencias service file-per-month + atomic write (T1)`

---

## Verification Commands (per task)

```bash
# Backend — after T1/T2/T5
python -m pytest tests/services/test_abiertas_urgencias_service.py -v
python -m pytest tests/routes/test_abiertas_urgencias_routes.py -v
python -m pytest tests/services/test_control_errores_sin_horario.py -v

# Full backend suite
python -m pytest -v

# Frontend — after T3/T4
npx vitest run
# or
npm run test --prefix frontend

# Build check — after T3/T4
npm run build --prefix frontend
```

---

## Risks

- **Sharded file contract break** mitigated by legacy compat GET without params (old frontend still works until new build ships together).
- **Malformed fechaEgreso parse** — strict `dd/mm/yyyy hh:mm:ss` regex returns `Sin horario` not exception; logged `[FRONT][ERROR]`.
- **Concurrent writes** — temp+rename last-write-wins, acceptable for low contention (~few saves/month manual); document, no file-lock.
- **Topic_key truncation** — long verbatim change name truncates `topic_key` collision between `/proposal` and `/spec`; use short mirror `sdd/abiertas-urgencias-horarios/*` as canonical (applied here).

---

## Next Recommended

`sdd-apply` — implement T1→T2→T3/T4→T5→T6 in order, strict TDD, keep routes thin and SRP.

