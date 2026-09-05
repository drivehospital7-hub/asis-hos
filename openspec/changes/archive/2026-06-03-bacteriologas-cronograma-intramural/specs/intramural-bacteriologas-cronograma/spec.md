# Intramural: Bacteriólogas contra Cronograma

## Descripción Funcional

Valida que facturas **Intramural** con tipo de procedimiento de laboratorio (`02` o `05`) y marcador `Laboratorio=Si` tengan como profesional atiende una bacterióloga que esté en el cronograma de turnos para la fecha de la factura.

La regla cierra un gap: existe una validación similar en Urgencias (`detect_profesionales_urgencias`) pero no se aplicaba a Intramural.

## Inputs

| Columna Excel | Índice | Propósito |
|---|---|---|
| `Tipo Factura Descripción` | `tipo_factura_descripcion` | Filtrar solo `"Intramural"` |
| `Código Tipo Procedimiento` | `codigo_tipo_procedimiento` | Debe ser `"02"` o `"05"` |
| `Laboratorio` | `laboratorio` | Debe ser `"Si"` |
| `Código Profesional` | `codigo_profesional` | Código del profesional que atiende |
| `Profesional Atiende` | `profesional_atiende` | Nombre del profesional (para el error) |
| `Fec. Factura` | `fec_factura` | Fecha para consultar cronograma |
| `Número Factura` | `numero_factura` | Identificador de factura |
| `Procedimiento` | `procedimiento` | Descripción del procedimiento |
| `Código` | `codigo` | Código CUPS del procedimiento |

## Outputs

Cada error tiene esta estructura:

```python
{
    "factura": str,                # Número de factura normalizado
    "codigo_profesional": str,     # Código del profesional
    "nombre_profesional": str,     # Nombre del profesional (columna Profesional Atiende)
    "procedimiento": str,          # Descripción del procedimiento
    "codigo": str,                 # Código CUPS del procedimiento
    "regla": str,                  # "Bacterióloga debe estar en cronograma del día"
    "problema": str,               # Mensaje descriptivo del error
    "fec_factura": str,            # Fecha de factura (para referencia)
}
```

## Reglas de Validación

1. **Filtro de fila**: La validación SHALL aplicarse solo si `Tipo Factura Descripción == "Intramural"`.
2. **Activación**: SHALL verificar que `Código Tipo Procedimiento` sea `"02"` o `"05"` Y `Laboratorio` sea `"Si"`.
3. **Excepciones**: Si `Código` (CUPS/procedimiento code) está en `EXCEPCIONES_BACTERIOLOGA` (`{"904903", "903883"}`), SHALL saltar la validación sin generar error.
4. **Cronograma inexistente**: Si `get_turno_del_dia(mes, anio, dia)` retorna lista vacía, SHALL saltar la validación sin generar error (el cronograma no existe o no tiene turnos cargados para ese día).
5. **Parseo de fecha**: SHALL parsear `Fec. Factura` completa para extraer mes, año, día como enteros. Si el formato es inválido, SHALL saltar la fila con un log warning.
6. **Validación contra cronograma**: SHALL verificar que el `Código Profesional` esté en la lista retornada por `get_turno_del_dia()`. Si NO está, SHALL generar un error.
7. **Profesional no es bacterióloga**: Si el `Código Profesional` no está en `PROFESIONALES_URGENCIAS` o su `tipo != "BACTERIOLOGA"`, SHALL saltar la validación (el profesional no es bacterióloga, la regla no aplica).
8. **Día sin turnos**: Si `get_turno_del_dia()` retorna `[]` (día sin turnos cargados), SHALL saltar sin error.
9. **Una factura, un error**: Cada factura SHALL generar a lo sumo un error de esta regla.

## Escenarios

### Happy Path
- **GIVEN** factura Intramural con `Tipo=02`, `Laboratorio=Si`, `Código Profesional=03730` (PABON GARCIA ALEJANDRA, BACTERIOLOGA), y `Fec. Factura=15/05/2026`
- **WHEN** `get_turno_del_dia(5, 2026, 15)` retorna `[{"nombre": "PABON GARCIA ALEJANDRA", "codigo": "03730 CE"}]`
- **THEN** NO se genera error

### Bacterióloga fuera del cronograma
- **GIVEN** factura Intramural con `Tipo=05`, `Laboratorio=Si`, `Código Profesional=03730`, y `Fec. Factura=20/05/2026`
- **WHEN** `get_turno_del_dia(5, 2026, 20)` retorna `[{"nombre": "PEÑA PEÑA LISBETH PAOLA", "codigo": "03375 PYM"}]`
- **THEN** se genera error: `regla="Bacterióloga debe estar en cronograma del día"`, `problema="Bacterióloga 03730 no programada en cronograma para el 20/05/2026"`

### Excepción
- **GIVEN** factura Intramural con `Tipo=02`, `Laboratorio=Si`, `Código=904903`
- **WHEN** el código está en `EXCEPCIONES_BACTERIOLOGA`
- **THEN** NO se genera error

### Cronograma inexistente
- **GIVEN** factura Intramural que cumple condiciones
- **WHEN** `get_turno_del_dia()` retorna `[]`
- **THEN** NO se genera error

### Profesional no es bacterióloga
- **GIVEN** factura Intramural con `Tipo=02`, `Laboratorio=Si`, `Código Profesional=01293` (MEDICO)
- **WHEN** el profesional no tiene `tipo == "BACTERIOLOGA"`
- **THEN** NO se genera error

### Fecha inválida
- **GIVEN** factura Intramural que cumple condiciones
- **WHEN** `Fec. Factura` tiene formato no parseable (ej. "ABC")
- **THEN** se salta la fila con log warning, sin generar error

### Profesional válido en cronograma con CE/PYM
- **GIVEN** factura Intramural con `Tipo=02`, `Laboratorio=Si`, `Código Profesional=03375`
- **WHEN** `get_turno_del_dia()` retorna `[{"nombre": "PEÑA PEÑA LISBETH PAOLA", "codigo": "03375 PYM"}]`
- **THEN** NO se genera error

### Día sin turnos cargados
- **GIVEN** factura Intramural que cumple condiciones
- **WHEN** `get_turno_del_dia()` retorna `[]` (día existe en cronograma pero sin turnos)
- **THEN** NO se genera error

## Criterios de Éxito

- [ ] El detector se registra en `_get_intramural_detectors()`
- [ ] Los errores se agregan a `error_groups["Profesionales"]`
- [ ] Factura Intramural + Tipo=02/05 + Lab=Si + bacterióloga fuera del cronograma → error
- [ ] Factura con excepción (904903 o 903883) → sin error
- [ ] Cronograma retorna `[]` → sin error
- [ ] Día sin turnos → sin error
- [ ] Profesional no es bacterióloga → sin error
- [ ] Una factura tiene a lo sumo un error de esta regla
- [ ] El formato del error coincide con el especificado

## No-requisitos

- No modifica el servicio de cronograma ni `PROFESIONALES_URGENCIAS`
- No modifica detectores de Urgencias
- No valida otros tipos de profesionales en Intramural
- No valida múltiples filas de una misma factura (usa factura única)
- No cambia `build_normalized_rows` ni `normalized_rows.py`
