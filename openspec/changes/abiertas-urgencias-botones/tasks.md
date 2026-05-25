# Tasks: Abiertas Urgencias — Port legacy JS to React

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~300 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Foundation

- [x] 1.1 Create `frontend/src/pages/abiertas-urgencias/constants.ts` — `NOMBRE_MAP` (short→full), `TOAST_DURATION`, column label constants, header detection strings
- [x] 1.2 Create `frontend/src/pages/abiertas-urgencias/utils.ts` — export signatures for `parseScheduleText`, `autoDetectColumns`, `calcularResponsable`, `copiarHorario`, `copiarResultados`, `escapeHtml`

## Phase 2: TDD — Pure Functions (RED→GREEN)

- [x] 2.1 RED: Write failing vitest tests for `parseScheduleText` — multi-line quoted fields, missing header, empty input, happy path (maps to spec scenarios)
- [x] 2.2 GREEN: Implement `parseScheduleText` — normalize line endings, join quoted fields, find DIA/DÍA header, parse tab-separated rows into `ScheduleDay[]`
- [x] 2.3 RED: Write failing vitest tests for `autoDetectColumns` — header label detection, pattern fallback (date/FEV), FEV standalone prefix concatenation
- [x] 2.4 GREEN: Implement `autoDetectColumns` — try header labels first, fall back to value patterns, detect FEV standalone prefix → concatenate with next column
- [x] 2.5 RED: Write failing vitest tests for `calcularResponsable` — night crossover (egreso<06:30→previous day noche), 30-min shift bounds (06:30/12:30/18:30), sin egreso, each shift
- [x] 2.6 GREEN: Implement `calcularResponsable` — determine shift by egreso time, map via `NOMBRE_MAP`, cross midnight lookup

## Phase 3: Schedule CRUD Wiring

- [x] 3.1 Wire `useEffect` on mount — `GET /abiertas-urgencias/api/schedule` → `schedule` state + `scheduleStatus` ("loading"|"loaded"|"empty")
- [x] 3.2 Wire Cargar/Editar toggle — `showParseCard` state, textarea binding for `scheduleText`, "Parsear y Guardar" calls `parseScheduleText` + `POST /api/schedule`
- [x] 3.3 Wire delete — `confirm()` dialog → `DELETE /api/schedule`, clear state on success
- [x] 3.4 Render schedule status bar + 4-column table (Día/07:00-13:00/13:00-19:00/19:00-07:00) + clipboard via `copiarHorario` with fallback

## Phase 4: Responsible Assignment Wiring

- [x] 4.1 Wire facturas textarea + "Procesar y Asignar Responsable" — calls `autoDetectColumns` + `calcularResponsable` per row → `results[]` state
- [x] 4.2 Pre-load `GET /api/control-errores` → `envioExistentes` (Ref<Set<string>>) for duplicate detection
- [x] 4.3 Render 9-column results table — fechaCrea, fechaEgreso, factura, área, paciente, estado, hcPendiente, responsable, envío button; vencida CSS class if >4 calendar days & estado "Abierta"
- [x] 4.4 Wire per-row Envío a Control — 3-state button (+ / ⚠+ / ✓ Enviado), confirm dialog for new/duplicate, `POST /api/control-errores`, update `envioEnviadas` ref

## Phase 5: Cross-cutting UX

- [x] 5.1 Add toast overlay — `useState<{message:string}>`, `setTimeout` auto-dismiss at `TOAST_DURATION`, render top-center absolute positioned div
- [x] 5.2 Add auth gating — disable all mutation actions (Parsear y Guardar, Editar, Eliminar, Envío a Control) when `can_write` is false, show tooltip "Iniciá sesión para modificar"
