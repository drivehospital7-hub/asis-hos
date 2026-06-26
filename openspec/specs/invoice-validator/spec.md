# Invoice Validator Specification

## Purpose

Validar nombres de archivos de facturas contra patrones FEV/CAP, detectar carpetas vacías, y detectar facturas duplicadas en múltiples ubicaciones.

---

## Requirements

### R1: FEV Pattern Validation

The system MUST match invoice files against the FEV regex pattern (case-insensitive). Valid SHALL mean the filename (without extension) consists only of the pattern.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Valid FEV | file `FEV12345.pdf` | validation runs | type = FEV, valid = true |
| FEV with prefix | file `INV_FEV789.pdf` | validation runs | type = FEV, valid = true |
| Invalid FEV | file `FEV_ABC.pdf` | validation runs | type = FEV, valid = false |

### R2: CAP Pattern Validation

The system MUST match invoice files against the CAP regex pattern (case-insensitive). Valid SHALL mean the filename (without extension) consists only of the pattern.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Valid CAP | file `CAP1234_ABC567.pdf` | validation runs | type = CAP, valid = true |
| CAP with prefix | file `INV_CAP567_DEF890.pdf` | validation runs | type = CAP, valid = true |
| Invalid CAP | file `CAP_ABC.pdf` | validation runs | type = CAP, valid = false |

### R3: Unknown Pattern

The system MUST mark files matching neither FEV nor CAP as type Unknown.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| No match | file `factura_generica.pdf` | validation runs | type = Unknown, valid = false |
| Wrong extension | file `notas.txt` | validation runs | type = Unknown, valid = false |

### R4: Empty Folder Detection

The system MUST flag any facturador subfolder containing zero invoice files.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Truly empty | folder has no files at all | validation runs | folder in empty_folders list |
| Non-invoice files only | folder has only `.txt` and `.log` files | validation runs | folder in empty_folders list |
| Has invoices | folder has 3 valid PDF invoices | validation runs | not in empty_folders list |

### R5: Duplicate Detection

The system MUST detect the same invoice filename appearing in multiple facturador folders across any root.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Cross-facturador | `FEV123.pdf` in Carlos and Maria folders | validation runs | duplicate entry with both paths and facturador names |
| Same root, different subdirs | `CAP1_A2.pdf` in two subdirs of same root | validation runs | duplicate entry reported |
| Three-way duplicate | `FEV99.pdf` in three different folders | validation runs | single duplicate entry with all 3 paths |
| No duplicate | `FEV123.pdf` appears only once | validation runs | no duplicate entry for this file |
| Different content, same name | two identical filenames in different folders | validation runs | treated as duplicate (filename-based, not content-based) |

## Non-Functional Requirements

- Pattern matching SHALL be case-insensitive and locale-independent.
- Validation MUST process all files across all scanned folders in a single pass.
- Duplicate detection SHALL be filename-based (content comparison is out of scope).
- Regex patterns SHALL reside in `app/constants/monitoreo_carpetas.py`, not in validator source code.
