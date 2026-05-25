# Design: Abiertas Urgencias — Port legacy JS to React

## Technical Approach

Single-page component (`page.tsx`) with `useState`/`useEffect` — identical pattern to `OdontologiaPage`. Extract three pure TS functions into `utils.ts`, constants (`NOMBRE_MAP`, labels) into `constants.ts`. All API calls inline with try/catch. Backend untouched.

Decision: **no sub-components** — the table renders are small enough for inline JSX. If the file exceeds ~400 lines during implementation, extract `ScheduleTable` and `ResultsTable` as leaf components at that point. The design keeps it modular in one file to match project conventions.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|---|---|---|---|
| State vs ref for `envioExistentes`/`envioEnviadas` | `useRef<Set<string>>` | global var (legacy), useState | Set mutations don't need re-renders; ref avoids unnecessary renders on preload |
| Toast mechanism | `useState` + `setTimeout` | shadcn sonner, react-hot-toast | Zero deps, matches legacy 2.5s behavior exactly, trivial to extract later |
| Vencida calculation | Inline in render (computed) | utility function | Only used for CSS class; trivial date math; keep it with the component |
| Clipboard fallback | `navigator.clipboard` with `document.execCommand` fallback | Always use clipboard API | Legacy code already handles Safari/old browser edge case; keep the same fallback |

## Data Flow

```
Mount ──► useEffect: GET /api/schedule ──► schedule state ──► ScheduleTable JSX
                                              │
User pastes schedule text ──► parseScheduleText() ──► POST /api/schedule
                                              │
User pastes facturas ──► autoDetectColumns() ──► calcularResponsable() ──► results[]
                              │                     │                          │
                         FETCH /api/control-errores ──► _envioExistentes ref ──► ResultsTable
                                                                                    │
User clicks Envío ──► confirm() ──► POST /api/control-errores ──► _envioEnviadas ref
```

## Component Architecture

```
AbiertasUrgenciasPage (page.tsx)
├── Breadcrumbs, PageTitle (existing components)
├── AsignarCard (collapsible)
│   ├── textarea │   └── Button "Procesar y Asignar Responsable"
├── ResultsSection (conditional)
│   ├── table with 9 columns │   ├── per-row Envío button (3-state) │   └── Button "Copiar a Excel"
├── ScheduleCard (collapsible)
│   ├── status bar │   ├── 4-column table │   ├── Button "CopiarHorario" │   ├── Button "Modificar/Cargar" │   └── Button "Eliminar"
├── ParseCard (collapsible, toggled by Modificar/Cargar)
│   ├── textarea │   └── Button "Parsear y Guardar"
└── Toast overlay
```

### State Shape

```typescript
// Page state
schedule: ScheduleDay[] | null
scheduleStatus: "loading" | "loaded" | "empty"
scheduleText: string          // textarea binding
showParseCard: boolean        // collapsible toggle
results: FacturaResult[] | null
facturasText: string          // textarea binding
showRespCard: boolean         // collapsible toggle
toast: { message: string } | null
envioExistentes: Ref<Set<string>>   // preloaded duplicates
envioEnviadas: Ref<Set<string>>      // sent this session

// From props
can_write: boolean

// Types
interface ScheduleDay { dia: number; manana: string; tarde: string; noche: string }
interface FacturaResult {
  fechaCrea: string; fechaEgreso: string; factura: string;
  estado: string; responsable: string; area: string;
  paciente: string; hcPendiente: string; _enviada?: boolean
}
```

## Three Pure Utility Functions

All in `utils.ts` — zero side effects, no DOM access, fully testable.

```typescript
// Parse pasted schedule TSV text into structured day array
function parseScheduleText(text: string): ScheduleDay[] | null

// Auto-detect column indices from header labels or first-row value patterns
function autoDetectColumns(
  headers: string[],
  primeraFila: string[]
): { cols: ColumnIndexes; foundLabels: Record<number, string> }

// Determine shift responsible using 30-min reception rule + night crossover
function calcularResponsable(
  fechaCreaStr: string,
  fechaEgresoStr: string,
  cronograma: ScheduleDay[]
): string
```

Business rules encoded in `calcularResponsable`:
- **Night crossover**: if egreso hour < 06:30 → lookup `noche` of previous day
- **30-min reception**: mañana 06:30–12:29, tarde 12:30–18:29, noche 18:30–06:29
- **FEV prefix**: if factura column has standalone "FEV" prefix, concatenate with next column's digits
- **Vencida**: `>4 calendar days` (not 96 hours) — computed in component via `Math.floor(dateDiff / 86400000)`

## File Change Plan

| File | Action | Description |
|---|---|---|
| `frontend/src/pages/abiertas-urgencias/utils.ts` | Create | Pure functions: `parseScheduleText`, `autoDetectColumns`, `calcularResponsable`, `copiarHorario`, `copiarResultados`, `escapeHtml` |
| `frontend/src/pages/abiertas-urgencias/constants.ts` | Create | `NOMBRE_MAP`, `TOAST_DURATION`, column label constants, header strings |
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modify | Wire all handlers, add state, API calls, rendering logic (~147 → ~400 lines) |
| `frontend/src/pages/abiertas-urgencias/main.tsx` | Unchanged | Already passes `can_write` prop |
| `app/templates/abiertas_urgencias.html` | Unchanged | Keep until React is validated in production |
| `app/routes/abiertas_urgencias.py` | Unchanged | Endpoints work as-is |
| `app/services/abiertas_urgencias_service.py` | Unchanged | Service layer works as-is |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit: utils | `parseScheduleText` — multi-line quoted fields, missing header, empty input | Jest/Vitest with `describe`/`it`. Pure function → no mocking needed |
| Unit: utils | `autoDetectColumns` — header detection, pattern fallback, FEV standalone prefix | Same file, pure function tests |
| Unit: utils | `calcularResponsable` — night crossover, 30-min boundary, sin egreso, each shift | Multiple `it` blocks covering edge cases |
| Integration | Full flow: mount → load schedule → parse → POST → render | pytest + Flask client (backend already tested). Frontend integration handled by manual verification with real data per specs |
| E2E | Manual: paste real schedule export, verify table matches legacy output | Run both React and legacy template side-by-side with same data |

No migration required — backend is unchanged, legacy template remains deployed.

## Open Questions

- None — all decisions resolved by reading the full legacy JS and existing React patterns.

## Delivery Risk Forecast

Decision needed before apply: No
Chained PRs recommended: No (~300 lines delta, well under 400-line budget)
400-line budget risk: Low
