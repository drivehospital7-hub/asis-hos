# Proposal: Migrar detectores Intramural al procesador unificado

## Intent

Migrar los detectores específicos de Intramural (IDE Contrato) desde el worktree `feature/intramural` al unificado (`feature/procesamiento-unificado`), donde ya existe la estructura base pero los detectores específicos están placeholder.

## Scope

### In Scope

1. `app/constants/intramural.py` — copiar textual (constantes PYM, tipo factura, códigos DX)
2. `app/services/intramural/ide_contrato_rules.py` — copiar textual (mapping de reglas IDE)
3. `app/services/intramural/ide_contrato_intramural.py` — copiar textual (detector IDE)
4. `app/services/intramural/detect_all.py` — **adaptar**: integrar el detector en `_get_intramural_detectors()` y en el flujo principal
5. `app/constants/__init__.py` — agregar `from app.constants.intramural import *`

### Out of Scope

- `app/services/intramural/normalized_rows.py` — **no se migra**: el unificado ya usa `app/services/normalized_rows.py` genérico que soporta "IDE Contrato" vía `error_groups`
- `_build_totales_por_tipo()` — no se migra: el unificado ya consolida totales por tipo
- `app/services/unified_processor.py` — sin cambios: ya registra "Intramural"
- `app/constants/base.py` — sin cambios: `AREA_INTRAMURAL` ya existe

## Capabilities

### New Capabilities

- `intramural-ide-contrato`: Detección de IDE Contrato incorrecto en facturas Intramural, con reglas exactas (codigo+entidad→IDE) y reglas por ruta PYM + Dx principal

### Modified Capabilities

None — refactor interno, no cambia comportamiento de specs existentes.

## Approach

**Copy + adapt**. Archivos de datos/config (`constants/intramural.py`, `ide_contrato_rules.py`) se copian textual. El detector (`ide_contrato_intramural.py`) se copia textual porque no tiene dependencias del worktree origen. El orquestador (`detect_all.py`) se adapta para inyectar el detector en el flujo de `error_groups` y registrarlo en `_get_intramural_detectors()`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/constants/intramural.py` | New | Constantes PYM, tipo factura, códigos DX |
| `app/constants/__init__.py` | Modified | Re-export de constants.intramural |
| `app/services/intramural/ide_contrato_rules.py` | New | Mapping de reglas IDE (data/config) |
| `app/services/intramural/ide_contrato_intramural.py` | New | Detector de IDE Contrato |
| `app/services/intramural/detect_all.py` | Modified | Integrar detector en orquestador |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Los imports de constantes en el detector apuntan a `app.constants.intramural` que no existe en unificado | Low | Se crea el archivo en el mismo paso |
| `CODIGOS_PYM_INTRAMURAL` y `CODIGOS_NUEVA_EPS_NO_CAPITA` referenciados en el detector no existen en unificado | Low | Van en `constants/intramural.py` que se copia |
| `normalize_invoice` ya existe en unificado en `app.services.transversales` | None | Se verifica que el import sea compatible |
| El detector usa `openpyxl.Worksheet` y `data_sheet.cell()` — mismo patrón que el resto del unificado | None | Compatible |

## Rollback Plan

Revertir los 5 archivos tocados (`git checkout` de los 3 nuevos + `git revert` de las 2 modificaciones). Son cambios autocontenidos sin side effects en otras áreas.

## Dependencies

- Ninguna externa. Los detectores transversales ya están en el unificado.
- `app/constants/__init__.py` debe importar `intramural` después de creado el archivo.

## Success Criteria

- [ ] `_get_intramural_detectors()` retorna `[detect_ide_contrato_intramural]` en lugar de `[]`
- [ ] Las filas normalizadas incluyen errores de tipo "IDE Contrato" para Intramural
- [ ] El procesador unificado ejecuta el detector cuando "Intramural" está presente en el Excel
- [ ] `detect_all_problems_intramural()` retorna `ide_contrato` con datos en lugar de lista vacía
