# Contrato Validation Dedup — Factura-Level Deduplication

## Purpose

Contract validation detectors (`ide_contrato` odontología, `ide_contrato_urgencias`) currently emit one error per row where the contract doesn't match. Since an invoice has exactly one contract, errors MUST appear once per invoice — not once per row. This spec defines deduplication behavior at the invoice level without changing detection logic for other error types.

## Requirements

### R1: Invoice-Level Dedup — Contract Errors

The system MUST emit at most one contract-validation error per invoice, regardless of how many rows violate the same contract rule. Subsequent rows of the same invoice SHALL be skipped for contract validation error reporting. The invoice identifier SHALL be the normalized value from `normalize_invoice()` — consistent across all detectors.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Happy path — same invoice, 12 rows | an invoice with 12 rows all violating the same contract rule | `detect_all()` runs | exactly 1 contract error emitted for that invoice |
| Single row | an invoice with 1 row violating the contract | `detect_all()` runs | exactly 1 contract error emitted |
| No violations | an invoice with all rows having correct contract | `detect_all()` runs | 0 contract errors emitted for that invoice |
| Mixed invoices — 2 invoices, 24 rows | 2 invoices, each with 12 rows violating the contract | `detect_all()` runs | exactly 2 contract errors emitted (1 per invoice) |

### R2: Different Error Types — No Cross-Contamination

Contract error dedup MUST NOT suppress other error types (e.g., decimal, duplicate, centrocosto) on the same invoice. Only contract-validation errors are deduplicated per invoice. Non-contract errors SHALL continue to report per row.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Contract + other errors on same invoice | an invoice has 12 rows with a contract violation AND 1 row with a decimal error | `detect_all()` runs | 1 contract error + 1 decimal error = 2 total errors |
| Contract + duplicate errors | an invoice has 4 contract violations AND a row-level duplicate | `detect_all()` runs | 1 contract error + 1 duplicate error (or more per existing duplicate logic) |

### R3: Empty / No-Op Invoice

If `normalize_invoice()` produces an empty string for a given row, the system MUST skip dedup for that row (no error emitted, no regression from current behavior).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Empty invoice | a row has an invoice number that normalizes to empty string | detector processes the row | no contract error emitted; no crash |
| Missing invoice | a row has no invoice number/None | detector processes the row | no contract error emitted; no error emitted for that row |

### R4: First Error Reported — Per Invoice

When multiple contract-validation rules could apply to the same invoice (e.g., both `ide_contrato_urgencias` and a future rule), the first detected contract error per invoice SHALL be the one reported. This is an acceptable trade-off — an invoice has one contract, so multiple distinct rules cannot apply simultaneously to the same contract.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| First rule fires | first row triggers rule A, subsequent rows trigger rule A again | loop processes all rows | rule A error emitted once (rule A error) |
| Only one active | any invoice | detection runs | at most one contract-validation entry per invoice |

## Non-Functional Requirements

- **Backward compatibility**: Detection logic for non-contract errors SHALL remain unchanged. All existing tests SHALL pass without modification.
- **Performance**: Dedup SHALL use a `set[str]` of normalized invoice numbers — O(1) lookup, negligible memory overhead.
