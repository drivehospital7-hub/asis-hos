# Proposal: Monitoreo de Carpetas

## Intent

~15 facturadores trabajan con facturas médicas en carpetas de red compartidas, cada uno con su propia estructura. No hay visibilidad automatizada de: (1) qué facturas existen, (2) duplicados entre carpetas, (3) nombres inválidos o carpetas vacías, (4) indicadores operacionales. Esto genera errores de facturación y seguimiento manual. Necesitamos un sistema que escanee las carpetas, infiera estado desde la ruta, detecte anomalías y genere reportes.

## Scope

### In Scope
- Nuevo `app/services/monitoreo_carpetas/` — 7 archivos: scanner, inferrer, 3 validators, report_generator, detect_all orchestrator
- Escaneo automático de ~15 carpetas de facturadores (rutas configurables)
- Inferencia de estado: Verificada (LISTAS OK / CAP LISTAS), Por corregir (CORREGIR/CORRECCION), En revisión (default)
- Validación de patrones FEV (`FEV\d+`) y CAP (`CAP\d+_\w+\d+`)
- Detección de duplicados (misma factura en >1 facturador) y carpetas vacías
- Reporte Excel por factura + indicadores operacionales
- Blueprint Flask con trigger de escaneo + descarga de reporte

### Out of Scope
- File watcher en tiempo real — diferido
- Dashboard persistente con histórico — diferido
- Integración con pipeline upload/detección existente — futuro

## Capabilities

### New Capabilities
- `folder-scanner`: Recorre directorios de red configurados, lista subcarpetas de facturadores, infiere estado desde el nombre del folder padre (Verificada / Por corregir / En revisión). Tolerante a variaciones estructurales entre facturadores.
- `invoice-validator`: Valida nombres contra patrones regex FEV/CAP, detecta carpetas vacías, detecta facturas duplicadas en múltiples ubicaciones.
- `monitoreo-report`: Genera reporte Excel con datos por factura (código, tipo, estado, ruta, facturador, fecha, flags) e indicadores operacionales (total por estado, top anomalías). Usa openpyxl con estilos de `app/utils/formatting.py`.

### Modified Capabilities
- None

## Approach

Paquete standalone `app/services/monitoreo_carpetas/` siguiendo el patrón SRP + orchestrator existente (como odontologia/urgencias/equipos_basicos). Cada detector en su propio archivo, unificados por `detect_all.py`. El scanner recorre las carpetas raíz configuradas, alimenta paths a los validadores y al detector de duplicados. Resultados agregados en un dict/list, exportados vía openpyxl. Blueprint Flask provee trigger liviano. Sin cambios en la pipeline existente de upload/detección.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/monitoreo_carpetas/` | New | folder_scanner, status_inferrer, name_validator, duplicate_detector, empty_folder, report_generator, detect_all |
| `app/constants/monitoreo_carpetas.py` | New | Rutas red, regex FEV/CAP, keywords de estado, config reporte |
| `app/routes/monitoreo_carpetas.py` | New | Blueprint Flask: trigger scan + download report |
| `app/__init__.py` | Modified | Register blueprint |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Acceso a carpetas de red (latencia/permisos) | Medium | Timeout por facturador, skip graceful, log de inaccesibles |
| Diferencias estructurales entre facturadores | Medium | Inferencia por regex tolerante, excepciones documentadas |
| Scan lento con ~15 facturadores + subdirectorios | Medium | Semaphore pattern de `processor_gate.py`, timeout ajustable |

## Rollback Plan

1. Eliminar registro del blueprint en `app/__init__.py`
2. Borrar `app/services/monitoreo_carpetas/` y `app/constants/monitoreo_carpetas.py`
3. Revertir `app/routes/monitoreo_carpetas.py`
4. Cada commit es independiente — revertir en orden inverso

## Dependencies

- Unidades de red mapeadas y accesibles desde el servidor Flask
- `pathlib` + `re` (stdlib) para recorrido y matching de patrones
- `openpyxl` para reporte Excel (ya en el proyecto)

## Success Criteria

- [ ] Scan completa todas las carpetas configuradas sin excepciones no manejadas
- [ ] Inferencia de estado identifica correctamente Verificada, Por corregir, En revisión
- [ ] Nombres FEV y CAP validados contra patrones regex
- [ ] Duplicados detectados cuando misma factura existe en >1 facturador
- [ ] Carpetas vacías reportadas
- [ ] Reporte Excel contiene columnas esperadas + indicadores operacionales
- [ ] Todos los tests existentes pasan sin regresión
