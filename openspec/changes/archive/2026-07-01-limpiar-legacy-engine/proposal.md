# Proposal: SDD — Limpiar legacy restante en engine

**Change name**: `limpiar-legacy-engine`
**Created**: 2026-07-01

---

## Problem statement

La migración al Rule Engine migró 35 detectores, pero **9 aún corren en modo pure legacy** (sin toggle engine, bypass completo). Adicionalmente **2 reglas de negocio no tienen equivalente engine**. Y hay **6 variables sin `else` clause** que fallarían si `is_rule_engine_enabled()` cambiara a False.

## Intent

Cerrar el círculo: que el engine sea la ÚNICA fuente de verdad para toda detección, sin código legacy ejecutándose.

## Scope

### In scope

| # | Qué | Detalle |
|---|-----|---------|
| 1 | `RevisionCantidadUrgenciasEvaluator` | Nuevo evaluador engine para urgencias |
| 2 | `CupsEquivalentesTransversalEvaluator` | Nuevo evaluador engine para unified_processor |
| 3 | Toggle engine para 9 detectores PURE LEGACY | Envolver con `if is_rule_engine_enabled():` |
| 4 | 6 `else` clauses faltantes | Agregar `else: var = []` |

### Out of scope

- Código wasteful (tipo_identificacion_entidad, codigo_entidad, etc.) — corre pero es sobrescrito. No afecta correctness.

## Approach

### Fase 1 — 2 evaluadores engine faltantes

**RevisionCantidadUrgenciasEvaluator** (operator: `revision_cantidad_urgencias_check`):
- Lógica: misma que `detect_revision_cantidad_urgencias` en `app/services/urgencias/revision_cantidad.py`
- Row-level: verifica cantidad > threshold según tipo de código
- Regla BD: `revision_cantidad_urgencias_valido`

**CupsEquivalentesTransversalEvaluator** (operator: `cups_equiv_transversal_check`):
- Lógica: mapeo de `CODIGOS_CUPS_EQUIVALENTES` en `app/services/transversales/cups_equivalentes.py`
- Row-level: si código tiene equivalente, sugerir reemplazo
- Regla BD: `cups_equivalentes_transversal`

### Fase 2 — Toggle + else clauses

**9 detectores a envolver**:

| Archivo | Detector |
|---------|----------|
| `urgencias/detect_all.py:122` | `decimales` |
| `equipos_basicos/detect_all.py:72` | `decimales` |
| `equipos_basicos/detect_all.py:87-89` | `ruta_duplicada` |
| `equipos_basicos/detect_all.py:128-137` | `cantidades_anomalas` |
| `equipos_basicos/detect_all.py:169-171` | `ide_contrato` |
| `hospitalizacion/detect_all.py:113` | `ide_contrato` |
| `hospitalizacion/detect_all.py:255` | `profesionales` |
| `urgencias/detect_all.py:289` | `revision_cantidad` |
| `unified_processor.py:269` | `cups_equivalentes_transversal` |

**6 else clauses faltantes**:
- equipos_basicos: `doble_tipo`, `centro_costo`
- hospitalizacion: `decimales`, `tipo_identificacion_edad`, `cantidades_hospitalizacion`, `cantidades_soat_hospitalizacion`

### Fase 3 — Tests

- Tests unitarios para los 2 evaluadores nuevos
- Snapshot tests engine vs legacy

## Risks

- `cups_equivalentes_transversal` está en `unified_processor.py` (fuera del flujo detect_all) — hay que integrarlo correctamente
- `revision_cantidad_urgencias` usa constantes específicas (`CODIGOS_LIMITE_ESPECIFICO`, `CODIGOS_REVISION_CANTIDAD_EXENTOS`) — replicar exactamente

## Review Workload Forecast

| Fase | Líneas | Riesgo |
|------|--------|--------|
| F1 — 2 evaluadores + reglas BD | ~120 | Bajo |
| F2 — Toggles + else | ~150 | Bajo |
| F3 — Tests | ~100 | Bajo |
| **Total** | **~370** | **Bajo** |

Budget: ~370 líneas. **No excede 400**. Single PR.
