# Delta for evidencia-auditoria

## MODIFIED Requirements

### R3: Query and Retrieval (with REST Endpoint)

The evidence repository MUST support querying by: rule ID, version, domain, factura, and timestamp range. Querying MUST NOT require loading the full evaluation log into memory — pagination SHALL be supported.
(Previously: Query and retrieval via EvidenceRepository only)

**REST ENDPOINT**: A `GET /api/evidencias` endpoint SHALL wrap the EvidenceRepository. Query params: `?regla_id=`, `?factura=`, `?dominio=`, `?desde=`, `?hasta=`, `?limit=`, `?offset=`. Response SHALL include both the results array and a `total` count. Default `limit` SHALL be 100. All responses MUST follow the canonical `{"status", "data", "errors"}` envelope.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| By rule (repository) | evidence with 500 records for rule R1 | query evidencias WHERE rule_id=R1 | all 500 records returned, paginated |
| By factura | evidence for factura="F001" across 3 rules | query evidencias WHERE factura="F001" | 3 records returned (one per rule evaluated) |
| Time range | evidence from 2026-06-01 to 2026-06-07 | query with timestamp BETWEEN | only records in range returned |
| No results | query for factura="NONEXISTENT" | query | empty result set, not an error |
| **REST: default pagination** | 500 evidence records in DB | `GET /api/evidencias` | first 100 records returned, total=500 |
| **REST: with filters** | evidence for R1, factura F001 | `GET /api/evidencias?regla_id=1&factura=F001` | filtered records only |
| **REST: custom page size** | 500 records, user wants 50 per page | `GET /api/evidencias?limit=50&offset=100` | records 101-150 returned, total=500 |
