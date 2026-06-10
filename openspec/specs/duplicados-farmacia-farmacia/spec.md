# Duplicados Farmacia-Farmacia — Specification

## Purpose

Detect facturas where every (codigo, cantidad) pair is duplicated within tipo factura "Farmacia" — without tariff or codigo_tipo_procedimiento filters. Flag for manual review — no auto-correction.

## Requirements

### Requirement: Filter by Tipo Factura

The system MUST only evaluate rows where `tipo_factura_descripcion` equals "Farmacia". Rows with any other value MUST be ignored.

#### Scenario: Farmacia tipo factura matches

- GIVEN a data sheet with rows where tipo_factura = "Farmacia"
- WHEN the detector runs
- THEN it evaluates those rows for duplicate pairs

#### Scenario: Other tipo factura ignored

- GIVEN a data sheet with rows where tipo_factura ≠ "Farmacia"
- WHEN the detector runs
- THEN those rows are not checked

### Requirement: Detect Duplicate Facturas

The system MUST group filtered rows by factura. Within each group, if EVERY distinct (codigo, cantidad) pair appears at least 2 times, the entire factura MUST be flagged as "Duplicados Farmacia". If ANY distinct pair appears only once, the factura MUST NOT be flagged.

#### Scenario: Factura con duplicidad total

- GIVEN a factura with 2+ rows where every (codigo, cantidad) pair appears ≥2 times
- WHEN the detector runs
- THEN the factura is flagged as "Duplicados Farmacia"

#### Scenario: Factura con mezcla (duplicados y únicos)

- GIVEN a factura where pair A appears 2 times but pair B appears 1 time
- WHEN the detector runs
- THEN nothing is flagged for that factura

#### Scenario: Factura sin duplicados

- GIVEN a factura where every (codigo, cantidad) pair is unique
- WHEN the detector runs
- THEN nothing is flagged

#### Scenario: Múltiples facturas independientes

- GIVEN factura F001 (all pairs duplicated) and F002 (not all duplicated)
- WHEN the detector runs
- THEN only F001 is flagged

### Requirement: Graceful Degradation

The system MUST return an empty list when required columns are missing. The system MUST NOT raise an exception on missing column references.

#### Scenario: Missing numero_factura column

- GIVEN a data sheet without numero_factura column
- WHEN the detector runs
- THEN an empty list is returned

#### Scenario: Missing codigo column

- GIVEN a data sheet without codigo column
- WHEN the detector runs
- THEN an empty list is returned

#### Scenario: Missing tipo_factura_descripcion column

- GIVEN a data sheet without tipo_factura_descripcion
- WHEN the detector runs
- THEN an empty list is returned

#### Scenario: Sin filas de Farmacia

- GIVEN no rows with tipo_factura = "Farmacia"
- WHEN the detector runs
- THEN an empty list is returned

### Requirement: No Auto-Correction

The system MUST NOT merge, remove, or modify rows. It SHALL flag groups exclusively for manual review.

#### Scenario: Duplicate flagged for review only

- GIVEN duplicate facturas detected
- WHEN the detector runs
- THEN rows are marked with type_error "Duplicados Farmacia" and severity review
- AND no rows are deleted or merged
