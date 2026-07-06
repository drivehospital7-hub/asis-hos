# Proposal: Monitoreo Watchdog Automático

## Intent

Eliminar escaneos completos O(n) en cada click. Tras el primer escaneo, watchdog detecta cambios incrementalmente en background. El botón "Scanear" pasa a ser verificación de salud del watchdog.

## Scope

### In Scope
- Agregar `watchdog` a `requirements.txt`
- Crear `FolderWatcher` en `app/services/monitoreo_carpetas/watcher.py` con `ScanResult` en memoria protegido por `threading.Lock`
- `POST /scan`: primera llamada = escaneo completo + arranque watchdog daemon thread; llamadas siguientes = health check (verificar observer vivo, retornar "monitoreando")
- Watchdog monitorea roots completos para: `on_created`, `on_modified`, `on_deleted`, `on_moved`
- Cada evento watchdog: re-escaneo incremental del subtree afectado, actualiza `ScanResult` en memoria
- Daemon threads mueren con el proceso (sin shutdown hook necesario)
- Si watchdog murió (error/silencio), siguiente `POST /scan` hace fallback a full scan

### Out of Scope
- SSE / Server-Sent Events (deferido a cambio futuro)
- Snapshot persistente a disco (deferido)
- Actualizaciones en tiempo real en frontend (deferido)
- Lista de cambios acumulados mostrada al usuario (deferido)
- Watch per-factuador (se monitorean roots completos)

## Capabilities

### New Capabilities
None — no se introduce una nueva capability.

### Modified Capabilities
- `folder-scanner`: El comportamiento de escaneo pasa de stateless (cada scan = completo O(n)) a stateful (primer scan = completo, detección posterior = incremental vía watchdog). El endpoint `POST /scan` cambia su semántica: primera llamada ejecuta escaneo completo + arranca watchdog; llamadas siguientes verifican salud del watchdog sin re-escaneo.

## Approach

Approach #1 de exploration: watchdog thread con lazy start. `FolderWatcher` envuelve un `watchdog.observer` en daemon thread. En primera llamada a `POST /scan`: se ejecuta el pipeline completo actual (scan → detect → report), luego se arranca el observer sobre los roots configurados. En llamadas subsiguientes: se verifica que el observer esté alive (health check). Si murió, fallback a full scan. `ScanResult` protegido con `threading.Lock` para acceso thread-safe desde watchdog handler + Flask request threads. Los event handlers ejecutan re-escaneo del subtree afectado y actualizan el resultado en memoria.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `requirements.txt` | Modified | Add `watchdog>=4.0.0` |
| `app/services/monitoreo_carpetas/watcher.py` | New | `FolderWatcher` class con observer + state management |
| `app/services/monitoreo_carpetas/detect_all.py` | Modified | Soporte para escaneo incremental de paths específicos |
| `app/services/monitoreo_carpetas/folder_scanner.py` | Modified | Re-escaneo de un subtree sin barrer todo el root |
| `app/routes/monitoreo_carpetas.py` | Modified | POST /scan con lógica de primera vs subsiguiente llamada |
| `app/constants/monitoreo_carpetas.py` | Modified | Constantes watchdog (polling interval, event types) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Watchdog en SMB/UNC no confiable | High | Health check en cada POST /scan + fallback a full scan si watchdog murió |
| Thread safety: watchdog thread + Flask threads | Low | `threading.Lock` en toda lectura/escritura de ScanResult |
| Sin shutdown hook en waitress/Flask | Medium | Daemon threads (daemon=True) mueren con el proceso main |
| Estado en memoria se pierde al reiniciar server | Medium | Aceptable — primer scan post-reinicio hace full scan |

## Rollback Plan

Revertir cambios en `POST /scan` al comportamiento síncrono original (siempre full scan). Eliminar `watcher.py`. Remover `watchdog` de `requirements.txt`. Todos los tests existentes deben pasar sin modificaciones.

## Dependencies

- `watchdog>=4.0.0` (nueva dependencia Python, agregar a `requirements.txt`)

## Success Criteria

- [ ] Primer `POST /scan` retorna resultado completo de escaneo (≈ comportamiento actual)
- [ ] `POST /scan` subsiguiente retorna health status sin re-escaneo completo
- [ ] Watchdog observer corre en background detectando eventos de filesystem
- [ ] Re-escaneo incremental del subtree afectado funciona para created/deleted/modified/moved
- [ ] Si watchdog muere, siguiente `POST /scan` hace fallback a full scan
- [ ] Tests existentes de `folder-scanner` y `monitoreo-report` siguen pasando sin cambios
