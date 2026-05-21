# Proposal: Reorganización de Módulos

## Intent

`revision_sheet.py` (6267 líneas) mezcla reglas de odontología, urgencias y equipos básicos con funciones duplicadas (decimales, tipo_documento), mal nombradas (`_detect_centro_costo_urgencias` hace 5 cosas en ~1800 líneas) y 3 ramas gigantes en `detect_all_problems`. `constants.py` (1346 líneas) mezcla ~18 grupos lógicos sin separación por dominio. Esto frena el mantenimiento, duplica lógica y aumenta el riesgo de regresión al agregar nuevas reglas o áreas.

## Scope

### In Scope
- `revision_sheet.py` → dividir en 3 módulos de área + transversales ampliado
- `constants.py` → convertir en package `constants/` con módulos por dominio
- `transversales/` → agregar 4 detectores parametrizados, unificar duplicaciones
- `exporter.py` → solo actualizar imports (sin cambio lógico)

### Out of Scope
- `utils/`, `routes/`, `cruce_sheet.py` — sin cambios
- `control_errores_service`, `abiertas_urgencias_service`, `genderize_*`, `derechos_extractor`, `eps_*_crud`, `notas_tecnicas_crud`, `procedimientos_crud` — NO TOCAR
- No se agregan nuevas reglas de negocio (solo reorganización)

## Capabilities

> This is a pure refactor — no new spec-level behavior. No spec files created or modified.

**New Capabilities**: None
**Modified Capabilities**: None

## Approach

### revision_sheet.py: Split POR ÁREA
Cada área (`odontologia/`, `urgencias/`, `equipos_basicos/`) tiene su propio `detect_all.py` orquestador. Reglas transversales (column_indices, ruta_duplicada, cantidades_anomalas, doble_tipo) van a `transversales/` parametrizadas por threshold/constantes. `_detect_centro_costo_urgencias` (~1800 líneas) → 5 módulos independientes (centro_costo, ide_contrato, cups_equivalentes, sala_observacion, hospitalizacion).

### constants.py: Package con fachada
`app/constants/` con `__init__.py` re-exportando TODO para backward compat total. Módulos: `base.py`, `columnas.py`, `colores.py`, `odontologia.py`, `urgencias.py`, `equipos_basicos.py`. Esto permite `from app.constants import X` sin cambios en los consumidores.

### exporter.py: Import update only
Cambiar `from app.services.revision_sheet import detect_all_problems` por `from app.services.odontologia.detect_all import detect_all_problems` (o el orquestador correspondiente según área).

### transversales/: Ampliar y unificar
- **Nuevos**: `column_indices.py`, `ruta_duplicada.py` (parametrizado: threshold configurable), `cantidades_anomalas.py` (parametrizado: constantes por área), `doble_tipo.py`
- **Unificar**: `decimales.py` — fusionar formato `list[str]` (transversales) y `list[dict]` (inline) en una única función que retorne `list[dict]`. Mantener solo versión transversales de `tipo_documento_edad.py` (es superior: mejor parsing, más campos, tipos adicionales).

## Files

| Archivo | Acción |
|---------|--------|
| `app/constants.py` | → `constants/__init__.py` (re-export) |
| `app/constants/base.py` | NEW — sheets, áreas, sufijos |
| `app/constants/columnas.py` | NEW — COLUMNS_TO_KEEP, URGENCIA_COLUMNS_TO_KEEP |
| `app/constants/colores.py` | NEW — COLOR_*, colores UI |
| `app/constants/odontologia.py` | NEW — PYP_CUPS_CODES, profesionales, IDE PyP |
| `app/constants/urgencias.py` | NEW — IDE Contrato, centros costo, SOAT, CAPITA, hospitalización |
| `app/constants/equipos_basicos.py` | NEW — thresholds, profesionales EB |
| `app/services/transversales/column_indices.py` | NEW — _get_column_indices |
| `app/services/transversales/ruta_duplicada.py` | NEW — parametrizado |
| `app/services/transversales/cantidades_anomalas.py` | NEW — parametrizado |
| `app/services/transversales/doble_tipo.py` | NEW |
| `app/services/transversales/decimales.py` | MODIFY — unificar formatos |
| `app/services/transversales/tipo_documento_edad.py` | MODIFY — adoptar como única |
| `app/services/transversales/__init__.py` | MODIFY — re-export nuevos |
| `app/services/odontologia/__init__.py` | NEW |
| `app/services/odontologia/detect_all.py` | NEW — orquestador |
| `app/services/odontologia/profesionales.py` | NEW |
| `app/services/odontologia/centro_costo.py` | NEW |
| `app/services/odontologia/ide_contrato.py` | NEW |
| `app/services/urgencias/__init__.py` | NEW |
| `app/services/urgencias/detect_all.py` | NEW — orquestador |
| `app/services/urgencias/centro_costo.py` | NEW — reglas 1-9 + REVERSE |
| `app/services/urgencias/ide_contrato.py` | NEW — ~30 reglas IDE |
| `app/services/urgencias/cups_equivalentes.py` | NEW — 890201, 129B01, 890205 |
| `app/services/urgencias/sala_observacion.py` | NEW — estancia, SOAT |
| `app/services/urgencias/hospitalizacion.py` | NEW — códigos oblig/prohibidos |
| `app/services/urgencias/profesionales.py` | NEW — 7 tipos |
| `app/services/urgencias/mal_capitado.py` | NEW — FEV/CAP |
| `app/services/urgencias/cantidades.py` | NEW — urgencias, SOAT, hosp |
| `app/services/urgencias/revision.py` | NEW — entidad 86, cantidad |
| `app/services/urgencias/codigos_db.py` | NEW — _get_codigos_no_en_db_ess118 |
| `app/services/urgencias/ide_contrato_reverse.py` | NEW |
| `app/services/equipos_basicos/__init__.py` | NEW |
| `app/services/equipos_basicos/detect_all.py` | NEW — orquestador |
| `app/services/equipos_basicos/profesionales.py` | NEW |
| `app/services/exporter.py` | MODIFY — imports |
| `app/services/revision_sheet.py` | DELETE |

