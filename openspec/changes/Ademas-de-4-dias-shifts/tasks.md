# Tasks: Ademas-de-4-dias-shifts

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~105–125 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Core Implementation — utils.ts

- [x] 1.1 Add `slotIndex(hourMin: number): 0|1|2` private helper reusing the 06:30/12:30/18:30 boundaries from `calcularResponsable`
- [x] 1.2 Add exported `masDeDosTurnosMismoResponsable(fechaEgreso, responsable, schedule, now?)` with: month guard, night-shift correction to previous day's `noche`, flat shift‑index ordering (`day*3+slot`), reverse‑NOMBRE_MAP name matching, inclusive counting from egreso shift, exclusive stop before current‑in‑progress shift, return `count >= 2`

## Phase 2: Integration — page.tsx

- [x] 2.1 Update `esVencida` signature to `(estado, fechaEgreso, responsable?, schedule?)`: if `schedule` truthy and non‑empty and `responsable` truthy, delegate to `masDeDosTurnosMismoResponsable`; else fall through to existing 4‑day rule
- [x] 2.2 Update call site (line 647) to pass `r.responsable` and `schedule` to `esVencida`

## Phase 3: Testing — utils.test.ts

- [x] 3.1 Write tests for `masDeDosTurnosMismoResponsable` covering: ≥2 shifts since egreso → true; only egreso shift → false; egreso last month → false; current shift in‑progress not counted; night‑shift egreso before 06:30 (previous day noche); name via NOMBRE_MAP mapping; name not in NOMBRE_MAP matched as‑is; empty/absent schedule at `esVencida` level → 4‑day fallback
