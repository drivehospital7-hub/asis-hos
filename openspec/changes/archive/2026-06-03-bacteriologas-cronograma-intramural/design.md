# Design: Bacteriólogas con Cronograma en Intramural

## Technical Approach

Nuevo detector autocontenido que itera filas de la hoja Excel, filtra por `Intramural + Tipo Procedimiento en (02,05) + Laboratorio=Si`, y valida que el profesional sea una bacterióloga programada en el cronograma del día. Se registra en `_get_intramural_detectors()` y sus errores se inyectan en `error_groups["Profesionales"]` dentro del orquestador `detect_all.py`.

Referencia: spec reglas 1-9, proposal approach section.

## Architecture Decisions

### Decision: Detector como función pura (no clase)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Clase con estado | Más boilerplate, rompe patrón existente | ❌ |
| **Función `detect_bacteriologas_cronograma(data_sheet, indices) → list[dict]`** | Misma firma que `centro_costo_intramural.py` y el resto de detectores | ✅ |

**Rationale**: El patrón existente en todo el proyecto es función → lista de errores. No hay estado compartido que justifique una clase.

### Decision: Error deduplication por factura

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Permitir múltiples errores por factura | Ruido, viola spec regla 9 | ❌ |
| **Set de facturas procesadas → max 1 error por factura** | Simple, spec-compliant | ✅ |

**Rationale**: Spec regla 9: "Una factura, un error". Usar `facturas_con_error: set[str]` para saltar si ya se reportó error para esa factura.

### Decision: `_parse_fecha` helper separada

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Inline en el detector | Testeable solo indirectamente | ❌ |
| **Función separada `_parse_fecha(val) → date \| None`** | Testeable en aislamiento, reutilizable | ✅ |

**Rationale**: El parseo de fecha tiene 3 formatos distintos + edge cases. Una función separada permite unit testing directo y evita complejidad en el detector.

## Data Flow

```
Excel rows (row=2..max_row)
    │
    ▼
[Filter: tipo_factura_descripcion == "Intramural"?]
    │ sí
    ▼
[Filter: codigo_tipo_procedimiento in ("02", "05")?]
    │ sí
    ▼
[Filter: laboratorio == "Si"?]
    │ sí
    ▼
[Filter: codigo (CUPS) NOT in EXCEPCIONES_BACTERIOLOGA?]
    │ sí (no es excepción)
    ▼
[Lookup: codigo_profesional in PROFESIONALES_URGENCIAS?]
    ├── No → error "Profesional no está en el listado de Urgencias"
    ├── Sí, tipo != "BACTERIOLOGA" → error "Profesional no es una bacterióloga"
    └── Sí, tipo == "BACTERIOLOGA" → continuar
                            │
                            ▼
[_parse_fecha(fec_factura) → date]
    │ inválida → log warning + skip row
    ▼
[get_turno_del_dia(mes, anio, dia)]
    ├── retorna [] (no hay cronograma o día sin turnos) → skip
    └── retorna turnos[]
                │
                ▼
[codigo_profesional in turnos?]
    ├── Sí → OK (no error)
    └── No → appends error a lista
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/intramural/bacteriologas_cronograma.py` | **Create** | Detector: filtros + validación contra cronograma |
| `app/services/intramural/detect_all.py` | **Modify** | Registrar detector en `_get_intramural_detectors()` + inyectar en `error_groups` + agregar a `resultado` y `totales` |
| `tests/services/test_intramural_bacteriologas_cronograma.py` | **Create** | Tests unitarios del detector |

## Interfaces / Contracts

### `bacteriologas_cronograma.py`

```python
def detect_bacteriologas_cronograma(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Detecta facturas Intramural con bacterióloga fuera del cronograma del día.

    Args:
        data_sheet: Hoja de Excel activa (openpyxl Worksheet).
        indices: Mapeo nombre_columna → índice 0-based (None si ausente).

    Returns:
        Lista de errores. Cada error tiene el formato:
        {
            "factura": str,
            "codigo_profesional": str,
            "nombre_profesional": str,
            "procedimiento": str,
            "codigo": str,           # Código CUPS del procedimiento
            "regla": str,            # "Bacterióloga debe estar en cronograma del día"
            "problema": str,         # Mensaje descriptivo
            "fec_factura": str,      # Fecha original de la factura
        }
    """
```

### Helper interno

```python
def _parse_fecha(val: Any) -> date | None:
    """Parsea fec_factura desde 3 formatos posibles.

    Formatos soportados:
    - ISO string: "2024-03-15" → datetime.strptime
    - Excel serial: 45367 → datetime.fromordinal(...)
    - Local string: "15/03/2024" → datetime.strptime

    Returns:
        date object, o None si no se pudo parsear (log warning).
    """
```

### Formato de error

```python
{
    "factura": "FAC-00123",
    "codigo_profesional": "03730",
    "nombre_profesional": "PABON GARCIA ALEJANDRA",
    "procedimiento": "Hormona Estimulante del Tiroides [TSH]",
    "codigo": "904902",
    "regla": "Bacterióloga debe estar en cronograma del día",
    "problema": "Bacterióloga 03730 no programada en cronograma para el 20/05/2026",
    "fec_factura": "20/05/2026",
}
```

### Cambio en `detect_all.py`

```python
def _get_intramural_detectors() -> list[Callable]:
    from app.services.intramural.bacteriologas_cronograma import (
        detect_bacteriologas_cronograma,
    )
    return [detect_bacteriologas_cronograma]


def detect_all_problems_intramural(...):
    # ... existing code ...

    # === NEW: bacteriólogas cronograma ===
    bacteriologas_errors = detect_bacteriologas_cronograma(data_sheet, indices)

    # error_groups
    error_groups["Profesionales"] = bacteriologas_errors

    # resultado["problemas"]
    resultado["problemas"]["profesionales"] = bacteriologas_errors

    # resultado["totales"]
    resultado["totales"]["profesionales"] = len(bacteriologas_errors)
```

