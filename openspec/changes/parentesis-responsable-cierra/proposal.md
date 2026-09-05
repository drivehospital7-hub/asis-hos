# Proposal: Excepción responsable-urgencias en CUPS sin contrato

## Intent

`detect_cups_sin_contrato()` compara cada fila contra pares `(cod_contrato, cups)` de la cadena DB `eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`. Pero un CUPS puede existir en DB sin estar vinculado a la `nota_hoja` de cierta EPS, generando falsos positivos. Ej: VACUNACION CONTRA RABIA (cups=965201, id=347) no está ligado a nota_hoja 12 (ASMET SALUD), pero es válido cuando factura un responsable de urgencias.

## Scope

### In Scope
- Modificar `detect_cups_sin_contrato()` internamente (sin cambiar signature)
- Pre-load adicional: procedimientos vinculados a `nota_hoja id=1` ("OTRAS EPB SOLO URGENCIAS")
- En el loop de filas: si `responsable_cierra ∈ FACTURADORES_URGENCIAS`, validar contra nota_hoja id=1

### Out of Scope
- Cambios a detect_all.py de cualquier área (0 archivos)
- Nuevos detectores o archivos (0 archivos nuevos)
- Cambios de signature o interfaz

## Capabilities

### New Capabilities
None

### Modified Capabilities
- **`procedimientos-contratados`**: Se agrega una excepción — cuando `Responsable Cierra Facturar` está en `FACTURADORES_URGENCIAS`, la validación usa procedimientos de `nota_hoja id=1` en vez de la cadena contractual de la entidad. No cambia el output format ni el contrato del detector.

## Approach

Dos cambios dentro de `detect_cups_sin_contrato()`:

1. **Pre-load adicional**: query `notas_tecnicas → procedimiento` filtrado por `id_nota_hoja = 1`, guardar `set[cups]` como `nota1_cups`.
2. **En el loop**: leer `responsable_cierra` del Excel (ya mapeado en `indices`). Si `str(valor).strip().upper() in FACTURADORES_URGENCIAS`, verificar `codigo in nota1_cups` en vez de `(cod_entidad, codigo) in pares_validos`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/transversales/procedimiento_contratado.py` | Modified | Pre-load + branching interno. ~15 líneas nuevas |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `responsable_cierra` no existe en Excel | Baja | `indices.get("responsable_cierra") is None` → skip branch, usar lógica actual |
| nota_hoja id=1 no tiene procedimientos | Baja | `nota1_cups` queda vacío → urgencias facturadores ven TODO como error (conservador) |
| FACTURADORES_URGENCIAS cambia | Baja | Constante ya centralizada en `app/constants/urgencias.py` |

## Rollback Plan

Revertir las líneas agregadas en `procedimiento_contratado.py`. Sin migración, sin impacto en DB.

## Dependencies

Ninguna. `FACTURADORES_URGENCIAS` y `responsable_cierra` ya existen.

## Success Criteria

- [ ] CUPS 965201 con responsable urgencias + cualquier entidad → NO genera error
- [ ] CUPS 965201 con responsable NO urgencias → genera error si no está contratado para esa entidad
- [ ] Tests existentes (19) siguen pasando
- [ ] Sin cambios de signature ni archivos nuevos