## No Tocar

| Módulo | Razón |
|--------|-------|
| `utils/formatting.py` | Formato condicional, no tiene lógica de área |
| `utils/column_filter.py` | Filtrado genérico de columnas |
| `utils/input_data.py` | Paths seguros, sin reglas de negocio |
| `utils/validators.py` | Validación genérica de paths |
| `utils/auth*.py`, `utils/db_config.py`, `utils/errores_storage.py` | Infraestructura |
| `routes/*` | Capa HTTP, sin lógica de negocio |
| `cruce_sheet.py` | Hoja CruceFacturas, independiente |
| `excel_column_headers.py`, `excel_headers_page.py` | Lectura de headers |
| `responsables.py`, `check.py` | Utilidades menores |
| `control_errores_service.py` | Módulo error aparte, bien separado |
| `abiertas_urgencias_service.py` | Funcionalidad independiente |
| `genderize_*` | Feature independiente |
| `derechos_extractor.py` | Funcionalidad aparte |
| `eps_*_crud.py`, `notas_tecnicas_crud.py`, `procedimientos_crud.py` | CRUDs independientes |

## Execution Order

| Fase | Qué | Depende de | Riesgo |
|------|-----|-----------|--------|
| 1. constants/ package | Crear estructura, re-exportar todo, verificar imports | — | Bajo |
| 2. transversales/ nuevos | column_indices, ruta_duplicada, cantidades_anomalas, doble_tipo | Fase 1 | Bajo |
| 3. Unificar transversales | decimales (fusionar), tipo_documento_edad (adoptar versión única) | Fase 2 | Medio |
| 4. odontologia/ | detect_all + profesionales, centro_costo, ide_contrato | Fase 3 | Medio |
| 5. urgencias/ | detect_all + 11 módulos. **Split centro_costo_urgencias** | Fase 3 | **Alto** |
| 6. equipos_basicos/ | detect_all + profesionales | Fase 3, 4 | Bajo |
| 7. Cleanup | exporter imports, eliminar revision_sheet.py | Todas | Medio |

## Risks

| Riesgo | P | I | Mitigación |
|--------|---|---|------------|
| Regresión reglas de negocio | High | Critical | Mover UNA regla a la vez. Validar cada fase con archivos Excel reales de producción. No big-bang. |
| Ruptura imports | Med | High | constants `__init__.py` como fachada. Tests de import después de cada fase. |
| IDE Contrato Urgencias acoplado | High | High | Las ~30 reglas están entremezcladas con centro costo en el mismo loop. Extraer UNA sub-regla a la vez, refactorizando el loop gradualmente. |
| Sin tests automatizados | High | High | Archivos Excel con casos conocidos como test suite manual. Cada fase produce el mismo output. |
| Inconsistencia formatos retorno | Med | Med | decimales: unificar a `list[dict]`. Revisar consumidores (templates, detect_all). |

## Rollback Plan

1. **Por fase**: Cada fase es un commit independiente y reversible.
2. **constants fachada**: Mientras `constants.py` exista como archivo único, revertir es trivial (eliminar `constants/`, restaurar `constants.py`).
3. **revision_sheet.py**: No se elimina hasta la Fase 7. Hasta entonces, ambos caminos coexisten.
4. **Comando**: `git revert <commit-hash>` de la fase problemática. Si hay dependencias, revertir en orden inverso (Fase 7 → Fase 1).

## Success Criteria

- [ ] Mismos problemas detectados con mismos mensajes que antes (comparar output con archivos Excel reales)
- [ ] Todos los imports resueltos sin errores (`from app.constants import X`, `from app.services.odontologia import detect_all`)
- [ ] Cero funciones duplicadas entre `transversales/` y módulos de área
- [ ] `revision_sheet.py` eliminado sin regresión
- [ ] `constants.py` eliminado sin regresión (todo via `constants/` package)

## Effort

| Métrica | Valor |
|---------|-------|
| Archivos creados | ~25 |
| Archivos modificados | ~8 |
| Archivos eliminados | 1 (revision_sheet.py) + 1 (constants.py) |
| Líneas nuevas | ~2500 |
| Líneas eliminadas | ~6500 (neto: -4000) |
| Complejidad | **ALTA** — riesgo de regresión en reglas críticas de facturación |
| Fases | 7 secuenciales, cada una validada con Excel real |
