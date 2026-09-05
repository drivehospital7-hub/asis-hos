# Proposal: Facturador Urgencias — Validación contra Nota 27 para entidades no listadas

## Intent

Bugfix: CUPS 903437 (Troponina I) causa falso positivo "CUPS no contratado" cuando MEZA FERNANDEZ CARLOS OMAR factura para ESS118. ESS118 no está en `_ENTIDADES_NOTA_URGENCIAS`, por lo que el bypass de urgencias no se activa. El código cae a validación normal (`pares_validos`), donde ESS118+903437 tampoco existe, reportando error incorrectamente.

## Scope

### In Scope
- Modificar lógica de validación en `procedimiento_contratado.py` para que facturadores urgencias validen contra `nota_urgencias_cups` como fuente adicional cuando la entidad NO está en `_ENTIDADES_NOTA_URGENCIAS`
- Verificar regresión: entidades en `_ENTIDADES_NOTA_URGENCIAS` mantienen comportamiento actual

### Out of Scope
- No se modifica `_ENTIDADES_NOTA_URGENCIAS` ni `FACTURADORES_URGENCIAS`
- No se modifican otros detectores ni orquestadores
- No se agregan nuevas entidades a la lista de bypass

## Capabilities

> This is an implementation-level bugfix, not a spec-level feature change.

### New Capabilities
None

### Modified Capabilities
None

## Approach

Modificar el bloque urgencias (líneas 211-219) separando la condición existente en dos ramas:

1. **Entidad EN `_ENTIDADES_NOTA_URGENCIAS`**: comportamiento actual — si el CUPS está en `nota_urgencias_cups` (nota_hoja 1 ó 27), `continue`. Si no, cae a validación normal.

2. **Entidad NO en lista + facturador es urgencias**: verificar `nota_urgencias_cups` como fuente ADICIONAL. Si el CUPS está en `nota_urgencias_cups`, `continue`. Si no, cae a `pares_validos` (validación normal).

La esencia del cambio: quitar `cod_entidad in _ENTIDADES_NOTA_URGENCIAS` como guarda para acceder a `nota_urgencias_cups`, manteniendo `resp_name in _FACTURADORES_URGENCIAS_NORM` como único requisito para aplicar la validación adicional contra nota_hoja 1/27.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/transversales/procedimiento_contratado.py` | Modified | Líneas 211-219: separar condición urgencias en dos ramas según si entidad está en `_ENTIDADES_NOTA_URGENCIAS` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Entidades fuera de `_ENTIDADES_NOTA_URGENCIAS` podrían bajar falsos positivos (menos errores, no más) | Med | El cambio solo AÑADE una fuente de validación, no la quita. No puede crear nuevos falsos positivos |
| Regresión en entidades listadas si la lógica se cambia incorrectamente | Low | Prueba: entidades listadas con CUPS no en nota_urgencias_cups deben caer a pares_validos igual que antes |

## Rollback Plan

Revertir el cambio en `procedimiento_contratado.py` restaurando la condición original de una sola rama con `cod_entidad in _ENTIDADES_NOTA_URGENCIAS`.

## Dependencies

None.

## Success Criteria

- [ ] ESS118 + CUPS 903437 + Carlos Omar → sin error "CUPS no contratado"
- [ ] Entidades en `_ENTIDADES_NOTA_URGENCIAS` mantienen validación actual (nota_hoja 1/27 + pares_validos)
- [ ] Facturadores NO urgencias no ven cambios en validación
