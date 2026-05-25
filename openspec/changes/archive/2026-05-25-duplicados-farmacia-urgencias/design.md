# Design: Duplicados Farmacia en Urgencias

## Technical Approach

Nuevo detector O(n) que agrupa filas de farmacia por `(factura, codigo_tipo_procedimiento)` y verifica que **todos los pares** `(codigo, cantidad)` dentro del grupo estén duplicados. Solo aplica para `codigo_tipo_procedimiento` = 09 o 12. Si algún par aparece solo una vez, el grupo NO se marca.

## Architecture Decisions

### Decision: Agrupación por (factura, tipo_proc) en vez de (factura, código, cantidad)

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **Agrupar por (factura, codigo_tipo_procedimiento)** | Regla de negocio exacta: todo el grupo debe estar duplicado | ✅ |
| Agrupar por (factura, código, cantidad) — viejo approach | No refleja la nueva semántica de "todos los pares deben repetirse" | ❌ |

**Rationale**: La lógica de negocio cambió de "cualquier par duplicado es error" a "si el tipo es 09/12, el grupo completo debe tener cada par al menos 2 veces". La agrupación por `(factura, tipo_proc)` permite contar ocurrencias por par dentro del grupo y verificar la condición ALL.

### Decision: Filtro por `codigo_tipo_procedimiento` en vez de solo tarifario viejo approach

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **Filtrar por tarifario AND tipo_proc in (09, 12)** | Sigue la nueva regla de negocio exacta | ✅ |
| Filtrar solo por tarifario | Marcaría falsos positivos para tipos que no requieren duplicidad total | ❌ |

**Rationale**: La nueva regla solo aplica a procedimientos tipo 09 y 12 dentro del tarifario farmacia. El set `CODIGOS_TIPO_PROC_09_12` ya existe en `constants/urgencias.py`.

### Decision: Output por grupo en vez de por par

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **Un item por grupo (factura, tipo_proc)** | Agrupa toda la información de pares duplicados en una sola fila | ✅ |
| Un item por par duplicado | Repite factura y tipo_proc, infla totales sin valor agregado | ❌ |

**Rationale**: Una fila por grupo con la lista de pares duplicados y el total de pares. La descripción incluye cuántos pares tiene el grupo y que todos están duplicados.

## Data Flow

```
Excel Sheet (data_sheet + indices)
        │
        ▼
detect_duplicados_farmacia()
  ├── Filtra por tarifario == VALOR_TARIFARIO_FARMACIA
  │   AND codigo_tipo_procedimiento in CODIGOS_TIPO_PROC_09_12
  ├── Dict grouping: key=(factura, codigo_tipo_procedimiento) → list[ (codigo, cantidad) ]
  ├── For each group:
  │     ├── Count occurrences of each (codigo, cantidad) pair
  │     ├── If ALL pairs have count >= 2:
  │     │     → "Duplicidad total en grupo {tipo_proc}" (flag)
  │     └── Else: skip
  └── Retorna list[dict] — 1 item por grupo con duplicidad total
        │
        ▼
detect_all.py sección 5
  ├── Llama detector, loggea count
  ├── Agrega a resultado["problemas"]["duplicados_farmacia"]
  ├── Agrega a resultado["totales"]["duplicados_farmacia"]
  └── Pasa a build_urgencias_normalized_rows()
        │
        ▼
normalized_rows.py
  └── Nueva sección "Duplicados Farmacia"
      → tipo_error = "⚠️ Revisión Necesaria"
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/urgencias/duplicados_farmacia.py` | **Modify** | Nuevo algoritmo: agrupa por (factura, tipo_proc), cuenta pares, flag ALL >= 2 |
| `app/services/urgencias/detect_all.py` | No change | Ya importa y llama el detector, mismo contrato |
| `app/services/urgencias/normalized_rows.py` | **Modify** | Adaptar sección "Duplicados Farmacia" al nuevo formato de output |
| `tests/services/test_duplicados_farmacia.py` | **Modify** | Tests actualizados para nueva lógica |

## Interfaces / Contracts

### Detector signature

```python
def detect_duplicados_farmacia(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
```

**Output item**:
```python
{
    "factura": str,
    "codigo_tipo_procedimiento": str,  # "09" or "12"
    "pares_duplicados": [
        {"codigo": str, "cantidad": int, "count": int},
        # ... (solo pares con count >= 2)
    ],
    "total_pares": int,  # total de pares únicos en el grupo
}
```

### Guard clauses
- `numero_factura` is None → return `[]`
- `tarifario` is None → return `[]`
- `codigo_tipo_procedimiento` is None → return `[]`
- `codigo` is None → saltar fila
- `cantidad` is None → tratar como 0

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Grupo 09 con todos los pares duplicados → 1 error | 4 filas (2 pares, cada par x2) |
| Unit | Grupo 09 con un par único → `[]` | 3 filas: par-A x2, par-B x1 |
| Unit | Sin filas de farmacia 09/12 → `[]` | Filas con tarifario distinto |
| Unit | Tarifario farmacia pero tipo_proc = 02 → `[]` | Fila farmacia con tipo_proc=02 |
| Unit | Columna tipo_proc faltante → `[]` | Indices sin `codigo_tipo_procedimiento` |
| Unit | Múltiples grupos: 09 con duplicidad total, 12 sin | FAC-001 grupo 09 flag, FAC-001 grupo 12 skip |
| Unit | Grupo con 3 pares distintos todos duplicados | 6 filas, 3 pares x2 cada uno |

## Migration / Rollout

No migration required. Feature replaces the previous logic entirely — the old behavior was never deployed to production (still in development).

## Open Questions

None.
