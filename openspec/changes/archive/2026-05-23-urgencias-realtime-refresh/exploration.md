## Exploration: urgencias-realtime-refresh

### Current State

The **Control Urgencias (Control de Novedades)** page is a single-page Flask/Jinja template (`control_errores.html`, ~3244 lines) with a **polling-based real-time refresh** mechanism and **inline cell editing** using a shared floating editor div.

#### Polling Architecture

- **Interval**: 3 seconds (`setInterval(async () => {...}, 3000)`)
- **Endpoint**: `GET /api/control-errores/changes?since={lastUpdate}`
- **Storage**: `app/utils/errores_storage.py` stores data in a flat JSON file (`control_errores.json`) with an `ultima_actualizacion` ISO timestamp updated atomically on every write
- **Comparison**: String comparison of ISO timestamps (`current > since`) in `check_cambios()`
- **On change detected**: Calls `loadErrores()` which re-fetches ALL errors via `GET /api/control-errores` and **completely replaces the table DOM** via `renderFilteredTable()` → `tbody.innerHTML = html`

#### Inline Editing Flow

1. Click on an `editable-cell` → `handleCellClick(td)` → `openEditor(td)`
2. A floating `#global-editor` div (outside the table) is positioned over the cell using `getBoundingClientRect()`
3. Input is a `<textarea>` or a custom `<select>` dropdown
4. Save triggers: Enter key, click outside, dropdown option select, Escape closes without save
5. `saveFromEditor()` → updates `cachedErrores` in-memory → calls `updateBackend(id, field, value)` which:
   - Updates `lastUpdate = new Date().toISOString()` (blocks polling)
   - Sends **fire-and-forget** `fetch(PUT /api/control-errores/{id})` — no await, no error check on response
   - Closes the editor

#### Separate Facturador Editor

- Triggered by a pencil icon button per row
- Opens `#global-editor` as a textarea with yellow background (`#fef9c3`)
- Same pattern: optimistic cache update, `lastUpdate` blocking, fire-and-forget PUT

#### Permission Model

- `window._canWrite` is set server-side based on session permissions (`*` or `control_urgencias:write`)
- Users without write: only `estado` and `observacion_facturador` fields are editable; `observacion` and `factura` show a read-only tooltip
- Users without write: cannot add new rows, delete, or export

#### CRUD Endpoints

| Method | Endpoint | Auth | Behavior |
|--------|----------|------|----------|
| GET | `/api/control-errores/changes?since=` | `control_urgencias` | Returns `{changed, last_update}` |
| GET | `/api/control-errores` | `control_urgencias` | Returns all errors (filtered) |
| POST | `/api/control-errores` | `control_urgencias:write` | Creates new error |
| PUT | `/api/control-errores/<id>` | `control_urgencias` | Field-level permission check in service |
| DELETE | `/api/control-errores/<id>` | `control_urgencias:write` | Deletes error + images folder |

### Affected Areas

- `app/templates/control_errores.html` — Main template with all JS logic (polling, inline editing, rendering, auth)
- `app/routes/control_errores.py` — Backend routes (check_changes, list, create, update, delete)
- `app/services/control_errores_service.py` — Business logic with field-level permission enforcement
- `app/utils/errores_storage.py` — JSON file persistence with atomic writes (`tempfile` + `replace`)
- `tests/services/test_control_errores_service.py` — Unit tests for permission logic
- `tests/services/test_control_errores_integration.py` — Integration tests for PUT endpoint permissions

### Flaws Found

1. **Polling destroys inline editor mid-edit (CRITICAL)** — When polling detects an external change, `loadErrores()` calls `renderFilteredTable()` which sets `tbody.innerHTML = html`, destroying all DOM references. If a user was mid-edit, the floating `#global-editor` becomes orphaned:
   - `currentCell` references a removed DOM element
   - Any pending save would operate on stale data
   - The `lastUpdate` blocking only protects against the current user's own edits, NOT external edits
   - Affects: normal cell edits AND the facturador editor AND new row creation

2. **No conflict detection for concurrent edits (CRITICAL)** — No version field, ETag, or conditional PUT. Two users editing the same cell simultaneously: **last write wins, no merge, no warning**. User A writes value X, user B writes value Y 100ms later — Y silently overwrites X with no notification to user A.

3. **Fire-and-forget PUT with no error handling (HIGH)** — `updateBackend()` sends `fetch(PUT)` without `await` and never checks the response. If the server returns 403 (permission denied), 404 (deleted by another user), or 500 (server error), the user sees a successful save because:
   - `cachedErrores` was optimistically updated
   - Editor was closed
   - The error is silently swallowed
   - Only the next poll (up to 3s later) would correct the cache

