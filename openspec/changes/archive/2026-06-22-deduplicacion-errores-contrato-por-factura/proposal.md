# Proposal: En estas reglas de contratos la factura sale mas de una vez el error por factura

## Intent

Contract validation detectors currently emit one error per **row** where the contract doesn't match. An invoice with 12 rows and the same contract violation produces 12 identical errors. Since an invoice has exactly one contract, errors MUST appear once per invoice — not once per row.

## Scope

### In Scope
- Add invoice-level dedup to `app/services/urgencias/ide_contrato_urgencias.py`
- Add invoice-level dedup to `app/services/odontologia/ide_contrato.py`

### Out of Scope
- `app/services/urgencias/centro_costo_urgencias.py` — centrocosto errors can legitimately differ per row (different codes, different valid cost centers). Needs separate analysis.
- Any other detector not related to contract validation.

## Capabilities

### New Capabilities
- `contrato-validation-dedup`: Contract validation errors SHALL be reported once per invoice, not once per row. Applies to urgencias and odontología detectors.

### Modified Capabilities
None — no existing spec defines per-row vs per-invoice reporting granularity.

## Approach

Follow the established pattern used by 4 existing detectors (`codigo_entidad.py`, `tipo_documento_edad.py`, `tipo_usuario.py`, `ide_contrato_reverse.py`):

1. Initialize `facturas_procesadas: set[str] = set()` before the main row loop.
2. At loop start, skip if `factura_str in facturas_procesadas: continue`.
3. After each `problemas_ide_contrato.append()` call, add `facturas_procesadas.add(factura_str)`.

This is a ~6-line addition per detector. No new abstractions or data structures needed.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/urgencias/ide_contrato_urgencias.py` | Modified | Add set dedup to loop body (multiple append sites) |
| `app/services/odontologia/ide_contrato.py` | Modified | Add set dedup to single append site |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| First-error bias: only the first failing rule per invoice is reported | Low | Acceptable — an invoice has one contract, so multiple rules can't apply simultaneously to the same invoice. |
| False dedup if `factura_str` is empty/normalized differently | Low | `normalize_invoice()` already handles normalization consistently. |

## Rollback Plan

Revert the set initialization, `in` check, and `add()` call from each affected detector. No config or schema changes to revert.

## Dependencies

None.

## Success Criteria

- [ ] Given an invoice with 12 rows all violating the same contract rule, exactly 1 error appears in the output (not 12).
- [ ] Given an invoice with no contract violations across any row, 0 errors appear (no regression).
- [ ] All existing tests pass without modification.
