# Proposal: CUPS Fallback — Cód. Equivalente CUPS en Cápita

## Intent

Cuando un CUPS en factura CAP (cápita) no está en `URGENCIAS_CAPITA_CUPS_CODES`, el detector `detect_capita_cups_invalidos` marca error de inmediato. Pero el Excel contiene una columna "Cód. Equivalente CUPS" (`codigo_equiv`) que puede tener un código alternativo SÍ listado. Necesitamos una verificación de respaldo: si el código principal falla, leer el equivalente y considerarlo válido si está en el listado.

## Scope

### In Scope
- Modificar `detect_capita_cups_invalidos()` en `app/services/urgencias/valida_capita.py`
- Agregar guard clause: si `codigo_equiv_idx` no es `None` y el valor equivalente está en `URGENCIAS_CAPITA_CUPS_CODES`, saltar el error
- Normalización consistente (`.strip().upper()`) del código equivalente
- Tests: agregar casos con código equivalente válido, inválido, y vacío

### Out of Scope
- No se modifican otros detectores ni áreas (odontología, equipos básicos)
- No se agregan nuevas columnas al Excel de entrada
- No se cambia la lógica de exportación ni hojas de revisión

## Capabilities

### New Capabilities
- `urgencias-capita-equivalente-cups`: Fallback validation que consulta "Cód. Equivalente CUPS" cuando el código principal no está en el listado de cápita

### Modified Capabilities
- None — no existing spec covers capita CUPS validation behavior

## Approach

Dentro del bloque actual (líneas 80-81 del archivo), después de verificar `codigo_str in URGENCIAS_CAPITA_CUPS_CODES` y ANTES de marcar error:

```python
# Verificar Cód. Equivalente CUPS como respaldo
if codigo_str not in URGENCIAS_CAPITA_CUPS_CODES:
    codigo_equiv_idx = indices.get("codigo_equiv")
    if codigo_equiv_idx is not None:
        equiv_val = data_sheet.cell(row=row, column=codigo_equiv_idx + 1).value
        equiv_str = str(equiv_val).strip().upper() if equiv_val else ""
        if equiv_str in URGENCIAS_CAPITA_CUPS_CODES:
            continue  # válido por equivalencia

    # Si llegamos acá, no hay equivalente válido → marcar error
    ...
```

Esto mantiene SRP: una sola responsabilidad por detector, y el orquestador `detect_all.py` no cambia.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/urgencias/valida_capita.py` | Modified | ~8 nuevas líneas entre chequeo principal y marcado de error |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `codigo_equiv_idx` es `None` (columna faltante) | Low | Guard clause saltea el fallback, comportamiento actual intacto |
| Celda "Cód. Equivalente CUPS" vacía | Med | `if equiv_str` saltea si está vacío/nulo |
| Falso positivo por equivalencia errónea | Low | Es el mismo listado de cápita — si el equiv está allí, el sistema lo acepta, que es el comportamiento deseado |

## Rollback Plan

Revertir el commit modificando `valida_capita.py`. El cambio es una sola función sin dependencias externas, rollback trivial.

## Dependencies

- Ninguna. `indices["codigo_equiv"]` ya se pasa desde `exporter.py` y `create_revision_sheet.py`.

## Success Criteria

- [ ] Factura CAP con CUPS no listado pero con "Cód. Equivalente CUPS" válido NO genera error
- [ ] Factura CAP con CUPS no listado y sin equivalente (o equivalente no listado) SÍ genera error
- [ ] Factura CAP con CUPS directamente en listado no se ve afectada (sigue siendo válida)
- [ ] Facturas no-CAP no se ven afectadas
- [ ] Tests existentes pasan sin modificaciones (salvo nueva cobertura)
