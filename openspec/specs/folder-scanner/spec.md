# Folder Scanner Specification

## Purpose

Recorrer directorios de red configurados, enumerar subcarpetas de facturadores, e inferir estado desde el nombre del folder padre. Tolerante a variaciones estructurales entre facturadores.

---

## Requirements

### R1: Scan Configured Roots

The system MUST read root directories from the **folder-scanner-config store** and enumerate first-level subdirectories as facturador folders.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Single root | store returns one root dir with 3 facturadores | scan runs | all 3 subdirs returned |
| Multiple roots | store returns 2 root dirs | scan runs | subdirs from both roots returned |
| Empty root | store returns empty list | scan runs | empty result returned (no error) |
| Store corrupt | store falls back to env var with 1 root | scan runs | that 1 root is scanned |

### R2: Infer Status from Folder Name

The system MUST assign status based on parent folder name matching configured keywords.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Verificada (LISTAS OK) | parent folder `LISTAS OK - Juan` | status inferred | status = Verificada |
| Verificada (CAP LISTAS) | parent folder `CAP LISTAS - Maria` | status inferred | status = Verificada |
| Por corregir (CORREGIR) | parent folder `CORREGIR - Carlos` | status inferred | status = Por corregir |
| Por corregir (CORRECCION) | parent folder `CORRECCION - Ana` | status inferred | status = Por corregir |
| Default (no keyword match) | parent folder `PENDIENTE - Luis` | status inferred | status = En revisión |
| Custom keyword | new keyword `REVISADO` added to config | status inferred | status = Verificada |

### R3: Structural Tolerance

The system SHOULD continue scanning remaining roots when one root is inaccessible. Inaccessible roots SHALL be logged with error reason.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Root unreachable | root dir `\\server\billing` network error | scan runs | error logged; other roots scanned |
| Timeout | root dir takes longer than configured timeout | scan runs | timeout logged; scan continues |
| Permission denied | no read access to root dir | scan runs | permission error logged; scan continues |
| Facturador inaccessible | 1 of 5 subdirs unreadable | scan runs | 4 subdirs returned; error logged |

### R4: Symlink Safety

The system SHOULD NOT follow directory symlinks or junctions pointing outside the root.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| External symlink | subfolder is a symlink to `\\other\share` | scan runs | subfolder skipped; warning logged |

### R5: Status Keywords Are Configurable

Status keywords SHALL reside in `app/constants/monitoreo_carpetas.py` as a mapping, not hardcoded in the scanner.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Constant imported | scanner initializes | imports from constants | mapping has Verificada, Por corregir, En revisión keys |
| No hardcoded strings | scanner runs | check source | status lookup references constants file, not inline literals |

## Non-Functional Requirements

- Scanner MUST complete within a configurable timeout per root directory.
- All errors SHALL be logged via `logger.error()` including path and exception message.
- The scanner SHALL NOT execute any external commands or shell calls.
