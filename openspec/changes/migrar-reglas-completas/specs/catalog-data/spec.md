# Catalog Data Specification

## Purpose

Reference data tables accessible from the rule engine during evaluation. Replaces hardcoded Python dictionaries with DB-backed lookup providers for professionals, contracts, code mappings, and domain constants.

## Requirements

### R1: Professional Catalog

The system MUST maintain a `profesionales` table with columns: `codigo` (PK), `nombre`, `tipo`, `dominio` (odontologia|urgencias|equipos_basicos). The `CatalogProvider` SHALL expose `exists_by_field(table, field, value) → bool` and field-access by dot path.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Lookup by code | "OD001" row exists with tipo="ODONTOLOGO" | `catalog.profesionales["OD001"].tipo` | returns "ODONTOLOGO" |
| Domain filter | 5 odontología + 3 urgencias professionals | query with dominio="odontologia" | returns 5 rows |
| Not found | "XX999" not in table | lookup | returns null/None, rule evaluates to NO_MATCH |

### R2: Contract Reference Data

The system MUST maintain contract reference tables: `contratos` (entidad, ide_contrato, vigencia_desde, vigencia_hasta) and `notas_tecnicas` (entidad, codigo, tarifa, nota_hoja). The `ContractProvider` SHALL resolve `contract.nota_tecnica[entidad]` and `contract.ide_valido[entidad][codigo]` paths.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Tariff lookup | ESSC18 has tarifa 5000 in notas_tecnicas | `contract.nota_tecnica["ESSC18"].tarifa` | returns 5000 |
| IDE set validation | ESS118 has IDE set {100, 200} for code 890201 | `contract.ide_valido["ESS118"]["890201"]` contains row's ide | returns true |
| Expired contract | contrato for ESS062 ended 2023-12-31, current date 2024-06 | lookup with vigencia check | contract excluded, treated as if not found |

### R3: Code Substitution Mappings

The system MUST maintain a `code_mappings` table: `codigo_original` (PK), `codigo_equivalente`, `entidad` (nullable, null=global), `dominio`. The `CodeMappingProvider` SHALL resolve `substitute(codigo, entidad, dominio)` → equivalent code or original if no mapping exists.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Global mapping | 906317 → 1906317 (entidad=null) | substitute("906317", any_entidad, "odontologia") | returns "1906317" |
| Entity-specific | 890205 → 890405 only for ESS118 | substitute("890205", "ESS118", "urgencias") | returns "890405" |
| No mapping | code "999999" not in table | substitute("999999", any) | returns "999999" (unchanged) |

### R4: Domain Constants

The system MUST maintain a `parametros_sistema` table: `clave` (PK), `valor`, `dominio` (nullable). Constants like `URGENCIAS_CODIGOS_CANTIDAD_MAX_1` SHALL be stored as JSON arrays. The engine's `ConstantsProvider` SHALL expose `constants.get(clave)`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List constant | `URGENCIAS_CODIGOS_CANTIDAD_MAX_1` = `["C8901","C8902"]` | `constants.get("URGENCIAS_CODIGOS_CANTIDAD_MAX_1")` | returns list with 2 codes |
| Scalar constant | `CENTRO_COSTO_FARMACIA` = "FARMACIA" | condition `eq(centro_costo, constants.get("CENTRO_COSTO_FARMACIA"))` | resolves to `eq(centro_costo, "FARMACIA")` |
| Missing key | "UNDEFINED_KEY" not in table | constants.get("UNDEFINED_KEY") | returns null, rule logs warning |
