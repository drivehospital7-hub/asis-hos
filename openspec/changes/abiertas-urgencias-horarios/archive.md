# Archive Note — abiertas-urgencias-horarios

**Change**: `abiertas-urgencias-horarios` (verbatim: *en abiertas-urgencias quiero que podamos ir guardando los horarios...*)
**Archived**: 2026-09-03
**Mode**: `engram` — source of truth is Engram, this file is legacy trail only
**Status**: PASS WITH WARNINGS — archived to Engram

## Engram Archive Report

Canonical report: **Engram `sdd/abiertas-urgencias-horarios/archive-report`** (id **1760**, sync `obs-d82c418d1db3ff72`)

Verbatim mirror: `sdd/en-abiertas-urgencias-quiero-que-podamos-ir-guardando-los-horarios/archive-report` (id 1761) — same content, truncated key fallback.

Full report includes: change summary, intent, files changed (726 insertions, 12 tracked + 5 new untracked), test evidence (58 pytest PASSED + 199 vitest PASSED + build), spec compliance, risks W1/W2, rollback plan, next steps, traceability.

## Test Evidence (from verify-report 1758/1759)

- `python -m pytest tests/services/test_abiertas_urgencias_service.py tests/routes/test_abiertas_urgencias_routes.py tests/services/test_control_errores_sin_horario.py -v` → **58 PASSED** (21+30+7)
- `npx vitest run` → **199 PASSED** (4 files)
- `npm run build --prefix frontend` → success 2.13s

## Risks

- **W1** No RED commits in git log (process gap, TDD proven via stash not commits) — warning only
- **W2** Pre-existing failure `test_helper_falls_back_to_text_content` unrelated — not blocking

## Spec Sync

Engram mode — no `openspec/specs/` merge, no `openspec/changes/archive/YYYY-MM-DD-*` move. Source-of-truth delta is `CONVENTIONS.md:322-343` paragraph + Engram archive report.

## Tasks Gate

`tasks.md` + Engram 1754: **0 unchecked** — all T1-T7 DONE. Apply-progress and verify-report prove completion.

## Observation IDs

| Artifact | ID | Topic |
|----------|----|-------|
| proposal | 1751 | `sdd/abiertas-urgencias-horarios/proposal-restore` |
| spec | 1752 | `sdd/abiertas-urgencias-horarios/spec` |
| design | 1753 | `sdd/abiertas-urgencias-horarios/design` |
| tasks | 1754 | `sdd/abiertas-urgencias-horarios/tasks` |
| apply-progress | 1755/1756/1757 | `sdd/abiertas-urgencias-horarios/apply-progress*` |
| verify-report | 1758/1759 | `sdd/abiertas-urgencias-horarios/verify-report` |
| archive-report | 1760 (canonical) | `sdd/abiertas-urgencias-horarios/archive-report` |

This note ensures `openspec/changes/abiertas-urgencias-horarios/` has an archive trail despite engram-mode storage. Do not delete — legacy audit trail.
