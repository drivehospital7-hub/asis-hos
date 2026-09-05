# Monitoreo Report Specification

## Purpose

Generar un reporte Excel con datos detallados por factura e indicadores operacionales agregados, usando openpyxl con estilos de `app/utils/formatting.py`.

---

## Requirements

### R1: Per-Invoice Data Sheet

The report MUST include a sheet named `Facturas` with one row per invoice containing: invoice code, type (FEV/CAP/Unknown), status (Verificada/Por corregir/En revisión), full path, facturador name, scan timestamp, and anomaly flags (duplicate, empty_folder, invalid_name).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| All fields present | scan returned 5 scanned invoices | report generated | sheet has 5 data rows; all 7 columns present |
| No invoices | scan returned 0 invoices | report generated | sheet has header row only |
| Anomalies present | 2 invoices are duplicates, 1 is invalid | report generated | flag columns set to true for those rows |
| No anomalies | no issues found | report generated | all flag columns = false for every row |

### R2: Operational Indicators

The report MUST include a second sheet named `Indicadores` with: total invoices per status, total per type, top 5 anomalies ranked by count.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Status counts | scan: 10 Verificada, 5 Por corregir, 2 En revisión | report generated | status counts match scanned data exactly |
| Type counts | 8 FEV, 7 CAP, 2 Unknown | report generated | type counts match scanned data |
| Top anomalies | duplicates=3, empty folders=2, invalid names=1 | report generated | ranked list: duplicates > empty > invalid |
| Zero anomalies | no problems found | report generated | each anomaly count = 0 |

### R3: Excel Formatting

The report MUST apply styles from `app/utils/formatting.py`. Headers SHALL use the header style defined there.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Header style applied | report generated | inspect row 1 of Facturas | header font, fill, and alignment match formatting.py style |
| Anomaly row highlighted | row has at least one active flag | report generated | row has conditional yellow background |

### R4: Output Path and Naming

The report MUST be saved to `app/data/output/` with timestamped filename `monitoreo_YYYYMMDD_HHMMSS.xlsx`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Timestamp naming | report generated 2026-06-23 15:30:00 | file saved | filename = `monitoreo_20260623_153000.xlsx` |
| Output dir missing | `app/data/output/` does not exist | report generated | error logged; report NOT generated |

### R5: Download Endpoint

`GET /monitoreo-carpetas/report/<filename>` MUST serve the generated report for download.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| File exists | report file in output dir | GET with valid filename | 200 response; Content-Disposition attachment; `.xlsx` |
| File not found | filename does not exist | GET with invalid name | 404 |
| Directory traversal | filename = `../../etc/passwd` | GET | 400; no file served |

## Non-Functional Requirements

- Report generation MUST complete within 30 s for ≤ 10,000 invoices.
- All reports SHALL be eligible for cleanup after 24 h (best-effort TTL, log on failure).
- The report MUST NOT use Polars — openpyxl only for writing, consistent with existing exporter pattern.