4. **Delete race condition (HIGH)** — User A is editing a row, user B deletes it. User A's `updateBackend` sends PUT, server returns "Error no encontrado" (404), but the fire-and-forget never checks this. User A's `cachedErrores` still has the deleted row until next poll.

5. **Entire table re-render on every change (MEDIUM)** — Every poll-triggered change replaces the entire `<tbody>` HTML. This:
   - Destroys and recreates all DOM elements
   - Loses all transient state (tooltips, modal references)
   - Causes visual flicker with large datasets
   - Resets pagination to page 1 (`currentPage = 1` via `applyFilters`)
   - Makes the CPU fan spin with many rows

6. **AddNewRow vulnerability to poll race (MEDIUM)** — `addNewRow()` inserts a `<tr id="new-row">` into the DOM and opens the editor. If polling detects a change during this process, `loadErrores()` destroys the new row. The `isAdding` flag remains `true` but the row is gone.

7. **lastUpdate blocking uses client clock (LOW-MEDIUM)** — The `lastUpdate` value is set to `new Date().toISOString()` which uses the client's clock. If the client clock is skewed, the comparison with the server's `ultima_actualizacion` could behave incorrectly (e.g., blocking changes that should be detected, or vice versa).

8. **No loading/error state indicators (LOW)** — If the polling fetch fails (network error), it silently logs to console. The user never sees connection issues. The stale cached data continues to display.

9. **Pagination reset on external change (LOW)** — `loadErrores()` calls `applyFilters()` internally via chain, resetting `currentPage = 1`. A user browsing page 5 gets thrown back to page 1 whenever someone else edits a row.

### Improvement Opportunities

1. **Replace polling with WebSocket or SSE (High effort, High impact)** — Server-sent events or WebSocket would provide real-time push without the 3-second latency and eliminate the double-request pattern.
2. **Guard against poll re-render during active edit (Low effort, High impact)** — Check `currentEditId` before calling `loadErrores()` in the poll handler. If editing, skip the remote update or defer it.
3. **Add optimistic locking with version field (Medium effort, High impact)** — Add a `version` field to each error, increment on every write, and reject stale PUTs. Notify the user of the conflict.
4. **Use `await` + error handling in `updateBackend` (Low effort, High impact)** — Check PUT response, revert cache on failure, show toast-style error instead of silent swallow.
5. **Partial/diff-based table update (Medium effort, Medium impact)** — Instead of replacing the entire `<tbody>`, upsert only changed rows. Use DOM diffing or per-row IDs.
6. **lastUpdate from server (Low effort, Low impact)** — After a successful PUT, use the response's timestamp instead of the client clock for `lastUpdate`.

### Approaches

1. **Minimal fix: poll guard + fetch error handling**
   - Guard poll handler: `if (currentEditId) return;` before calling `loadErrores()`
   - Make `updateBackend` async with proper error handling (revert cache on failure)
   - Check PUT response for 404/403 and revert optimistic update
   - Effort: Low

2. **Medium: Version-based optimistic locking + partial re-render**
   - Add `version` field to each error (integer, starts at 1, incremented on save)
   - Pass version in PUT, server rejects if mismatch (409 Conflict)
   - On 409: show toast "Edited by another user", reload data, restore editor with server value
   - Track row renderings by `row-id` so poll can update only changed rows
   - Effort: Medium

3. **Full upgrade: WebSocket push + row-level updates**
   - Replace polling with WebSocket or SSE via Flask-SocketIO or plain EventSource
   - Server pushes individual change events (row updated/created/deleted)
   - Client updates only affected rows in the DOM
   - Abandon the `lastUpdate` blocking pattern entirely
   - Effort: High

### Recommendation

**Start with Approach 1 (Minimal fix)** — it solves the most critical flaw (editor destruction during poll) and the silent error swallowing with very low risk. This is a quick win that prevents data loss and user confusion.

Then if concurrent editing is a real problem in practice (two people in the same page simultaneously), move to **Approach 2** — version-based locking is the standard web pattern for "last write loses" and integrates cleanly with the existing REST endpoints.

Approach 3 (WebSocket) would be architectural overkill unless there are explicit requirements for sub-second sync or very high concurrent usage. The 3-second poll is acceptable for this use case.

### Risks

- Fixing the poll guard (`if (currentEditId) return;`) means external changes are delayed until the user finishes their edit. This is acceptable UX — better to delay the update than lose an edit.
- Adding version-based locking changes the API contract — all existing clients must be updated to send `version`. Old tabs without the version field would get 409 until refreshed.
- The JSON file storage is inherently not concurrent-safe at the server level. Two simultaneous PUT requests could theoretically interleave reads/writes. The atomic write helps but doesn't provide row-level locking.

### Ready for Proposal

Yes — the flaws are well-understood, and Approach 1 is a low-risk, high-value improvement that should be proposed as the first step.
