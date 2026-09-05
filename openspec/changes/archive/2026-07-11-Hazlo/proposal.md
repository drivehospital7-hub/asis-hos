# Propuesta: Reemplazar evaluadores centro_costo con árboles de condiciones

## Intención

Eliminar la deuda técnica de `CentroCostoCheckEvaluator` y `CentroCostoIntramuralEvaluator`. Son cajas negras con 10+ reglas hardcodeadas que ignoran el contrato del árbol de condiciones. Existen 3 copias de la misma lógica (evaluator check, evaluator intramural, legacy Python). La solución es migrar cada REGLA a árboles AND/OR/NOT en `condiciones`, usando el engine existente.

## Alcance

### Incluye

1. Migrar REGLA1-9 + REVERSE del `CentroCostoCheckEvaluator` (rules 4, 27, 28, 29) a árboles de condiciones
2. Migrar reglas de `CentroCostoIntramuralEvaluator` (REGLA1-2, REGLA4, REGLA6-10, RESPONSABLE_URGENCIAS) — no tiene REGLA3
3. Definir catálogos de constantes (CODIGOS_PYP, CODIGOS_EXCEPTUADOS, CODIGOS_HOSPITALIZACION_ESTANCIA, etc.) como tablas `catalogos` o arrays JSONB en `parametros`
4. Tests de equivalencia conductual (snapshot) entre evaluador legacy y árboles nuevos
5. Eliminar `CentroCostoCheckEvaluator` y `CentroCostoIntramuralEvaluator` de `evaluators.py`
6. Marcar `apply_common_centro_costo_rules` como deprecated hasta verificación en prod

### Excluye

- Reglas extramurales de centro costo (no evaluadas por engine)
- Otros evaluadores (sala_obs_check, ent_code_match, cups_equivalentes, etc.)

## Capacidades

- **Nuevas**: None — refactor interno del motor de reglas, no introduce nuevas capacidades al sistema
- **Modificadas**: None — el comportamiento observable del engine no cambia (mismas entradas, mismas salidas)

## Enfoque

Cada REGLA bilateral se modela como `NOT(AND(premisas, NOT(conclusión)))`. Las reglas unidireccionales (REGLA8) solo tienen forward. Todas las REGLAs se combinan bajo un OR raíz (cualquier match = problema), envuelto en NOT.

```
REGLA1: cod_tipo=02 + lab=NO + no exceptuado → centro=APOYO DIAGNÓSTICO
→ NOT(AND(eq(codigo_tipo_procedimiento,02), eq(laboratorio,NO),
          NOT(cat_in(CODIGOS_EXCEPTUADOS,codigo)),
          NOT(eq(centro_costo,APOYO_DIAGNÓSTICO))))
```

Catálogos: migrar a tabla `catalogos` con operador `cat_in`, o fallback a arrays JSONB en `reglas.parametros`.

## Áreas afectadas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `app/services/engine/evaluators.py` | Eliminado | Remover ambos evaluadores centro_costo |
| `app/services/engine/condition_evaluator.py` | Modificado | Agregar operador `cat_in` para catálogos |
| `seed/migracion-engine/` | Nuevo | Migraciones SQL con árboles por dominio (odontologia, urgencias, equipos_basicos, hospitalizacion) |
| `app/services/transversales/centro_costo_rules.py` | Deprecado | Marcar como deprecated |

## Riesgos

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| Árboles no producen mismos resultados que evaluador legacy | Media | Tests de snapshot con 100+ facturas reales por dominio |
| Catálogos de constantes sin tabla/hogar definido | Media | `cat_in` con `catalogos` DB como plan A; array JSONB en parametros como fallback |
| Intramural tiene 5 reglas únicas (REGLA6/7/10, RESPONSABLE_URGENCIAS) sin equivalente en base | Media | Cada una requiere su propio sub-árbol; verificar con datos reales de intramural |

## Plan de Rollback

Por regla: mantener el evaluador legacy activo pero no usado. Si falla, cambiar `evaluator` en `reglas` de vuelta a `centro_costo_check` vía UPDATE. No eliminar código Python hasta verificación en prod completa.

## Dependencias

- Engine de condiciones AND/OR/NOT (ya implementado en `condition_evaluator.py`)
- Operador `cat_in` (nuevo) o soporte para arrays JSONB en condiciones

## Criterios de Éxito

- [ ] Cada REGLA del evaluador tiene un árbol de condiciones equivalente en DB
- [ ] Tests de snapshot: output del engine idéntico al del evaluador legacy en 100+ facturas reales por dominio
- [ ] `CentroCostoCheckEvaluator` eliminado de `evaluators.py`
- [ ] `CentroCostoIntramuralEvaluator` eliminado de `evaluators.py`
- [ ] Catálogos de constantes migrados a DB o definidos en `parametros`
