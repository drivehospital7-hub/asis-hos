# Design: Además-de-4-días-shifts

## Technical Approach

Pure function `masDeDosTurnosMismoResponsable()` in `utils.ts` walks forward through schedule slots from the egreso's own shift (inclusive) up to the shift *before* the current one, counting how many times the responsable appears. Modified `esVencida()` in `page.tsx` calls it when schedule is loaded — if ≥2 shifts match, the row is vencida. No schedule → 4-day fallback unchanged.

## Architecture Decisions

### Decision: Keep `esVencida` in page.tsx

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Move to utils.ts + export | Consistent location, directly testable | ❌ Bigger diff, changes component contract |
| Keep in page.tsx, delegate to new utils function | Minimal diff, pure logic stays testable | ✅ Follows proposal |

The shift-checking logic is a pure function in `utils.ts` (testable alongside `calcularResponsable`). `esVencida` stays as a thin adapter in page.tsx.

### Decision: Flat shift-index ordering for counting

Schedule days map to a linear index: `day * 3 + slot` (0=mañana, 1=tarde, 2=noche). Egreso shift and "now" shift are each resolved to an index, and we count schedule entries strictly between them. This avoids nested conditional logic for day boundaries and night-shift cross-midnight.

### Decision: Reverse NOMBRE_MAP for name matching

`responsable` stores the *full* name (e.g., "CARLOS OMAR"). Schedule stores *short* names ("CARLOS"). We build `reverseNOMBRE_MAP[fullName] → shortName` once and compare schedule slots against `shortName || responsable` (fallback for unmapped names).

## Data Flow

```
esVencida(estado, fechaEgreso, responsable, schedule)
  │
  ├── estado !== "Abierta" → false
  │
  ├── schedule empty → 4-day diff check (unchanged)
  │
  └── schedule exists → masDeDosTurnosMismoResponsable(egresoStr, responsable, schedule)
        │
        ├── egreso month ≠ current month → false (fallback to 4-day)
        │
        └── Iterate schedule days:
              For each shift in [manana→tarde→noche]:
                index = day*3 + slot
                skip if index < egresoShiftIndex
                skip if index ≥ nowShiftIndex
                count++ if slot matches responsable
              return count ≥ 2
```

## Key Functions

### `masDeDosTurnosMismoResponsable(fechaEgreso: string, responsable: string, schedule: ScheduleDay[], now?: Date): boolean`

**Inputs**: Egreso datetime string, full responsible name, schedule array, optional now (for test injection).

**Algorithm** (pseudocode):
```
function masDeDosTurnosMismoResponsable(egresoStr, responsable, schedule, now = new Date()):
  egreso = parseDate(egresoStr)           // private, preserves time
  if (!egreso || egreso.getMonth() !== now.getMonth() ||
      egreso.getFullYear() !== now.getFullYear()) return false

  // Resolve egreso shift index
  egresoSlot = slotIndex(egreso.getHours() + egreso.getMinutes()/60)
  egresoDay = egreso.getDate()

  // Night shift correction: 00:00-06:29 belongs to previous day's noche
  hourMin = egreso.getHours() + egreso.getMinutes()/60
  if (hourMin < 6.5):
    egresoSlot = 2; egresoDay -= 1   // noche of prev day
  egresoIdx = egresoDay * 3 + egresoSlot

  // Resolve "now" shift index
  nowSlot = slotIndex(now.getHours() + now.getMinutes()/60)
  nowDay = now.getDate()
  if (now.getHours() + now.getMinutes()/60 < 6.5):
    nowSlot = 2; nowDay -= 1
  nowIdx = nowDay * 3 + nowSlot

  // Build reverse name map
  revMap = Object.fromEntries(
    Object.entries(NOMBRE_MAP).map(([k, v]) => [v, k])
  )
  shortName = revMap[responsable] || responsable

  // Count matched shifts strictly between egresoIdx and nowIdx
  count = 0
  for (day of schedule):
    for ([slotName, slotIdx] of [["manana",0], ["tarde",1], ["noche",2]]):
      shiftIdx = day.dia * 3 + slotIdx
      if (shiftIdx < egresoIdx) continue
      if (shiftIdx >= nowIdx) continue  // current shift in progress, skip
      slotValue = (day[slotName] || "").toUpperCase().trim()
      if (slotValue === shortName || slotValue === responsable):
        count++
  return count >= 2
```

