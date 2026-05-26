# Tasks: Validador Column in Control de Novedades (Urgencias)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~80–120 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Storage + Service + Template + Tests | PR 1 | Single PR — all changes are interdependent declarations |

## Phase 1: Storage Layer

- [x] 1.1 Add `validador: str = ""` param to `crear_error()` in `app/utils/errores_storage.py:112`
- [x] 1.2 Store `"validador": validador` key in the error dict inside `crear_error()`
- [x] 1.3 Verify `actualizar_error()` explicitly does NOT accept/pass validador (no changes needed — confirmed)

## Phase 2: Service Layer

- [x] 2.1 In `add_error()` in `app/services/control_errores_service.py:84`, compose `validador = f"{session.get('primer_nombre', '')} {session.get('apellido_1', '')}".strip()`
- [x] 2.2 Pass `validador=validador` keyword arg to `crear_error()` call (ignore client payload — session always wins)

## Phase 3: Template (Jinja2 + JS)

- [x] 3.1 Add `<th>Validador</th>` as first `<th>` in the `<thead>` (line 93–101)
- [x] 3.2 In `renderTable()`: add read-only `<td class="fecha-creado">${escapeHtml(e.validador || '-')}</td>` as first cell (before factura)
- [x] 3.3 In `renderFilteredTable()`: same cell as first `<td>` in the row template
- [x] 3.4 In `addNewRow()`: add `<td class="fecha-creado">${currentUserName || '-'}</td>` as first cell
- [x] 3.5 Update all 4 `colspan="7"` → `"8"` (lines 103, 375, 395, 1252)

## Phase 4: Testing (RED-GREEN-REFACTOR)

- [x] 4.1 **RED**: Write test `test_crear_error_stores_validador` — patch `_escribir_datos`, call `crear_error(validador="Juan Pérez")`, assert dict has `"validador": "Juan Pérez"`
- [x] 4.2 **GREEN**: Implement storage change; test passes
- [x] 4.3 **RED**: Write test `test_add_error_composes_validador_from_session` — mock session keys, assert `crear_error` called with expected validador
- [x] 4.4 **GREEN**: Implement service change; test passes
- [x] 4.5 **RED**: Write test `test_add_error_ignores_client_validador` — post with `{"validador": "hacker"}`, assert stored validador is from session, not payload
- [x] 4.6 **GREEN**: Verify the service already ignores client validador (it reads session only); test passes
- [x] 4.7 **RED**: Write integration test `test_post_creates_with_validador` — `app_client` with `session_transaction()`, POST valid payload, assert response includes `validador`
- [x] 4.8 **GREEN**: Integration test passes against existing code
- [x] 4.9 **REFACTOR**: Clean up test setup, ensure existing tests still pass

## Implementation Order

Storage → Service → Template → Tests. Storage has no dependencies on other layers. Service depends on storage signature. Template is independent from storage/service (can be verified visually). Tests verify the full chain.
