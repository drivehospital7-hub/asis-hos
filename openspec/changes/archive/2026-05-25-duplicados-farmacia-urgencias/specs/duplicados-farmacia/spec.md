# Duplicados Farmacia — Specification

## Purpose

Detect facturas where every (codigo, cantidad) pair within a group (codigo_tipo_procedimiento = "09" or "12") is duplicated, under tariff "Suministros, Medicamentos". Flag for manual review — no auto-correction.

## Requirements

### Requirement: Filter by Tarifario

The system MUST only evaluate rows where the tariff column equals `VALOR_TARIFARIO_FARMACIA` ("Suministros, Medicamentos"). Rows with any other tariff value MUST be ignored.

#### Scenario: Tarifario farmacia matches

- GIVEN a data sheet with rows where tariff = "Suministros, Medicamentos"
- WHEN the detector runs
- THEN it evaluates those rows for duplicate groups

#### Scenario: Tarifario no farmacia is ignored

- GIVEN a data sheet with rows where tariff ≠ "Suministros, Medicamentos"
- WHEN the detector runs
- THEN those rows are not checked

### Requirement: Filter by Tipo Procedimiento

The system MUST only evaluate rows where `codigo_tipo_procedimiento` is "09" or "12". Rows with any other value MUST be ignored.

#### Scenario: Tipo procedimiento 09 or 12 included

- GIVEN rows with codigo_tipo_procedimiento = "09" or "12"
- WHEN the detector runs
- THEN those rows are evaluated

#### Scenario: Other tipo procedimiento ignored

- GIVEN rows with codigo_tipo_procedimiento ≠ "09" or "12"
- WHEN the detector runs
- THEN those rows are skipped

### Requirement: Detect Duplicate Groups

The system MUST group filtered rows by (factura, codigo_tipo_procedimiento). Within each group, if EVERY distinct (codigo, cantidad) pair appears at least 2 times, the entire group MUST be flagged as "Duplicados Farmacia — Grupo {09|12}". If ANY distinct pair appears only once, the group MUST NOT be flagged.
(Previously: Pair-level detection — any pair appearing ≥2 times was flagged individually)

#### Scenario: Grupo 12 con duplicidad total

- GIVEN a factura with 2+ rows of codigo_tipo_procedimiento=12 where every (codigo, cantidad) pair appears ≥2 times
- WHEN the detector runs
- THEN the group is flagged as "Duplicados Farmacia — Grupo 12"

#### Scenario: Grupo 09 con duplicidad total

- GIVEN a factura with 3 distinct pairs in tipo 09, all appearing ≥2 times
- WHEN the detector runs
- THEN the group is flagged

#### Scenario: Grupo con mezcla (duplicados y únicos)

- GIVEN a factura with tipo 09 where pair A appears 2 times but pair B appears 1 time
- WHEN the detector runs
- THEN nothing is flagged for that group

#### Scenario: Múltiples grupos independientes

- GIVEN a factura with rows in both 09 (all duplicated) and 12 (not all duplicated)
- WHEN the detector runs
- THEN only the 09 group is flagged

### Requirement: Graceful Degradation

The system MUST return an empty list when the tariff column, codigo_tipo_procedimiento column, or either is missing. The system MUST NOT raise an exception on missing column references.

#### Scenario: Missing tariff column

- GIVEN a data sheet without a tariff column
- WHEN the detector runs
- THEN an empty list is returned

#### Scenario: Missing codigo_tipo_procedimiento column

- GIVEN a data sheet without codigo_tipo_procedimiento
- WHEN the detector runs
- THEN an empty list is returned

#### Scenario: Sin filas de farmacia

- GIVEN no rows with tariff = "Suministros, Medicamentos"
- WHEN the detector runs
- THEN an empty list is returned

### Requirement: No Auto-Correction

The system MUST NOT merge, remove, or modify rows. It SHALL flag groups exclusively for manual review.

#### Scenario: Duplicate flagged for review only

- GIVEN duplicate groups detected
- WHEN the detector runs
- THEN rows are marked with type_error "Duplicados Farmacia" and severity review
- AND no rows are deleted or merged