### Modified `esVencida`
```typescript
function esVencida(
  estado: string,
  fechaEgreso: string,
  responsable: string,
  schedule: ScheduleDay[] | null,
): boolean {
  if (estado !== "Abierta") return false;
  if (schedule && schedule.length > 0) {
    if (masDeDosTurnosMismoResponsable(fechaEgreso, responsable, schedule)) {
      return true;
    }
  }
  // Fallback: >4 calendar days (unchanged)
  const egreso = parseFecha(fechaEgreso);
  if (!egreso) return false;
  const hoy = new Date();
  const hoyInicio = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  return Math.floor((hoyInicio.getTime() - egreso.getTime()) / 86400000) > 4;
}
```

### Private helpers in utils.ts
- `slotIndex(hourMin: number): 0|1|2` — reuses the 06:30/12:30/18:30 boundaries
- `buildReverseNombreMap(): Record<string, string>` — builds once inside the main function

## Edge Cases

| Case | Handling |
|------|----------|
| No schedule loaded | `schedule` is null/empty → skip shift check, 4-day only |
| Egreso last month | Month mismatch → return false, 4-day fallback applies |
| Night shift egreso (18:30-06:29) | Egreso before 06:30 → slot=2, day-1. Next shift is this day's mañana |
| Night shift now (after midnight) | Now before 06:30 → current shift is previous day's noche, exclude from count |
| Responsable has no future shifts | No schedule slots match → count=0 < 2 |
| Name not in NOMBRE_MAP | `revMap[resp]` is undefined → fallback to `resp` as short name |
| Partial day (current shift in progress) | `nowIdx` excludes current shift from counting |
| Egreso today, only hours ago | `egresoIdx` and `nowIdx` may be same → no slots counted → false |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/abiertas-urgencias/utils.ts` | Modify | Add `masDeDosTurnosMismoResponsable()` and private helpers (`slotIndex`) |
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modify | Import new function, update `esVencida` signature and body, update call site (line 647) |
| `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts` | Modify | Add test suite for `masDeDosTurnosMismoResponsable` |

### No new files needed — single function addition to existing module structure.

## Interfaces / Contracts

No new types. Existing interfaces reused:
- `ScheduleDay` (imported from utils.ts)
- `FacturaResult.responsable` (string — the normalized full name)

New export:
```typescript
export function masDeDosTurnosMismoResponsable(
  fechaEgreso: string,
  responsable: string,
  schedule: ScheduleDay[],
  now?: Date,                  // for test injection
): boolean;
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `masDeDosTurnosMismoResponsable` | Vitest, same test file, mock schedule with known data, inject `now` via optional param |
| Unit | Modified `esVencida` | Test call site in page.tsx? No — keep it simple: test the pure function, `esVencida` is thin delegation |
| Regression | All existing utils tests | Must pass unchanged |

### Test cases for `masDeDosTurnosMismoResponsable`
1. Egreso in day 1 `manana` (=CARLOS), same day `tarde` also CARLOS → true (egreso shift counts as 1, tarde as 2)
2. Egreso in day 1 `manana` (=CARLOS), no other CARLOS shifts → false (only 1, egreso shift)
3. Egreso in day 1 `manana` (=CARLOS), only day 2 `manana` CARLOS → true (egreso shift + day 2 = 2)
4. No schedule → N/A (esVencida handles this, function itself expects ScheduleDay[])
5. Egreso last month → false
6. Egreso same day, all shifts CARLOS, today still in egreso shift (manana in progress) → false (current shift not counted)
7. Night shift egreso (day 5 at 03:00 → day 4 noche), day 4 noche=CARLOS, day 5 manana=CARLOS → true
8. Name via NOMBRE_MAP (responsable="CARLOS OMAR", schedule has "CARLOS") → matches (egreso shift counts)
9. Name not in NOMBRE_MAP (responsable="PEPE", schedule has "PEPE") → matches

## Open Questions

None. The design is complete — all inputs, outputs, and edge cases are specified.
