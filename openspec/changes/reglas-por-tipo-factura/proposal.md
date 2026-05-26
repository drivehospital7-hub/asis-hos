# Proposal: reglas-por-tipo-factura

## Intent

Detection rules are organized by HTTP route (`/urgencias`) instead of "Tipo Factura Descripcion" Excel column. One orchestrator runs 16 detectors against ALL rows regardless of invoice type. Detectors already filter internally (8 of 13 do), but 5 don't, and the architecture mixes Urgencias, Hospitalizacion, Intramural, and Ambulatoria in a single package.

**Goal**: dispatch detectors by business type (column value), not HTTP route. Each tipo_factura gets its own orchestrator and package.

## Scope

### In Scope (2-PR incremental)

**PR 1 — Internal filters (~4h, low risk)**
- Add `tipo_factura_descripcion` filter to 5 detectors that lack it: `profesionales_urgencias`, `ide_contrato_urgencias`, `ide_contrato_reverse`, `codigos_sin_db`, `revision_cantidad`
- Move `detect_copago_entidad` from `urgencias/` to `transversales/`
- Move `odontologia/mal_capitado.py` to `urgencias/` (fix wrong package import)

**PR 2 — Structural reorganization (~8-14h, medium risk)**
- Create 4 packages: `hospitalizacion/`, `intramural/`, `ambulatoria/` + shrink `urgencias/`
- Each package gets its own `detect_all.py` orchestrator
- Create `app/services/tipo_factura_registry.py` — maps column values to detector lists
- Update `exporter.py` to dispatch by `tipo_factura_descripcion` instead of `area`
- Move/split `centro_costo_urgencias.py` (448 lines, mixes 4 tipos) into per-tipo detectors
- Update routes, ~40 test files, and `normalized_rows` builder

### Out of Scope
- Splitting `app/constants/urgencias.py` (794 lines) — deferred to follow-up
- Changing transversal detectors (correctly apply to all types)
- Modifying frontend JSON response shape
- Adding new detection rules — reorganization only

## Capabilities

### New Capabilities
- `tipo-factura-registry`: Central registry mapping "Tipo Factura Descripcion" → detector lists, enabling dispatch by business type
- `hospitalizacion-detection`: Independent orchestrator for Hospitalizacion invoices
- `intramural-detection`: Independent orchestrator for Intramural invoices
- `ambulatoria-detection`: Independent orchestrator for Ambulatoria invoices

### Modified Capabilities
None — no existing spec changes its requirements. Detector behavior is preserved; only dispatch mechanism changes.

## Approach

**2-PR incremental strategy** validated by exploration (see `exploration.md` for full detector mapping):

| PR | Risk | Effort | What |
|----|------|--------|------|
| 1 | Low | ~4h | Add internal `tipo_factura` filters + fix code smells. No structural changes. All existing tests pass. |
| 2 | Medium | ~8-14h | Package split, registry creation, orchestrator per tipo, route updates, test migration. |

**Architecture target** (after PR 2):
```
app/services/
├── transversales/              # Unchanged
├── odontologia/                # Unchanged
├── equipos_basicos/            # Unchanged
├── urgencias/                  # Only Urgencias detectors
├── hospitalizacion/            # NEW: Hospitalizacion detectors
├── intramural/                 # NEW: Intramural detectors
├── ambulatoria/                # NEW: Ambulatoria detectors
└── tipo_factura_registry.py    # NEW: tipo_factura → detector list dispatch
```

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/urgencias/` | Modified | Shrink to Urgencias-only; move others out |
| `app/services/hospitalizacion/` | New | Hospitalizacion detectors + orchestrator |
| `app/services/intramural/` | New | Intramural detectors + orchestrator |
| `app/services/ambulatoria/` | New | Ambulatoria detectors + orchestrator |
| `app/services/tipo_factura_registry.py` | New | Dispatch registry |
| `app/services/exporter.py` | Modified | Dispatch by tipo_factura, not area |
| `app/routes/` | Modified | Route dispatch updated |
| `app/services/odontologia/mal_capitado.py` | Modified | Move to urgencias/ |
| Tests (~40 files) | Modified | Update import paths |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Breaking ~40 test files | Medium | Run `pytest -v` after every step; update imports incrementally |
| `build_urgencias_normalized_rows` coupled to flat list | Medium | Create per-tipo builders in PR 2 |
| Frontend expects specific `area` key in JSON | Low | Keep `area` field, add `tipo_factura` field |
| `centro_costo_urgencias.py` refactor (448 lines) | High | Split in PR 2 only; each tipo gets its own detector file |
| Git conflicts during package move | Low | Use `git mv` to preserve history |

## Rollback Plan

**PR 1**: Revert via `git revert` — filters only skip rows, no structural changes.
**PR 2**: Roll back to PR 1 state. New packages don't affect old code paths. `tipo_factura_registry.py` is additive; old orchestrator stays until tests confirm new dispatch.

## Dependencies

- `exploration.md` (done) — detector mapping complete
- All existing tests must pass on `main` before starting
- `Tipo Factura Descripcion` column already in `required_headers` — no Excel format change needed

## Success Criteria

- [ ] PR 1: All 13 urgencias detectors filter by `tipo_factura_descripcion`; `pytest` passes unchanged
- [ ] PR 1: `mal_capitado.py` lives in `urgencias/`; `detect_copago_entidad` in `transversales/`
- [ ] PR 2: 4 independent orchestrators (urgencias, hospitalizacion, intramural, ambulatoria) with `detect_all.py` each
- [ ] PR 2: `tipo_factura_registry.py` maps all known tipo_factura values to correct detector lists
- [ ] PR 2: `exporter.py` dispatches by tipo_factura; routes unchanged in behavior
- [ ] PR 2: All ~40 test files pass with updated imports
- [ ] PR 2: `centro_costo_urgencias.py` split into per-tipo detectors (max 200 lines each)
- [ ] JSON response format backward-compatible (frontend unchanged)
