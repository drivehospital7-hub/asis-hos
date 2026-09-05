# Design: Excepción responsable-urgencias en CUPS sin contrato

## Technical Approach

Modificar `detect_cups_sin_contrato()` internamente — sin cambiar su signature ni tocar detect_all.py — para que cuando `Responsable Cierra Facturar` sea un facturador de urgencias, valide el CUPS contra `nota_hoja id=1` en vez de contra `pares_validos`. Se agregan ~15 líneas en el detector y un pre-load query adicional dentro del bloque DB existente.

## Architecture Decisions

### Decision: Per-row lectura de `responsable_cierra`

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Leer columna en el row loop | Simple, 0 cambios a detect_all.py | ✅ Elegido |
| Mapear en detect_all.py y pasar como parámetro | Cambia signature del detector, toca detect_all.py | ❌ Descartado (scope out) |

### Decision: Pre-load dentro del bloque `try`/`except` existente

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Query dentro del bloque existente | Cero cambios estructurales, mismo manejo de errores | ✅ Elegido |
| Query separado fuera del bloque | Duplica manejo de excepciones | ❌ Descartado |

### Decision: Ubicación del branch en el row loop

Insertar después de `codigo_equiv` (línea 198) y antes de `entidades_con_datos` (línea 201). Si el urgencias-facturador pasa (CUPS en `nota1_cups`), `continue` salta todo el resto. Si falla, cae a validación normal — conservador y correcto.

### Decision: `_FACTURADORES_URGENCIAS_NORM` como `frozenset` module-level

El set original tiene nombres en mayúscula pero normalizar explícitamente evita bugs si cambia la fuente. `frozenset` comunica inmutabilidad.

## Data Flow

```
Excel row loop
  │
  ├─ responsable_cierra columna existe?
  │   ├─ No → validación normal (pares_validos)
  │   └─ Sí → ¿resp_name in _FACTURADORES_URGENCIAS_NORM?
  │       ├─ No → validación normal
  │       └─ Sí → ¿codigo in nota1_cups?
  │           ├─ Sí → continue (sin error)
  │           └─ No → ¿codigo_equiv in nota1_cups?
  │               ├─ Sí → continue
  │               └─ No → cae a validación normal (error si no contratado)
  │
  └─ (resto del flujo existente: entidades_con_datos → pares_validos → error)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/transversales/procedimiento_contratado.py` | Modify | +15 lines: import, module-level frozenset, nota1 pre-load query, row-loop branch |
| `tests/services/test_detect_cups_sin_contrato.py` | Modify | Update `_make_mock_session` helper (backward-compatible), add new test cases |

## Interfaces / Contracts

**Sin cambios**: `detect_cups_sin_contrato(data_sheet, indices) -> list[dict]` se mantiene idéntica.

Nuevo module-level en `procedimiento_contratado.py`:

```python
_FACTURADORES_URGENCIAS_NORM: frozenset[str] = frozenset(
    f.strip().upper() for f in FACTURADORES_URGENCIAS
)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_make_mock_session` helper | Backward-compatible: `nota1_cups` default `[]` — tests existentes no se rompen |
| Unit | Default behavior unchanged | Run all 19 existing tests — deben pasar sin cambios |
| Unit | Urgencias facturador + CUPS in nota1 | Sin error (continue por nota1_cups) |
| Unit | Urgencias facturador + CUPS not in nota1 | Error (falla validación y cae al error) |
| Unit | Urgencias facturador + CUPS via codigo_equiv in nota1 | Sin error |
| Unit | No urgencias facturador | Comportamiento normal, pares_validos |
| Unit | Columna responsable_cierra ausente | Fallback a validación normal |
| Unit | responsable_cierra vacío | Fallback a validación normal |

## Migration / Rollout

No migration required. Rollback: revert lines in `procedimiento_contratado.py`.

## Open Questions

- [ ] None.
