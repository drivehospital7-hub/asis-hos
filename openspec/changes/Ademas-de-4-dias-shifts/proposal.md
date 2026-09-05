# Proposal: Además-de-4-días-shifts

## Intent

A factura with estado "Abierta" should also render as vencida when the assigned responsible person has worked ≥2 shifts since the egreso date — even if fewer than 4 calendar days have passed. Fall back to the existing 4-day rule when no schedule is loaded.

## Scope

### In Scope
- New `masDeDosTurnosMismoResponsable()` pure function in `utils.ts`
- Modified `esVencida()` — accepts `responsable` and `schedule`, runs shift check when schedule exists
- Updated call site in `page.tsx` — passes `r.responsable` and `schedule` to `esVencida`
- Unit tests for shift counting and all edge cases
- Delta spec updating "Detect Vencida Rows" from `responsible-assignment`

### Out of Scope
- Backend changes (all logic is client-side)
- UI changes beyond the vencida row background
- "Envío a Control" button behavior
- Cross-month schedule navigation or past-month schedule caching

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `responsible-assignment` (delta in `openspec/changes/abiertas-urgencias-botones/specs/responsible-assignment/spec.md`): "Detect Vencida Rows" extends from date-only to date OR ≥2-responsible-shifts

## Approach

**New function** `masDeDosTurnosMismoResponsable(fechaEgreso, responsable, schedule)`:

1. Parse `fechaEgreso` WITH time (use `parseDate` from utils.ts, which preserves hours)
2. Determine egreso shift via same boundary logic as `calcularResponsable` (06:30/12:30/18:30)
3. Find the **next** shift after egreso's shift where this `responsable` appears — scan forward in schedule days/slots
4. Count all shifts by `responsable` from that next shift up to "now"
5. Return `true` if count ≥ 2

**"Now" boundary**: count only fully elapsed shifts (current in-progress shift does NOT count). For the current day, only shifts whose end time has passed.

**Modified `esVencida(estado, fechaEgreso, responsable, schedule)`**:
- If `schedule` exists AND `masDeDosTurnos...` returns true → vencida
- Otherwise → original 4-day calendar check (unchanged)

**Key edge cases**:
- Egreso month ≠ current month → can't count shifts (schedule only covers this month) → return false, fall through to 4-day
- Responsible has zero future shifts in schedule → return false
- Egreso time falls in night shift (18:30-06:29) → next shift is the afternoon of the same calendar day
- Name normalization: compare via `NOMBRE_MAP` same as `calcularResponsable` to handle short→full mapping

## Affected Areas

| Area | Impact | |
|------|--------|-|
| `frontend/src/pages/abiertas-urgencias/utils.ts` | Modified | + `masDeDosTurnosMismoResponsable()`, `esVencida` signature change |
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modified | `esVencida` call site, pass `responsable` + `schedule` |
| `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts` | Modified | New test cases for shift counting |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Schedule only covers current month | High | Return false when egreso month ≠ now; 4-day rule still applies |
| Name mismatch (NOMBRE_MAP vs schedule raw) | Medium | Normalize both sides via same NOMBRE_MAP before comparing |
| "Now" semantics ambiguous for partial shifts | Med | Count only fully elapsed shifts (current shift excluded) |
| Performance — scanning all days for each row | Low | Schedule is small (~31 days × 3 slots). Negligible |

## Rollback Plan

Revert `utils.ts`, `page.tsx`, and test file to HEAD. The original `esVencida` 2-arg signature is restored with no call-site changes needed — pure revert.

## Dependencies

None. `schedule` is already in component scope as React state.

## Success Criteria

- [ ] Factura <4 days old with ≥2 shifts by same person since egreso → renders red background
- [ ] No schedule loaded → 4-day rule only (no regression)
- [ ] Responsible with no future shifts → 4-day rule only
- [ ] Egreso in previous month → 4-day rule only
- [ ] All existing `utils.test.ts` tests pass unchanged
