# Multi-Dominio Scope Specification

## Purpose

A rule SHALL be applicable to an explicit list of one or more dominios while
`'transversal'` keeps its matches-all meaning. `regla_dominios` is the source
of truth for scope; the legacy `reglas.dominio` single-value column is kept as
a read-only-compatible mirror and MUST NOT be deleted in this change.

## Requirements

### Requirement: Scope storage and migration

The system MUST store rule scope in `regla_dominios(regla_id, dominio)` with
`PRIMARY KEY (regla_id, dominio)` and an index on `(dominio, regla_id)`.

#### Scenario: Backfill covers every existing rule

- GIVEN migration 023 runs against a database where `reglas` has N rows
- WHEN the backfill step executes
- THEN `regla_dominios` contains exactly N rows mapping each `reglas.id` to
  its current `reglas.dominio` value
- AND no row of `reglas` is modified or deleted

#### Scenario: Scope entries are unique per rule

- GIVEN rule 75 has `('urgencias')` in `regla_dominios`
- WHEN a duplicate `('urgencias')` insert for rule 75 is attempted
- THEN the database MUST reject it via the primary key

### Requirement: Domain resolution in the engine

The engine MUST load a rule for a domain run if and only if the rule's scope
contains the run domain or the `'transversal'` wildcard. Rows with no scope
entries MUST fall back to the legacy single-column semantics.

#### Scenario: Explicit multi-domain match

- GIVEN rule `profesional_urg_trabajadora_social` with scope
  `['urgencias', 'hospitalizacion']`
- WHEN a `hospitalizacion` run resolves rules
- THEN the rule is loaded
- WHEN an `odontologia` run resolves rules
- THEN the rule is NOT loaded

#### Scenario: Transversal still matches all

- GIVEN a rule with scope `['transversal']`
- WHEN runs for `urgencias`, `odontologia`, and `intramural` resolve rules
- THEN the rule is loaded in all three runs

#### Scenario: Single-domain rule is unaffected

- GIVEN a rule with scope `['odontologia']`
- WHEN an `odontologia` run and an `urgencias` run resolve rules
- THEN the rule is loaded only in the `odontologia` run

#### Scenario: Exact match keeps priority over transversal

- GIVEN two active versions of the same rule name, one scoped to the run
  domain and one scoped to `'transversal'`
- WHEN `_load_rule_by_name` selects between them
- THEN the exact-domain version MUST win (existing exact-first ordering
  preserved)

#### Scenario: Legacy fallback for scope-less rows

- GIVEN a rule row with zero entries in `regla_dominios` (e.g. written by an
  old code path)
- WHEN a run resolves rules for the value stored in its legacy
  `reglas.dominio` column
- THEN the rule is loaded following the pre-change single-column semantics

### Requirement: CRUD validation and compatibility

The rule service MUST accept `dominios: string[]`, validate it against the
canonical vocabulary, persist scope + legacy mirror atomically, and keep
`dominio: string` working for existing callers.

#### Scenario: Create with multiple dominios

- GIVEN a create payload with `dominios = ['urgencias', 'hospitalizacion']`
- WHEN `create_rule` executes
- THEN `regla_dominios` holds both entries
- AND the legacy `reglas.dominio` mirror is set to the first sorted value
- AND `to_dict` returns `dominios = ['hospitalizacion', 'urgencias']`
  (canonical sorted order)

#### Scenario: Empty or invalid scope is rejected

- GIVEN a create or update payload with `dominios = []`
- OR with any value outside `REGLA_DOMINIOS_VALIDOS`
- WHEN the service executes
- THEN it MUST raise `ValueError`
- AND no scope row is written (transaction rolled back)

#### Scenario: Legacy single-dominio callers keep working

- GIVEN a create payload with only `dominio = 'odontologia'` and no
  `dominios` key
- WHEN `create_rule` executes
- THEN scope is persisted as `['odontologia']`
- AND `duplicate_rule` and `create_version` copy the full scope list

#### Scenario: Domain-filtered listing includes applicable rules

- GIVEN rules scoped `['urgencias']` and `['transversal']` and one scoped
  `['odontologia']`
- WHEN `list_rules(dominio='urgencias')` executes
- THEN it returns the first two rules and NOT the third

### Requirement: UI multi-domain editing and display

The admin-reglas UI MUST let users select zero-or-more (validated non-empty on
save) dominios per rule and MUST display every scoped dominio.

#### Scenario: Edit rule scope in the UI

- GIVEN rule 75 with scope `['urgencias']`
- WHEN the user checks `hospitalizacion` in the edit form and saves
- THEN the API receives `dominios = ['urgencias', 'hospitalizacion']`
- AND the rule row shows both badges afterwards

#### Scenario: Filter matches any scoped dominio

- GIVEN rules scoped `['urgencias', 'hospitalizacion']` and `['odontologia']`
- WHEN the user filters the rule list by `hospitalizacion`
- THEN the first rule is shown and the second is hidden
- AND transversal rules remain visible under every filter (they apply
  everywhere)

#### Scenario: Stored scope always renders

- GIVEN a rule whose scope contains a value outside the current UI option
  list (e.g. seeded before the list was extended)
- WHEN the rule is displayed or edited
- THEN the stored value MUST be shown as-is and MUST NOT be hidden behind a
  placeholder or dropped on save