## Manejo de Errores y Edge Cases

| Escenario | Comportamiento | Fundamento |
|-----------|---------------|------------|
| `indices` faltante (`numero_factura`, `codigo_profesional`, `fec_factura`) | Retorna `[]` con log warning | No se puede validar sin columnas clave |
| `codigo_tipo_procedimiento` no es `"02"` ni `"05"` | Skip silencioso | Filtro de activación (spec regla 2) |
| `laboratorio` no es `"Si"` | Skip silencioso | Filtro de activación (spec regla 2) |
| `codigo` en `EXCEPCIONES_BACTERIOLOGA` | Skip silencioso | Excepción explícita (spec regla 3) |
| `codigo_profesional` no está en `PROFESIONALES_URGENCIAS` | Error: "Profesional no está en el listado de Urgencias" | Spec regla 7 |
| `codigo_profesional` está pero `tipo != "BACTERIOLOGA"` | Error: "Profesional no es una bacterióloga" | Spec regla 7 |
| `fec_factura` no parseable | Log warning + skip | Spec regla 5 |
| `get_turno_del_dia()` retorna `[]` | Skip silencioso | Spec regla 4 |
| `codigo_profesional` no está en turnos del día | Error agregado | Spec regla 6 |
| Misma factura ya tiene error de esta regla | Skip (no duplicar) | Spec regla 9 |

## Dependencias entre Módulos

```
bacteriologas_cronograma.py
    ├── app.constants.urgencias.PROFESIONALES_URGENCIAS    (lectura)
    ├── app.constants.urgencias.EXCEPCIONES_BACTERIOLOGA   (lectura)
    ├── app.services.cronograma_bacteriologas_service.get_turno_del_dia  (llamada)
    └── app.services.transversales.normalize.normalize_invoice (helper)

detect_all.py
    ├── app.services.intramural.bacteriologas_cronograma.detect_bacteriologas_cronograma
    └── (agrega a error_groups, resultado, totales)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_parse_fecha()` — ISO string, serial Excel, local string, None, inválido | Parametrized pytest con casos borde |
| Unit | `detect_bacteriologas_cronograma()` — cada escenario del spec | Crear workbook in-memory con openpyxl, inyectar datos fila por fila |
| Unit | Filtro: skip si no es Intramural | Mockear row values |
| Unit | Excepción: código en EXCEPCIONES_BACTERIOLOGA | Assert lista vacía |
| Unit | Profesional no encontrado / no bacterióloga | Assert error específico |
| Unit | Bacterióloga en cronograma vs fuera | Mockear `get_turno_del_dia` con monkeypatch |
| Unit | Cronograma vacío (`[]`) | Assert lista vacía |
| Integration | `detect_all_problems_intramural()` incluye nuevo detector | Assert `"profesionales"` key en `resultado["problemas"]` y `resultado["totales"]` |

### Test file structure

```
tests/services/test_intramural_bacteriologas_cronograma.py
├── TestParseFecha
│   ├── test_iso_string
│   ├── test_excel_serial
│   ├── test_local_format
│   ├── test_none
│   └── test_invalid
├── TestDetectBacteriologasCronograma
│   ├── test_skip_no_intramural
│   ├── test_skip_wrong_tipo_procedimiento
│   ├── test_skip_laboratorio_no
│   ├── test_skip_excepcion_bacteriologa
│   ├── test_error_profesional_no_encontrado
│   ├── test_error_profesional_no_bacteriologa
│   ├── test_skip_cronograma_vacio
│   ├── test_error_fuera_de_cronograma
│   ├── test_ok_en_cronograma
│   ├── test_una_factura_un_error
│   └── test_fecha_invalida_skip
```

## Checklist de Implementación

- [ ] Crear `app/services/intramural/bacteriologas_cronograma.py`
  - [ ] Función `_parse_fecha()` con 3 formatos
  - [ ] Función `detect_bacteriologas_cronograma()` con algoritmo completo
  - [ ] Importar `PROFESIONALES_URGENCIAS`, `EXCEPCIONES_BACTERIOLOGA`
  - [ ] Importar `get_turno_del_dia`
  - [ ] Importar `normalize_invoice`
  - [ ] Logging con `logger = logging.getLogger(__name__)`
  - [ ] Retornar errores en formato spec
  - [ ] Deducir errores por factura (set)
- [ ] Modificar `app/services/intramural/detect_all.py`
  - [ ] Agregar `detect_bacteriologas_cronograma` a `_get_intramural_detectors()`
  - [ ] Llamar al detector en `detect_all_problems_intramural()`
  - [ ] Agregar a `error_groups["Profesionales"]`
  - [ ] Agregar a `resultado["problemas"]["profesionales"]`
  - [ ] Agregar a `resultado["totales"]["profesionales"]`
- [ ] Crear `tests/services/test_intramural_bacteriologas_cronograma.py`
  - [ ] Tests para `_parse_fecha`
  - [ ] Tests para cada escenario del spec
  - [ ] Tests de integración en `detect_all.py`
- [ ] Verificar: `python -m pytest tests/services/test_intramural_bacteriologas_cronograma.py -v`
- [ ] Verificar: `python -m pytest tests/services/test_intramural_detect_all.py -v`

## Open Questions

None — spec y proposal cubren todos los casos de borde conocidos.
