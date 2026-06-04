# Design: Duplicado ID+Código para Intramural

## Technical Approach

Nuevo detector `detect_duplicado_id_codigo()` que agrupa filas por `(identificación, código)` usando un `defaultdict[list]`. Cada grupo con >1 elemento produce un error **por fila**. Se registra en el orquestador de Intramural y se agrega handler en `build_normalized_rows()`.

---

## Architecture Decisions

### Decision: Usar `codigo` → `"Cód. Equivalente CUPS"` (existing mapping)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Crear `codigo_duplicado` → `"Código"` | Rompe con el patrón existente; todos los detectores usan `codigo` | ❌ Rechazado |
| Usar `codigo` → `"Cód. Equivalente CUPS"` | Consistente con detectores existentes; si el Excel Intramural usa exactamente "Código", el mapping fallaría | ✅ Aceptado |
| Soporte dual (try ambos nombres) | Complejidad innecesaria para un caso no confirmado | ❌ Rechazado |

**Rationale**: El detector recibe el mismo `indices` dict que los demás detectores Intramural, donde `codigo` ya está mapeado a `"Cód. Equivalente CUPS"` con éxito comprobado. Si el Excel usara exactamente "Código", se ajusta el mapping en `required_headers` del caller, no en el detector.

### Decision: Agrupar por `(identificacion, codigo)` — sin filtrar por factura distinta

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Agrupar solo si misma factura | Falsos negativos: mismo paciente+mismo código en distintas facturas también es duplicado | ❌ Rechazado |
| Agrupar sin filtrar factura | Marca TODAS las repeticiones; el equipo revisa | ✅ Aceptado |
| Configurable por threshold | El negocio dijo "toda repetición es error" | ❌ Rechazado |

**Rationale**: El negocio es claro — cualquier repetición de la misma combinación identificación+código es sospechosa. Se marca siempre.

### Decision: Un error POR FILA (no un error por grupo)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Un error por grupo | Menos ruido pero pierde trazabilidad por factura | ❌ Rechazado |
| Un error por fila | Más líneas en resultados pero cada factura aparece explícitamente | ✅ Aceptado |

**Rationale**: El sistema actual funciona por fila (cada error se asocia a una factura). Consistencia con el patrón existente.

---

## Data Flow

```
Excel Intramural (.xlsx)
    │
    ▼
detect_all_problems_intramural(data_sheet, indices)
    │
    ├── detect_decimales(...)
    ├── detect_tipo_documento_edad(...)
    ├── ... (otros detectores existentes)
    │
    ├── detect_duplicado_id_codigo(data_sheet, indices)
    │       │
    │       ├── Valida: numero_factura, identificacion, codigo
    │       ├── Itera filas 2..max_row
    │       ├── Agrupa por (identificacion_str, codigo_str)
    │       └── Retorna: [{factura, identificacion, codigo, procedimiento, cantidad_repeticiones}, ...]
    │
    ├── error_groups["Duplicado ID+Código"] = resultado_detector
    │
    ▼
build_normalized_rows(error_groups)
    │
    ├── Itera error_groups["Duplicado ID+Código"]
    └── Produce filas con tipo_error="Duplicado ID+Código"
    │
    ▼
resultado["problemas"]["duplicado_id_codigo"]
resultado["totales"]["duplicado_id_codigo"]
```

---

## Component Details

### New: `app/services/intramural/duplicado_id_codigo.py`

```python
"""Detector de duplicados por identificación + código en Intramural.

Dos o más filas con mismo Nº Identificación y mismo Código se marcan como error.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.services.transversales.normalize import normalize_invoice

logger = logging.getLogger(__name__)


def detect_duplicado_id_codigo(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Detecta filas con misma identificación + mismo código (duplicados).

    Args:
        data_sheet: Hoja activa del Excel.
        indices: Mapeo nombre_columna → índice 0-based.

    Returns:
        Lista de dicts con keys: factura, identificacion, codigo,
        procedimiento, cantidad_repeticiones. Vacía si faltan columnas.
    """
    num_fact_idx = indices.get("numero_factura")
    ident_idx = indices.get("identificacion")
    codigo_idx = indices.get("codigo")
    proc_idx = indices.get("procedimiento")

    if None in (num_fact_idx, ident_idx, codigo_idx):
        logger.warning("Duplicado ID+Código - Columnas necesarias no encontradas")
        return []

    # Agrupar filas por (identificacion, codigo)
    grupos: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for row in range(2, data_sheet.max_row + 1):
        numero = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura = normalize_invoice(numero)
        if not factura:
            continue

        ident_raw = data_sheet.cell(row=row, column=ident_idx + 1).value
        codigo_raw = data_sheet.cell(row=row, column=codigo_idx + 1).value

        ident_str = str(ident_raw).strip() if ident_raw is not None else ""
        codigo_str = str(codigo_raw).strip() if codigo_raw is not None else ""

        if not ident_str or not codigo_str:
            continue

        procedimiento = (
            str(data_sheet.cell(row=row, column=proc_idx + 1).value or "").strip()
            if proc_idx is not None
            else ""
        )

        key = (ident_str, codigo_str)
        grupos[key].append({
            "factura": factura,
            "identificacion": ident_str,
            "codigo": codigo_str,
            "procedimiento": procedimiento,
        })

    # Generar errores: cada grupo con >1 elemento produce error por fila
    resultado: list[dict[str, Any]] = []
    for key, filas in grupos.items():
        if len(filas) <= 1:
            continue
        for fila in filas:
            resultado.append({
                "factura": fila["factura"],
                "identificacion": fila["identificacion"],
                "codigo": fila["codigo"],
                "procedimiento": fila["procedimiento"],
                "cantidad_repeticiones": len(filas),
            })

    if resultado:
        logger.info(
            "Duplicado ID+Código - %d filas duplicadas en %d grupos",
            len(resultado),
            sum(1 for g in grupos.values() if len(g) > 1),
        )

    return resultado
```

