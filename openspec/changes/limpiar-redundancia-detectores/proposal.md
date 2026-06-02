# Proposal: Limpiar Redundancia de Detectores en Odontología/Equipos Básicos

## Intent

Resolver la duplicación aparente entre `detect_codigo_entidad_vs_entidad_afiliacion` y `detect_tipo_identificacion_entidad` que se ejecutan juntos en odontología y equipos básicos, mientras que urgencias solo ejecuta el segundo.

## Scope

### In Scope
- Analizar qué reglas valida cada detector y determinar si son realmente redundantes
- Hacer consistente la invocación de detectores transversales de entidad entre todas las áreas
- Eliminar (o re-agregar) el detector que corresponda en cada `detect_all.py`

### Out of Scope
- Refactorizar `tipo_factura_registry.py` vs `detect_all.py` dual dispatch (problema mayor, separado)
- Optimizar rendimiento (doble iteración sobre filas — impacto despreciable)
- Agregar/eliminar detectores en áreas nuevas no listadas

## Findings (Investigación)

| Aspecto | `detect_codigo_entidad_vs_entidad_afiliacion` | `detect_tipo_identificacion_entidad` |
|---------|----------------------------------------------|--------------------------------------|
| Columnas | `codigo_entidad_cobrar`, `entidad_afiliacion`, `entidad_cobrar` | `tipo_identificacion`, `codigo_entidad_cobrar` |
| Regla | Código en columna Cód Entidad Cobrar debe coincidir con código `{XXX}` extraído de Entidad Afiliación | AS/MS requiere Cód Entidad = 86000; 86000 solo válido para AS/MS |
| Archivo | `app/services/transversales/codigo_entidad.py` | `app/services/transversales/tipo_identificacion_entidad.py` |
| Usado por odontología | Sí (vía detect_all + normalized_rows) | Sí (vía detect_all + normalized_rows) |
| Usado por equipos básicos | Sí (vía detect_all + normalized_rows) | Sí (vía detect_all + normalized_rows) |
| Usado por urgencias | No (explícitamente vacío: `[]`) | Sí (vía detect_all + build_normalized_rows) |
| Usado por ambulatoria | Sí (vía detect_all) | No |
| Usado por intramural | Sí (vía detect_all) | No |
| Usado por hospitalización | Sí (vía detect_all) | No |
| En `tipo_factura_registry.py` | Sí (como transversal para TODOS los tipos) | No |

**Conclusión**: NO son detectores duplicados. Validan reglas de negocio **distintas**. El problema real es **inconsistencia** entre áreas:

- `detect_codigo_entidad_vs_entidad_afiliacion` corre en 5 de 6 áreas (falta en urgencias)
- `detect_tipo_identificacion_entidad` corre en 3 de 6 áreas (odontología, EB, urgencias)

## Approach

### Decisión 1: Aclarar que NO son duplicados
El merge de `origin/main` trajo `detect_tipo_identificacion_entidad` como NUEVO detector transversal, no como reemplazo del viejo. Ambos deben coexistir.

### Decisión 2: Hacer consistente su uso
- `detect_codigo_entidad_vs_entidad_afiliacion`: **re-agregarlo en urgencias** si la regla aplica; mantenerlo en todas las demás
- `detect_tipo_identificacion_entidad`: **agregarlo en ambulatoria, intramural y hospitalización** si la regla aplica a esas áreas

**Alternativa**: Si business confirma que la regla de `detect_codigo_entidad_vs_entidad_afiliacion` NO aplica a urgencias, dejar como está (urgencias vacío). Pero igual hay que agregar `detect_tipo_identificacion_entidad` al resto.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/odontologia/detect_all.py` | Modified | Ajustar si se mueve a uso consistente (ningún cambio si mantenemos ambos) |
| `app/services/equipos_basicos/detect_all.py` | Modified | Idem |
| `app/services/urgencias/detect_all.py` | Modified | Re-agregar `detect_codigo_entidad_vs_entidad_afiliacion` (si aplica) |
| `app/services/ambulatoria/detect_all.py` | Modified | Agregar `detect_tipo_identificacion_entidad` |
| `app/services/intramural/detect_all.py` | Modified | Agregar `detect_tipo_identificacion_entidad` |
| `app/services/hospitalizacion/detect_all.py` | Modified | Agregar `detect_tipo_identificacion_entidad` |

## Capabilities

### New Capabilities
None — no new functionality, solo consistencia.

### Modified Capabilities
None — las reglas de negocio ya están cubiertas por detectores existentes. No cambia comportamiento en spec-level.

## Decisions Needed

1. **¿`detect_codigo_entidad_vs_entidad_afiliacion` aplica a urgencias?** Si sí, re-agregarlo. Si no, documentar por qué no aplica.
2. **¿`detect_tipo_identificacion_entidad` aplica a ambulatoria, intramural y hospitalización?** Si sí, agregarlo en sus detect_all.py. Si alguna área no maneja AS/MS o código 86000, documentarlo.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Asumir que son duplicados y eliminar uno funcional | Low (evidencia clara de reglas distintas) | Validar con business antes de merge |
| Overflow de errores si se agrega detector a área que no corresponde | Low | Confirmar reglas de negocio por área |
| Conflicto con `tipo_factura_registry.py` (dual dispatch) | Medium | No tocar registry en este cambio; solo alinear detect_all.py |

## Rollback Plan

Revertir commits de los detect_all.py modificados. Ningún cambio a detectores centrales, solo a orquestadores.

## Effort Estimate

Bajo — solo cambios de import + llamada + agregar key en resultado dict en cada detect_all.py. ~30 min efectivos.

## Success Criteria

- [ ] Ambos detectores se ejecutan consistentemente en todas las áreas donde aplican
- [ ] Urgencias documenta explícitamente por qué no usa `detect_codigo_entidad_vs_entidad_afiliacion` (con comentario en código, no silenciosamente vacío)
- [ ] `detect_tipo_identificacion_entidad` se agrega a ambulatoria, intramural y hospitalización (o se documenta por qué no aplica)
- [ ] Tests existentes pasan sin cambios en resultados esperados
