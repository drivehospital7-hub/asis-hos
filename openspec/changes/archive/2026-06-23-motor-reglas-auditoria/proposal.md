# Proposal: Motor de Reglas con Auditoría

## Intent

19+ detectores Python hardcodeados. Umbrales en constantes. Excepciones como IFs inline. Sin trazabilidad (qué regla, qué versión, por qué). Cambiar un umbral = editar código + redesplegar. Inauditable.

**Solución**: Reglas en DB con versionado, evidencia inmutable y trazabilidad completa. Pipeline existente intacto.

## Scope

### In Scope (F1 — Fundación)
- Tablas DB: `reglas`, `condiciones`, `excepciones`, `resultados_auditoria`, `evidencias`
- `RuleEvaluator` con árboles de condiciones compuestas (AND/OR/NOT)
- Evidencia inmutable por evaluación (regla, versión, valores, resultado)
- Migración 2-3 detectores existentes como proof-of-concept
- Wrapper transparente para pipeline existente (`exporter.py`, `detect_all.py`)

### Out of Scope
- UI de administración (F2), DSL/templates (F3), paralelismo/optimización (F3), ML/multi-tenant (F4)

## Capabilities

### New
- `motor-reglas`: Motor DB-backed con condiciones compuestas, versionado y estados (draft/active/deprecated/retired). Reglas paramétricas, no enumeradas.
- `evidencia-auditoria`: Snapshot inmutable de cada evaluación: qué regla, qué versión, qué datos, qué condiciones evaluaron a qué.

### Modified
- None. El contrato del pipeline de procesamiento no cambia: mismos problemas detectados, mismo formato de salida.

## Approach

**Registry pattern** para evaluadores atómicos y data providers (extensible sin tocar el core). **Wrapper** (`RuleBasedDetector`) con idéntica interfaz que los detectores actuales. `detect_all.py` delega al wrapper. **Migración incremental**: detectores no migrados siguen con Python; migrados usan motor. Convivencia total en F1.

4 capas: Definición (DB + seeds) → Evaluación (Resolver filtra por dominio → Evaluator recorre árbol → Exception Handler → Evidence Collector) → Evidencia (snapshot inmutable) → Repositorio (consultable).

## Boundary

**Phase 1 entregable**: Reglas en DB + evidencia capturada + wrapper que mantiene el pipeline existente funcionando. El sistema se comporta igual desde afuera. La diferencia es interna: las reglas son datos, no código.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/models/` | New | Regla, Condicion, Excepcion, ResultadoAuditoria, Evidencia |
| `app/services/engine/` | New | Resolver, evaluator, exception_handler, evidence_collector |
| `app/services/engine/evaluators/` | New | Evaluadores atómicos registrables (eq, gt, lt, in, contains, regex) |
| `app/services/engine/providers/` | New | Data providers por dominio |
| `app/services/*/detect_all.py` | Modified | Wrapper opcional hacia motor |
| `app/services/transversales/` | Modified | Migración 2-3 detectores seleccionados |
| `app/services/exporter.py` | Modified | Captura de evidencia post-procesamiento |
| `app/constants/base.py` | Modified | Umbrales migrados a seeds DB |

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Condiciones como árbol compuesto (AND/OR/NOT), no lista plana | Modela reglas reales (ej: "valor > X AND convenio IN (A,B)"). Lista plana forzaría regla-por-combinación. |
| D2 | Excepción como entidad separada, no como regla | Suspende/modifica una regla existente. Si fuera regla, explotaría el catálogo. |
| D3 | Reglas paramétricas, no enumeradas | Una regla "valor_factura > {umbral}" con múltiples configuraciones de parámetros, no N reglas clonadas. |
| D4 | Resolver filtra por dominio antes de evaluar | Evita cargar y evaluar reglas de odontología en un archivo de urgencias. Eficiencia + corrección. |
| D5 | DB para comportamiento de negocio; config para operación del motor | Umbrales, condiciones y excepciones en DB (cambiables sin deploy). Timeouts, batch sizes en config. |
| D6 | Registry pattern para evaluadores y providers | Nuevos operadores (ej: `between`, `age_in_days`) se agregan sin modificar el core del motor. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Regresión en detección existente | Medium | Snapshot tests: misma entrada → mismos problemas detectados |
| Degradación de performance (DB queries por evaluación) | Medium | Precarga de reglas activas por dominio en memoria; batch insert de evidencias |
| Árbol de condiciones no cubre algún detector actual | Low | Mapeo explícito detector→árbol antes de codificar; si no mapea, se deja en Python |

## Rollback Plan

1. Feature flag `USE_RULE_ENGINE=false` → todos los detectores usan código Python legacy.
2. Si el flag no alcanza: revertir wrapper en `detect_all.py` a llamar funciones originales.
3. Tablas DB nuevas no afectan pipeline legacy — coexisten sin consumirse.

## Dependencies

- PostgreSQL con JSONB (árbol de condiciones) — disponible en stack actual
- SQLAlchemy 2.x — en uso
- Seeds SQL (sin dependencia adicional de Alembic para F1)

## Success Criteria

- [ ] 2-3 detectores migrados producen idénticos resultados que versiones Python (snapshot tests)
- [ ] `evidencias` contiene registro inmutable de cada regla evaluada (versión + valores)
- [ ] Pipeline `/procesar` funciona sin cambios de interfaz
- [ ] Rollback a detectores legacy funciona con flag de configuración
- [ ] Tests existentes pasan sin modificaciones (o con adaptación mínima documentada)