### Modified: `app/services/intramural/detect_all.py`

**En `_get_intramural_detectors()`** — agregar import y retorno:

```python
from app.services.intramural.duplicado_id_codigo import (
    detect_duplicado_id_codigo,
)
return [
    ...,
    detect_duplicado_id_codigo,
]
```

**En `detect_all_problems_intramural()`** — después del paso 7 (IDE Contrato), antes de `build_normalized_rows`:

```python
# 8. Duplicado ID+Código
from app.services.intramural.duplicado_id_codigo import (
    detect_duplicado_id_codigo,
)
duplicado_id_codigo = detect_duplicado_id_codigo(data_sheet, indices)
logger.info(
    "Duplicado ID+Código: %d problemas", len(duplicado_id_codigo)
)
```

Agregar a `error_groups`:
```python
error_groups = {
    ...
    "Duplicado ID+Código": duplicado_id_codigo,
}
```

Agregar a `resultado["problemas"]`:
```python
"duplicado_id_codigo": duplicado_id_codigo,
```

Agregar a `resultado["totales"]`:
```python
"duplicado_id_codigo": len(duplicado_id_codigo),
```

### Modified: `app/services/normalized_rows.py`

Agregar bloque después del handler de "Cups Sin Contrato" (línea 349):

```python
# --- Duplicado ID+Código ---
for item in error_groups.get("Duplicado ID+Código", []):
    factura = item.get("factura", "")
    identificacion = item.get("identificacion", "")
    codigo = item.get("codigo", "")
    proc = item.get("procedimiento", "")
    repeticiones = item.get("cantidad_repeticiones", 0)
    rows.append({
        "tipo_error": "Duplicado ID+Código",
        "factura": factura,
        "fec_factura": _get_fec_factura(factura),
        "responsable_cierra": _get_responsable(factura),
        "descripcion": (
            f"Identificación+Código duplicado "
            f"({repeticiones} veces)"
        ),
        "procedimiento": _build_procedimiento(codigo, proc),
        "detalle": f"ID: {identificacion} | Cód: {codigo}",
        "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
    })
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Columna `identificacion` no existe en Excel | `indices["identificacion"] is None` → detector retorna `[]` |
| Columna `codigo` no existe en Excel | `indices["codigo"] is None` → detector retorna `[]` |
| Columna `numero_factura` no existe | `indices["numero_factura"] is None` → detector retorna `[]` |
| Columna `procedimiento` no existe | `proc_idx is None` → se usa `""` como procedimiento (no bloquea) |
| Valor `identificacion` es `None` en una fila | `ident_str` queda `""` → `if not ident_str: continue` |
| Valor `codigo` es `None` en una fila | `codigo_str` queda `""` → `if not codigo_str: continue` |
| Valor `factura` es `None` | `normalize_invoice(None)` retorna `""` → `continue` |
| Grupo con 1 sola fila | Se ignora (no es duplicado) |
| 3+ filas con mismo ID+código | Cada fila se marca con `cantidad_repeticiones` = total del grupo |
| `error_groups` no tiene key `"Duplicado ID+Código"` | `error_groups.get("Duplicado ID+Código", [])` → no crash |

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/intramural/duplicado_id_codigo.py` | **Create** | Nuevo detector de duplicados |
| `app/services/intramural/detect_all.py` | **Modify** | Registrar detector en orquestador + `_get_intramural_detectors()` |
| `app/services/normalized_rows.py` | **Modify** | Handler para "Duplicado ID+Código" |

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Detector con 2 filas mismo ID+código | Assert 2 errores con `cantidad_repeticiones=2` |
| Unit | Detector con filas sin duplicados | Assert `[]` |
| Unit | Detector con columna faltante | Assert `[]` |
| Unit | Detector con valores None en celdas | Assert filas None son ignoradas |
| Unit | Detector con 3 filas duplicadas | Assert 3 errores con `cantidad_repeticiones=3` |
| Integration | Flujo completo con `detect_all_problems_intramural` | Assert errores aparecen en `resultado["problemas"]["duplicado_id_codigo"]` |
| Integration | `build_normalized_rows` con key "Duplicado ID+Código" | Assert filas normalizadas se generan correctamente |

---

## Open Questions

- [ ] Confirmar si la columna en el Excel Intramural se llama "Código" o "Cód. Equivalente CUPS" — afecta el `required_headers` en el caller que construye `indices`

---

## Migration / Rollout

No migration required. El sistema ya ignora keys faltantes en `error_groups` sin crash. Si se revierte, retroceder los 3 archivos.
