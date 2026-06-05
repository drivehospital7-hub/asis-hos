# Design: CAP exception — ESS118 / EPSS41 in CUPS sin contrato

## Technical Approach

Extend `detect_cups_sin_contrato()` internally — same pattern as the existing urgencias exception (parentesis-responsable-cierra). Add a single batch pre-load query for `nota_hoja id IN (2, 3)` and two branches in the row loop that check `factura.startswith("CAP")` + `cod_entidad` to redirect validation to the appropriate capitado set. No signature changes, no new files.

## Architecture Decisions

### Decision: Single batch query for nota_hoja 2 & 3

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Two separate queries | Simpler code but 2x round trips | ❌ Descartado |
| Single `IN (2, 3)` query + dict split | One round trip, slight complexity | ✅ Elegido |

Rationale: Following the existing `nota1_cups` pre-load pattern, but merging both nota_hoja IDs into one query. Results are split into `nota_cap_cups: dict[int, set[str]]` keyed by `id_nota_hoja`. This keeps DB round trips at 4 total (same as current design +1).

### Decision: Branch placement in row loop

Insert AFTER the urgencias exception (line 224) and BEFORE `entidades_con_datos` (line 227). Rationale:
- Urgencias takes priority (it's a person-based exception, more specific)
- CAP check is factura-based; if urgencias already matched, no need to evaluate CAP
- Placed before `entidades_con_datos` so CAP entities that lack standard contractual data still get validated against their capitado set

### Decision: Fails-closed on empty nota_cap sets

If `nota_cap_cups[2]` or `nota_cap_cups[3]` is empty (no procedimientos loaded for that nota_hoja), the `codigo in nota_cap_cups[N]` check fails → no continue → falls through to standard validation → error. Safe default.

## Data Flow

```
Row loop (existing flow with CAP additions):
  │
  ├─ (existing: skip null factura, skip farmacia, skip PYM, etc.)
  │
  ├─ urgencias exception (existing, line 215–224)
  │   └─ matched → continue
  │
  ├─ CAP exception (NEW)
  │   ├─ factura empieza con "CAP" + cod_entidad == "ESS118"?
  │   │   ├─ codigo in nota_cap_cups[3] → continue
  │   │   └─ otherwise → cae a validación normal
  │   └─ factura empieza con "CAP" + cod_entidad == "EPSS41"?
  │       ├─ codigo in nota_cap_cups[2] → continue
  │       └─ otherwise → cae a validación normal
  │
  ├─ entidades_con_datos (existing)
  ├─ pares_validos check (existing)
  └─ error generation (existing)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/transversales/procedimiento_contratado.py` | Modify | +18 lines: batch pre-load (6 lines), row-loop branch (12 lines) after urgencias, before `entidades_con_datos` |
| `tests/services/test_detect_cups_sin_contrato.py` | Modify | Extend `_make_mock_session` helper (backward-compatible), add 6 new tests |

## Interfaces / Contracts

**Sin cambios**: `detect_cups_sin_contrato(data_sheet, indices) → list[dict]` signature unchanged.

New internal structures in `procedimiento_contratado.py`:

```python
# Pre-load (inside try block, after nota1_cups)
cap_results = (
    session.query(NotasTecnicas.id_nota_hoja, Procedimiento.cups)
    .join(Procedimiento, Procedimiento.id == NotasTecnicas.id_procedimiento)
    .filter(NotasTecnicas.id_nota_hoja.in_([2, 3]))
    .all()
)
nota_cap_cups: dict[int, set[str]] = {2: set(), 3: set()}
for nt_id, proc in cap_results:
    nota_cap_cups[nt_id].add(proc.cups.strip().upper())
```

```python
# Row-loop branch (after urgencias, before entidades_con_datos)
numero_raw = data_sheet.cell(row=row, column=num_fact_idx + 1).value
factura_num = normalize_invoice(numero_raw)
if factura_num and factura_num.upper().startswith("CAP"):
    if cod_entidad == "ESS118" and codigo in nota_cap_cups[3]:
        continue
    if cod_entidad == "EPSS41" and codigo in nota_cap_cups[2]:
        continue
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_make_mock_session` helper | Extend with optional `cap_cups: dict[int, list[str]]` param (default `{}`), add 4th `.all()` side_effect entry — backward compatible, all 28 existing tests pass unchanged |
| Unit | CAP + ESS118 + CUPS in nota3 | Sin error |
| Unit | CAP + EPSS41 + CUPS in nota2 | Sin error |
| Unit | CAP + ESS118 + CUPS NOT in nota3 | Error |
| Unit | CAP + EPSS41 + CUPS NOT in nota2 | Error |
| Unit | CAP + ESS118 + nota3 empty | Error (fails closed) |
| Unit | No-CAP factura + ESS118 | Error normal (no excepción aplica) |

Test helper change:
```python
def _make_mock_session(
    pairs: list[tuple[str, str]],
    eps_names: dict[str, str],
    nota1_cups: list[str] | None = None,
    cap_cups: dict[int, list[str]] | None = None,  # NEW
) -> MagicMock:
```
The `cap_cups` dict is flattened into `[(id_nota_hoja, cups), ...]` tuples and appended as the 4th `.all()` return value.

## Migration / Rollout

No migration required. Rollback: revert lines in `procedimiento_contratado.py` and test file.

## Open Questions

- [ ] None.
