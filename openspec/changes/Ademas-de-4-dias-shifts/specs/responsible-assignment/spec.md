# Responsible Assignment — Delta Spec

## Parent Spec

This is a **delta** on the existing "Responsible Assignment Specification" at:
`openspec/changes/abiertas-urgencias-botones/specs/responsible-assignment/spec.md`

Only the **Detect Vencida Rows** requirement is modified. All other requirements, scenarios, and behavior remain as defined in the parent spec.

---

## Change Summary

**Requirement: Detect Vencida Rows** is extended. Previously it used a single condition (egreso > 4 calendar days ago). Now it uses **two OR conditions**:

1. **Calendar rule** (unchanged): egreso > 4 calendar days before today → vencida
2. **Shift rule (new)**: the same responsible person has worked **≥ 2 shifts** counting from the egreso's own shift (inclusive) up to the last completed shift → vencida

If no schedule is loaded, condition 2 is skipped and only the 4-day calendar rule applies (no regression).

---

## Requirements

### Requirement: Shift-Counting Function — `masDeDosTurnosMismoResponsable`

The system MUST provide a pure function `masDeDosTurnosMismoResponsable(fechaEgreso: Date, responsable: string, schedule: ScheduleDay[]): boolean` that returns `true` when the responsible person appears in **≥ 2 completed shifts** after the egreso's shift, according to the loaded schedule.

#### Counting rules

1. **Determine egreso shift slot**: Use the same boundary logic as `calcularResponsable` (06:30–12:29 → `manana`, 12:30–18:29 → `tarde`, 18:30–06:29 → `noche`). The night shift maps to the **previous calendar day** when the time is before 06:30 (mirroring `calcularResponsable`).
2. **Counting starts from egreso's own shift (inclusive)**: The egreso's own shift slot counts as shift #1 for the same responsible person.
3. **Slot order per day**: `manana`, `tarde`, `noche`, then next day's `manana`.
4. **Name matching**: Normalize both the schedule name and `responsable` parameter via `NOMBRE_MAP` before comparing. A name present in the schedule that has no entry in `NOMBRE_MAP` is compared as-is.
5. **Completed shifts only**: The current in-progress shift MUST NOT be counted. A shift is considered "completed" when its end time has passed as of `new Date()`:
   - `manana` (ends 12:29): completed if current time ≥ 12:30
   - `tarde` (ends 18:29): completed if current time ≥ 18:30
   - `noche` (ends 06:29 next day): completed if current time ≥ 06:30 of next calendar day
6. **Stop scanning**: Stop at the last fully completed shift slot. Do not scan into future incomplete shifts.
7. **Return `false`** if the schedule is null/empty, if egreso is in a different month/year from today, or if fewer than 2 matching shifts are found.

### Requirement: Modified `esVencida`

The system MUST modify `esVencida` to accept two additional parameters:

```typescript
function esVencida(
  estado: string,
  fechaEgreso: string,
  responsable?: string,
  schedule?: ScheduleDay[] | null,
): boolean
```

- If `schedule` is truthy and non-empty AND `responsable` is truthy AND `masDeDosTurnosMismoResponsable()` returns `true` → return `true` (vencida) immediately.
- Otherwise → fall through to the existing 4-day calendar rule (unchanged from parent spec).
- If `schedule` is null/empty → skip shift check entirely, 4-day rule only.

### Requirement: Updated Call Site

The row rendering in `page.tsx` MUST pass `r.responsable` and `schedule` to `esVencida`:

```typescript
const isVencida = esVencida(r.estado, r.fechaEgreso, r.responsable, schedule);
```

---

## Scenarios

#### Scenario: ≥2 shifts since egreso, shift check returns true

- GIVEN schedule: day 1 = {manana: "CARLOS", tarde: "CARLOS", noche: ""}, day 2 = {manana: "", tarde: "", noche: ""}
- AND egreso on day 1 at 10:00 (`manana`), estado "Abierta"
- AND responsable "CARLOS OMAR"
- AND today is day 2 at 14:00
- WHEN `masDeDosTurnosMismoResponsable` is called
- THEN scans: day 1 `manana` = CARLOS (count 1 — egreso shift counts), day 1 `tarde` = CARLOS (count 2) → returns `true`

#### Scenario: Only 1 shift since egreso (egreso shift itself, no more)

- GIVEN schedule: day 1 = {manana: "CARLOS", tarde: "", noche: ""}, day 2 = {manana: "", tarde: "", noche: ""}
- AND egreso on day 1 at 10:00 (`manana`), estado "Abierta"
- AND responsable "CARLOS OMAR"
- AND today is day 2 at 14:00
- WHEN `masDeDosTurnosMismoResponsable` is called
- THEN scans: day 1 `manana` = CARLOS (count 1 — egreso shift), day 1 `tarde` = no match, day 1 `noche` = no match, day 2 = no CARLOS
- AND count = 1 < 2 → returns `false`

#### Scenario: No schedule loaded — 4-day rule only

- GIVEN `schedule` is `null`
- AND egreso 3 days ago, estado "Abierta"
- WHEN `esVencida` is called
- THEN returns `false` (skip shift check, 3 days ≤ 4)

#### Scenario: Estado not Abierta — never red

- GIVEN estado is "Cerrada"
- WHEN `esVencida` is called (with any schedule)
- THEN returns `false` immediately, no shifts evaluated

#### Scenario: Egreso in previous month — shift check skipped

