# Design: Deduplicación de errores de contrato por factura

## Technical Approach

Añadir un `set[str]` de facturas procesadas al inicio del loop principal de cada detector. Si la factura ya fue reportada, se salta la fila completa. Sigue el patrón ya establecido en 4 detectores (`codigo_entidad.py`, `tipo_documento_edad.py`, `tipo_usuario.py`, `ide_contrato_reverse.py`).

## Architecture Decisions

### Decision: Dónde implementar la dedup

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **En cada detector** (set local) | +0 dependencies, +0 acoplamiento, ~6 líneas por detector | ✅ Elegido |
| En orquestador (`detect_all.py`) | Tendría que post-procesar la lista, deduplicar por factura. Pierde el skip temprano (sigue recorriendo todas las filas). Más complejo. | ❌ Rechazado |
| En normalizer (`normalized_rows.py`) | Afecta a TODOS los detectores, no solo contrato. Cambio de alto impacto. | ❌ Rechazado |
| Helper compartido (decorator/wrapper) | Sobrediseño para 2 detectores que necesitan ~6 líneas idénticas. | ❌ Rechazado |

### Decision: Skip temprano vs post-filter por regla

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **Skip temprano** (al inicio del loop, toda la fila) | Una factura = un contrato. Si no matchea, no matchea para ninguna regla. ~3 líneas. | ✅ Elegido |
| Post-filter por regla (check en cada append) | 6 check-points en urgencias, overhead innecesario. Misma conducta final. | ❌ Rechazado |

### Decision: Set vs List

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **Set** | O(1) lookup, sin duplicados, mismo patrón que detectores existentes | ✅ Elegido |
| List | O(n) lookup, funcional pero más lento para hojas grandes | ❌ Rechazado |

## Data Flow

**Antes** (N filas = N errores idénticos):

```
Row 1 (FAC-001, código X) ─→ rule check ─→ error "IDE 900, esperado 977"
Row 2 (FAC-001, código Y) ─→ rule check ─→ error "IDE 900, esperado 977"  ← DUPLICADO
Row 3 (FAC-001, código Z) ─→ rule check ─→ error "IDE 900, esperado 977"  ← DUPLICADO
```

**Después** (1 error por factura):

```
facturas_procesadas: set[str] = set()

Row 1 (FAC-001) ─→ ¿en set? No ─→ rule check ─→ error ─→ add("FAC-001")
Row 2 (FAC-001) ─→ ¿en set? Sí ─→ continue (skip)
Row 3 (FAC-001) ─→ ¿en set? Sí ─→ continue (skip)
```

## File Changes

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `app/services/urgencias/ide_contrato_urgencias.py` | Modificar | Añadir `facturas_procesadas: set[str] = set()` antes del loop (L92). Al inicio del loop, después del `normalize_invoice`, check `if factura_str in facturas_procesadas: continue` (L96). Después de CADA append, `facturas_procesadas.add(factura_str)` o simplificado: `facturas_procesadas.add(factura_str)` al final del bloque de reglas si se añadió al menos un error. |
| `app/services/odontologia/ide_contrato.py` | Modificar | Añadir `facturas_procesadas: set[str] = set()` antes del loop (L182). Check al inicio del loop (L187). `facturas_procesadas.add(factura_str)` después del append (L219). |

### Detalle urgencias — 6 rule sections, 1 skip point

El skip temprano al inicio del loop (después de `normalize_invoice`) evita tener que trackear 6 append sites. Si la factura ya fue procesada, se salta toda la validación. No se necesita `add()` por cada regla.

**Código a insertar** en `ide_contrato_urgencias.py`:

```python
# L91: después de `problemas_ide_contrato: list[dict[str, Any]] = []`
facturas_procesadas: set[str] = set()

# L96-97: después de `if not factura_str: continue`
if factura_str in facturas_procesadas:
    continue

# Al final del bloque de reglas, dentro del loop, antes del next row:
facturas_procesadas.add(factura_str)
```

### Detalle odontología — 1 rule section, 1 skip point

```python
# L181: después de `problemas: list[dict[str, str]] = []`
facturas_procesadas: set[str] = set()

# L187-188: después de `if not factura_str: continue`
if factura_str in facturas_procesadas:
    continue

# L226-227: después del append
facturas_procesadas.add(factura_str)
```

## Interfaces / Contracts

Sin cambios. La función `detect_ide_contrato_urgencias()` y `detect_ide_contrato_odontologia()` mantienen su firma y tipo de retorno. Solo cambia la cardinalidad: antes N errores por N filas de la misma factura, ahora 1.

## Testing Strategy

| Capa | Qué testear | Approach |
|------|-------------|----------|
| Unit (urgencias) | Misma factura en 3 filas → 1 error | Crear hoja con 3 filas FAC-001, todas con IDE incorrecto. Assert `len(result) == 1`. |
| Unit (odontología) | Misma factura en 3 filas → 1 error | Crear hoja con 3 filas FAC-001, todas con IDE incorrecto. Assert `len(result) == 1`. |
| Unit (urgencias) | Facturas distintas cada una con error → N errores | Crear FAC-001 y FAC-002, ambas con error. Assert `len(result) == 2`. |
| Unit (odontología) | Sin errores → 0 errores | Regression test: misma factura con IDE correcto. Assert `len(result) == 0`. |
| Integration | Pipeline completo `detect_all`→`normalized_rows` | Verificar que las filas normalizadas no tienen duplicados de contrato por factura. |
| Regression | Tests existentes pasan sin modificación | `python -m pytest -v tests/services/test_odontologia_ide_contrato.py tests/services/test_urgencias_normalized_rows.py tests/services/test_odontologia_normalized_rows.py` |

## Migration / Rollout

No migration required. Rollback: revertir las ~6 líneas añadidas a cada detector.

## Open Questions

None.
