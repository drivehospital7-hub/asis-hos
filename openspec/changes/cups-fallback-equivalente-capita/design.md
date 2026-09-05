# Design: CUPS Fallback — Cód. Equivalente CUPS en Cápita

## Technical Approach

Modificación localizada en `detect_capita_cups_invalidos()` (`valida_capita.py`). Entre el chequeo principal (`codigo_str in URGENCIAS_CAPITA_CUPS_CODES`) y el marcado de error, se inserta una guard clause que lee la columna "Cód. Equivalente CUPS" (`codigo_equiv`). Si el código equivalente existe y está en el listado, la fila se considera válida y se salta el error.

No hay cambios en el orquestador (`detect_all.py`), rutas, exportación, ni otras áreas.

## Architecture Decisions

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Columna `codigo_equiv` como fallback vs. listado adicional de equivalencias | Un listado separado requeriría nueva constante, validación, y mantenimiento. Usar la columna existente es cero nuevos datos | Usar columna existente `codigo_equiv` |
| Insertar guard en `detect_capita_cups_invalidos` vs. nuevo detector | Nuevo detector = nuevo archivo + registro en orquestador + más tests. El cambio es ~8 líneas, no justifica split | Modificar función existente |
| Normalización del equivalente | Sin normalización, " 890201 " ≠ "890201". Con `.strip().upper()` hay consistencia con el código principal | Normalizar como `codigo_str` (`.strip().upper()`) |

## Data Flow

```
detect_all.py ──→ detect_capita_cups_invalidos(data_sheet, indices)
                       │
                       ├── ¿Prefijo CAP?    ─no→ continue
                       │
                       ├── ¿Código en URGENCIAS_CAPITA_CUPS_CODES?
                       │       ├── sí → continue (válido)
                       │       └── no  →
                       │              ├── leer codigo_equiv
                       │              ├── ¿existe columna?  ─no→ marcar error
                       │              ├── ¿celda no vacía?   ─no→ marcar error
                       │              ├── ¿equiv in listado? ─sí→ continue (válido por equiv)
                       │              └── no → marcar error
                       │
                       └── retorna problemas[]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/urgencias/valida_capita.py` | Modify | Insertar guard clause (~8 líneas) en `detect_capita_cups_invalidos()` entre líneas 81 y 83 |
| `tests/services/test_urgencias_capita.py` | Create | Tests unitarios para el nuevo comportamiento (crear archivo) |

## Interfaces / Contracts

Sin cambios de interfaz. `detect_capita_cups_invalidos` mantiene su firma:

```python
def detect_capita_cups_invalidos(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, str]]:
```

El dict `indices` ya contiene `"codigo_equiv"` desde `exporter.py` (columna "Cód. Equivalente CUPS").

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | CUPS no listado + equivalente válido → NO error | Crear workbook con fila CAP, código no-listado, codigo_equiv listado. Assert lista vacía |
| Unit | CUPS no listado + equivalente inválido → SÍ error | Igual pero con codigo_equiv también no-listado. Assert 1 error con observación correcta |
| Unit | CUPS no listado + codigo_equiv vacío → SÍ error | celda vacía/None. Assert 1 error (comportamiento actual preservado) |
| Unit | CUPS no listado + columna ausente → SÍ error | `indices` sin `"codigo_equiv"`. Assert 1 error |
| Unit | CUPS directamente listado → sin impacto | Código principal en listado, cualquier codigo_equiv. Assert 0 errores |

## Migration / Rollout

No migration required. Rollback = revertir commit en `valida_capita.py`.

## Open Questions

- [ ] Ninguna — el cambio está completamente especificado y acotado.
