# Design: Facturador Urgencias — Validación contra Nota 27 para entidades no listadas

## Technical Approach

Single-condition restructure in `detect_cups_sin_contrato()`: remove `cod_entidad in _ENTIDADES_NOTA_URGENCIAS` from the urgencias bypass guard (line 215). This makes the `nota_urgencias_cups` check available to ALL urgencias billers regardless of entity, while preserving the `pares_validos` fallthrough for both list and non-list entities.

The existing dual-branch semantics are equivalent — both branches check `nota_urgencias_cups` first, then fall through to `pares_validos`. The `_ENTIDADES_NOTA_URGENCIAS` guard was incorrectly blocking entities outside the list from even accessing the check. Removing it is safe because:

1. The check only runs when `resp_name` matches an urgencias biller — this gate remains.
2. If CUPS is found in `nota_urgencias_cups` → `continue` (same for both list and non-list).
3. If CUPS is NOT found → execution falls through to `pares_validos` (same for both).

## Architecture Decisions

### Decision: Remove guard vs. two explicit branches

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Remove `cod_entidad in _ENTIDADES_NOTA_URGENCIAS` only | Simpler, fewer lines changed, no duplication | ✅ **Chosen** |
| Two explicit branches (`if in_list / else`) | Explicit intent, easier to diverge later | ❌ Unnecessary — both branches have identical fallthrough |

**Rationale**: Both branches perform the identical flow (check `nota_urgencias_cups` → if found `continue` → else fall through). The single-conditional removal achieves the same with less code and zero duplication. If future requirements diverge per entity type, that change can be additive.

### Decision: Keep `_ENTIDADES_NOTA_URGENCIAS` constant

The constant is retained as-is but no longer gates the bypass. It remains available for future entity-specific logic without dead-code removal.

## Data Flow

**Before** (broken for ESS118):

```
Facturador urgencias? AND entidad en _ENTIDADES_NOTA_URGENCIAS?
    ├── No (ESS118, etc.) → skip block → validación normal (pares_validos) → FALLA
    └── Sí → CUPS en nota_urgencias_cups?
              ├── Sí → continue
              └── No → pares_validos
```

**After** (fixed):

```
Facturador urgencias?
    ├── No → skip block → pares_validos (unchanged)
    └── Sí → CUPS en nota_urgencias_cups?
              ├── Sí → continue
              └── No → pares_validos (igual que antes para entidades en lista)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/transversales/procedimiento_contratado.py` | Modify | **Line 207-210**: update comment to reflect that all urgencias billers check `nota_urgencias_cups` first. **Line 215**: remove `and cod_entidad in _ENTIDADES_NOTA_URGENCIAS`. |

No other files modified. No files created or deleted.

## Interfaces / Contracts

No new interfaces. `_ENTIDADES_NOTA_URGENCIAS` constant retained but no longer used in the condition (preserved for documentation and future use).

## Testing Strategy

### Existing tests (section 14, lines 594-754)

All 8 tests use **ESS118** (NOT in `_ENTIDADES_NOTA_URGENCIAS`). After the fix they should pass as originally intended. They cover: CUPS in set → no error, CUPS not in set → error, `codigo_equiv` in set → no error, empty set → error, missing column → normal validation, empty cell → normal validation, double-space normalization.

### New tests

| Test | Scenario | Expected |
|------|----------|----------|
| Entity in list + CUPS in nota_urgencias_cups | EPSS08 + urgencias biller + 965201 | No error (regression) |
| Entity in list + CUPS NOT in nota_urgencias_cups, NOT in pares_validos | EPSS08 + urgencias biller + 999999 | Error |
| Entity NOT in list + CUPS in pares_validos | ESS118 + urgencias biller + 878001 (in pares) | No error (pares_validos fallback) |
| Bug scenario | ESS118 + 903437 + MEZA FERNANDEZ CARLOS OMAR | No error |
| Non-urgencias biller unchanged | ESS118 + 965201 + non-urgencias name | Error (normal validation) |

## Migration / Rollout

No migration required. Single file modification, deploy as part of normal release cycle.

## Open Questions

None.