- GIVEN schedule loaded for current month (June)
- AND egreso on 25 May, estado "Abierta"
- WHEN `masDeDosTurnosMismoResponsable` is called
- THEN returns `false` (egreso month differs from today's month)
- AND fallback: 4-day rule decides (15+ days → `true`)

#### Scenario: Responsable has no future shifts in schedule

- GIVEN schedule has CARLOS on day 1 `manana` only (the same day as egreso)
- AND egreso on day 1 at 10:00 (`manana`)
- AND responsable "CARLOS OMAR"
- WHEN `masDeDosTurnosMismoResponsable` is called
- THEN scans: day 1 `manana` = CARLOS (count 1 — egreso shift counts), day 1 `tarde` = no match, day 1 `noche` = no match, day 2+ = no CARLOS
- AND count = 1 < 2 → returns `false`

#### Scenario: Night shift egreso — egreso shift counts + next day shifts

- GIVEN schedule: day 1 = {..., noche: "CARLOS"}, day 2 = {manana: "CARLOS", tarde: "CARLOS", ...}
- AND egreso on day 1 at 20:00 (`noche` of day 1), responsable "CARLOS OMAR"
- AND today is day 2 at 18:30 (manana and tarde both fully elapsed)
- WHEN `masDeDosTurnosMismoResponsable` is called
- THEN scans: day 1 `noche` = CARLOS (count 1 — egreso shift counts), day 2 `manana` = CARLOS (count 2) → returns `true`

#### Scenario: Night shift egreso before 06:30 — previous day's noche

- GIVEN schedule: day 4 = {..., noche: "CARLOS"}, day 5 = {manana: "CARLOS", tarde: "CARLOS", ...}
- AND egreso on day 5 at 03:00 (`noche` of day 4), responsable "CARLOS OMAR"
- AND today is day 5 at 18:30
- WHEN `masDeDosTurnosMismoResponsable` is called
- THEN egreso is in `noche` of day 4 → day 4 `noche` = CARLOS (count 1), day 5 `manana` = CARLOS (count 2) → returns `true`

#### Scenario: < 4 days AND ≥ 2 shifts — shift wins

- GIVEN egreso on day 1 at 10:00, today is day 2 at 14:00 (≤ 4 days)
- GIVEN schedule: day 1 = {manana: "CARLOS", tarde: "CARLOS", noche: ""}
- AND responsable "CARLOS OMAR", estado "Abierta"
- WHEN `esVencida` is called
- THEN `masDeDosTurnosMismoResponsable` returns `true` (day 1 manana = CARLOS count 1, day 1 tarde = CARLOS count 2)
- AND the function returns `true` before checking the 4-day rule
- (Calendar rule alone would return `false` — only 2 days)

#### Scenario: Name normalization — short name matches full name

- GIVEN schedule has "CARLOS" on day 2 `manana`
- AND NOMBRE_MAP = {"CARLOS": "CARLOS OMAR"}
- AND responsable = "CARLOS OMAR"
- WHEN `masDeDosTurnosMismoResponsable` scans day 2 `manana`
- THEN CARLOS is normalized via NOMBRE_MAP to "CARLOS OMAR", matches responsable → counted

#### Scenario: Current shift not counted

- GIVEN schedule: day 1 = {manana: "CARLOS", tarde: "", noche: ""}, day 2 = {manana: "CARLOS", tarde: "", noche: ""}
- AND egreso on day 1 at 10:00 (`manana`), responsable "CARLOS OMAR"
- AND today is day 2 at 10:00 (manana of day 2 STILL IN PROGRESS, ends at 12:29)
- WHEN `masDeDosTurnosMismoResponsable` is called
- THEN scans: day 1 `manana` = CARLOS (count 1 — egreso shift counts), day 1 `tarde` = no match, day 1 `noche` = no match, day 2 — stop before current shift (manana in progress) → returns `false`
- (If day 2's manana were counted, count would be 2)

---

## Acceptance Criteria

- [ ] `esVencida` accepts 4 parameters and maintains backward compatibility with the existing rendering
- [ ] `masDeDosTurnosMismoResponsable` returns `true` when ≥ 2 shifts of same person exist, counting from the egreso's own shift (inclusive)
- [ ] `masDeDosTurnosMismoResponsable` returns `false` when fewer than 2 shifts exist
- [ ] `masDeDosTurnosMismoResponsable` returns `false` when schedule is null/empty (skip)
- [ ] `masDeDosTurnosMismoResponsable` returns `false` when egreso month ≠ current month
- [ ] `masDeDosTurnosMismoResponsable` returns `false` when responsible has no future shifts
- [ ] Current in-progress shift is NOT counted
- [ ] Name normalization via NOMBRE_MAP works: short names in schedule match full names in responsible
- [ ] Night shift crossing midnight: egreso before 06:30 is treated as previous day's `noche`
- [ ] Night shift: next shift after `noche` is `manana` of next calendar day
- [ ] No schedule loaded → `esVencida` behaves exactly as before (4-day rule only)
- [ ] All existing scenarios from parent spec remain passing
- [ ] Row renders with `resp-row--vencida` class + red background when either condition met

---

## Non-Goals

- **No backend changes**: schedule is already loaded client-side via existing API endpoint; no new endpoints needed
- **No UI changes beyond vencida row**: the row background toggle is the only visual impact
- **No "Sin Egreso" or envío button changes**: those behaviors are unaffected
- **No cross-month schedule navigation**: the schedule covers the current month only; previous-month egresos fall through to 4-day rule
- **No past-month schedule caching**: we don't fetch or store schedule data for previous months
- **No performance optimization**: schedule size is bounded (≤ 31 days × 3 slots); linear scan is acceptable
- **No changes to `calcularResponsable`**: shift boundary logic and name mapping remain untouched
