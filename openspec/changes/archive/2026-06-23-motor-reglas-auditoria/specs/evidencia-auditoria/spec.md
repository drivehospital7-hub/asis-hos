# Evidencia de Auditoría — Immutable Evaluation Snapshot

## Purpose

Capture an immutable, per-evaluation record of every rule execution: which rule, which version, what input data, which conditions in the tree evaluated to what result. Enables full audit traceability — every detection can be traced back to the exact rule, version, and data that produced it.

---

## Requirements

### R1: Per-Evaluation Capture

For every rule evaluated against a row, the Evidence Collector MUST record: rule ID, rule version, row identifier (factura), domain, timestamp, condition tree evaluation trace (per-node: operator, operands, result), final outcome (MATCH/NO_MATCH/ERROR), and the rule's parameter configuration used.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| MATCH capture | rule R1 v3 matches row with factura="F001" | evidence collected | record contains: rule=R1, version=3, factura="F001", tree trace with per-node results, outcome=MATCH |
| NO_MATCH capture | rule R2 v1 does not match row | evidence collected | record contains outcome=NO_MATCH and full tree trace |
| ERROR capture | rule R3 has unknown operator | evidence collected | record contains outcome=ERROR and error message |
| Batch scope | 50 rows × 5 rules processed | evidence batch insert | 250 evidence records persisted |

### R2: Immutability Guarantee

Once persisted, an evidence record MUST NEVER be modified. Any attempt to UPDATE or DELETE an evidence row SHALL be rejected at the data layer. No application code path SHALL mutate existing evidence.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Insert only | evidence table with 100 records | processing complete | no UPDATE or DELETE operations executed |
| Direct SQL attempt | evidence record with EVID=42 | `UPDATE evidencias SET ...` | rejected (application layer or DB constraint) |
| Archival, not deletion | old evidence needs cleanup | archive process runs | records moved to archive table, never deleted |

### R3: Query and Retrieval

The evidence repository MUST support querying by: rule ID, version, domain, factura, and timestamp range. Querying MUST NOT require loading the full evaluation log into memory — pagination SHALL be supported.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| By rule | evidence with 500 records for rule R1 | query evidencias WHERE rule_id=R1 | all 500 records returned, paginated |
| By factura | evidence for factura="F001" across 3 rules | query evidencias WHERE factura="F001" | 3 records returned (one per rule evaluated) |
| Time range | evidence from 2026-06-01 to 2026-06-07 | query with timestamp BETWEEN | only records in range returned |
| No results | query for factura="NONEXISTENT" | query | empty result set, not an error |

### R4: Relationship to Audit Results

Each audit result (problema detected) MUST reference its source evidence via `evidencia_id`. The system SHALL provide a join path: "find all problems detected by rule R1 v3 → trace back to evidence → inspect tree trace." No detected problem SHALL exist without a corresponding evidence record.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Problem → evidence link | rule R1 detects problema P1 on factura="F001" | result stored | `resultado_auditoria.evidencia_id` references the evidence record |
| Full trace | problema P1, click "audit trail" | query evidence by result's evidencia_id | full condition tree trace for P1 returned |
| Orphan guard | a problem is somehow stored without evidencia_id | integrity check runs | flagged as data integrity violation |

---

## Acceptance Criteria

- [ ] Every rule evaluation produces exactly one evidence record (per rule, per row, per param config)
- [ ] Evidence records are insert-only: no UPDATE or DELETE in application code
- [ ] Evidence repository supports queries by rule, version, domain, factura, time range
- [ ] Each `resultado_auditoria` row has a non-null `evidencia_id` foreign key
- [ ] Querying evidence for a specific problem returns the full condition evaluation trace
