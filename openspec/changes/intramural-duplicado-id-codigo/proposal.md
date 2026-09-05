# Proposal: AGREGUEMOS UNA REGLA PARA INTRAMURAL DE DUPLICIDAD SI FACTURA CON COLUMNA EXCEL "Nº Identificación" y "Código" repetido marcar error

## Intent

Evitar que una misma combinación paciente (Nº Identificación) + procedimiento (Código) se facture más de una vez en Intramural. Cuando dos o más filas comparten ambos valores, al menos una es un duplicado que debe revisarse.

## Scope

### In Scope
- Nuevo detector `detect_duplicado_id_codigo()` en `app/services/intramural/`
- Registro en el orquestador `detect_all.py` de Intramural
- Handler en `build_normalized_rows()` para el nuevo tipo de error
- Actualización de `resultado["problemas"]` y `resultado["totales"]`

### Out of Scope
- Detectar duplicados en otras áreas (Odontología, Urgencias, Equipos Básicos)
- Modificar `detect_ruta_duplicada` (transversales) — es otro concepto
- Umbrales configurables (toda repetición es error)

## Capabilities

### New Capabilities
- `intramural-duplicado-id-codigo`: Detectar filas con mismo paciente y mismo código en Intramural

### Modified Capabilities
None

## Approach

1. **Crear** `app/services/intramural/duplicado_id_codigo.py`:
   - Función `detect_duplicado_id_codigo(data_sheet, indices) -> list[dict]`
   - Recorre filas, agrupa por `(identificacion, codigo)` usando `defaultdict[list]`
   - Cada grupo con >1 elemento produce un error **por fila** con `factura`, `identificacion`, `codigo`, `procedimiento`, `cantidad_repeticiones`
   - Retorna `[]` si falta alguna columna

2. **Registrar** en `app/services/intramural/detect_all.py`:
   - Importar y llamar el detector en `detect_all_problems_intramural()`
   - Agregar grupo `"Duplicado ID+Código"` a `error_groups`
   - Agregar entrada en `resultado["problemas"]` y `resultado["totales"]`

3. **Agregar handler** en `app/services/normalized_rows.py`:
   - Nuevo bloque `# --- Duplicado ID+Código ---` que lee `error_groups.get("Duplicado ID+Código", [])`

4. **Output format** por error:
   ```python
   {
       "factura": str,
       "identificacion": str,
       "codigo": str,
       "procedimiento": str,
       "cantidad_repeticiones": int,
   }
   ```

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/intramural/duplicado_id_codigo.py` | **New** | Detector de duplicados por identificación + código |
| `app/services/intramural/detect_all.py` | Modified | Registrar detector en orquestador |
| `app/services/normalized_rows.py` | Modified | Handler para nuevo tipo de error |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Columna "Código" no existe en algunos Excels | Low | Detector retorna `[]` si falta columna (patrón estándar) |
| Falsos positivos si mismo paciente tiene mismo código en distintas facturas | Medium | Revisar con el equipo de negocio; si aplica, filtrar por factura diferente |
| `build_normalized_rows()` omite el nuevo tipo | Low | Se agrega explícitamente en la implementación |

## Rollback Plan

Revertir commits modificando los 3 archivos. Si se despliega, el sistema ignora la key faltante en `error_groups` (no crash).

## Dependencies

Ninguna.

## Success Criteria

- [ ] Dado un Excel Intramural con dos filas mismo `Nº Identificación` y `Código`, el detector las marca como error
- [ ] Dado un Excel sin columnas necesarias, detector retorna `[]` sin errores
- [ ] Los errores aparecen correctamente en la hoja de resultados exportada
- [ ] Tests unitarios pasan
