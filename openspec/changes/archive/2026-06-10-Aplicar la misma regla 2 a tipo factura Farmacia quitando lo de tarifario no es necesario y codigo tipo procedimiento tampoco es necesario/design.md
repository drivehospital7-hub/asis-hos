# Design: Duplicados Farmacia para tipo factura Farmacia (sin tarifario ni tipo procedimiento)

## Technical Approach

Extraer el algoritmo de detección de duplicados de farmacia (actualmente en `app/services/urgencias/duplicados_farmacia.py`) a una función base parametrizada en `app/services/transversales/`. Crear un detector thin para "Farmacia" que invoque la base sin filtros de tarifario ni `codigo_tipo_procedimiento`. Refactorizar el detector de Urgencias para que use la misma función base — comportamiento idéntico garantizado por los tests existentes.

El diseño sigue el patrón del proyecto: un archivo por detector, parámetros para controlar comportamiento, y output compatible con `normalized_rows.py`.

## Architecture Decisions

### Decision: Parámetros de la función base

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Parámetros separados para cada filtro (`tipo_factura`, `tarifario_val`, `codigos_tipo_proc`) | Más parámetros pero cada uno tiene semántica clara. El grouping key se deriva automáticamente: si `codigos_tipo_proc` está presente, group by `(factura, tipo_proc)`; si no, solo `factura`. | ✅ Elegido |
| Parámetro único `filters: dict` + `group_key: str` | Más genérico pero introduce acoplamiento a keys internas. Menos legible. | ❌ Descartado |
| Copiar el algoritmo en cada detector | Evita refactor, pero viola DRY. El cambio pide explícitamente compartir. | ❌ Descartado |

### Decision: Output format differences

| Aspecto | Urgencias (con `codigos_tipo_proc`) | Farmacia (sin `codigos_tipo_proc`) |
|---------|-------------------------------------|-------------------------------------|
| Grouping key | `(factura, codigo_tipo_procedimiento)` | `(factura,)` |
| Output incluye `codigo_tipo_procedimiento` | ✅ Sí | ❌ No |
| Guard columnas requeridas | tarifario + tipo_proc | Solo básicas |

La función base decide el formato de output según si recibió `codigos_tipo_proc` o no.

### Decision: Normalized rows handler

El handler actual en `normalized_rows.py` usa `item.get("codigo_tipo_procedimiento", "")` — ya tolera valores vacíos. Pero muestra "Grupo : N pares" cuando está vacío. Se actualiza para omitir "Grupo" cuando no hay tipo_proc.

## Data Flow

```
detect_duplicados_generico(data_sheet, indices, *, tipo_factura, tarifario_val, codigos_tipo_proc)
│
├─ Filters rows by tipo_factura (required)
├─ If tarifario_val: filters by tarifario column
├─ If codigos_tipo_proc: filters by codigo_tipo_procedimiento in set
│
├─ Groups: (factura, tipo_proc) if codigos_tipo_proc else (factura,)
│
└─ For each group:
     └─ Counts (codigo, cantidad) pairs
     └─ If ALL pairs count ≥ 2 → emit result

detect_duplicados_farmacia (Urgencias)
  └─ wraps detect_duplicados_generico(..., tipo_factura="Urgencias",
       tarifario_val=VALOR_TARIFARIO_FARMACIA,
       codigos_tipo_proc=CODIGOS_TIPO_PROC_09_12)

detect_duplicados_farmacia_farmacia (nuevo)
  └─ wraps detect_duplicados_generico(..., tipo_factura="Farmacia")
       (tarifario_val=None, codigos_tipo_proc=None)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/transversales/detect_duplicados_base.py` | **Create** | Función `detect_duplicados_generico()` — algoritmo base parametrizado |
| `app/services/farmacia/duplicados_farmacia_farmacia.py` | **Create** | Detector thin para tipo factura "Farmacia" |
| `app/services/urgencias/duplicados_farmacia.py` | Modify | Refactorizado a wrapper que delega en función base |
| `app/services/farmacia/detect_all.py` | Modify | Agregar nuevo detector a `_get_farmacia_detectors()`, error group y totales |
| `app/services/normalized_rows.py` | Modify | Ajustar handler "Duplicados Farmacia" para output sin `codigo_tipo_procedimiento` |
| `tests/services/test_duplicados_farmacia.py` | Modify | Tests existentes deben pasar igual (refactor sin cambio de comportamiento) |
| `tests/services/test_duplicados_farmacia_farmacia.py` | **Create** | Tests para el nuevo detector de tipo Farmacia |

## Interfaces / Contracts

```python
def detect_duplicados_generico(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    *,
    tipo_factura: str,
    tarifario_val: str | None = None,
    codigos_tipo_proc: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Base algorithm.

    When codigos_tipo_proc is not None:
        Required columns: tarifario, codigo_tipo_procedimiento
        Grouping: (factura, codigo_tipo_procedimiento)
        Output keys: factura, codigo_tipo_procedimiento, pares_duplicados, total_pares

    When codigos_tipo_proc is None:
        Required columns: tipo_factura_descripcion, numero_factura, codigo, cantidad
        Grouping: (factura,)
        Output keys: factura, pares_duplicados, total_pares
    """
```

```python
# New detector — app/services/farmacia/duplicados_farmacia_farmacia.py
def detect_duplicados_farmacia_farmacia(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Detecta duplicados en facturas tipo Farmacia.
    Agrupa por factura. Si todos los pares (codigo, cantidad) aparecen ≥2, flag.
    Sin filtros de tarifario ni codigo_tipo_procedimiento.
    """
    return detect_duplicados_generico(
        data_sheet, indices,
        tipo_factura="Farmacia",
    )
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Función base con/ sin filtros | Parametrize con casos de Urgencias y Farmacia |
| Unit | Nuevo detector Farmacia | Mismos escenarios que Urgencias pero sin filtros |
| Unit | Normalized rows con output sin tipo_proc | Verificar descripción no incluye "Grupo " |
| Regression | Urgencias refactor | Tests existentes deben pasar SIN cambios |

## Migration / Rollout

No migration required. El cambio es únicamente de código — no hay datos ni esquemas que migrar.

## Open Questions

None — diseño cubierto por proposal + specs.
