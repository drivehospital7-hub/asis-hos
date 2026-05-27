# Proposal: Ruta Intramural (Scaffold)

## Intent

Crear el scaffold completo del área "Intramural" — ruta Flask, frontend React, orquestador de detección
y constantes — clonando la estructura de urgencias pero **sin reglas de negocio propias**. Solo aplica
detectores transversales existentes (decimales, tipo documento, código entidad, tipo usuario).
El cambio se realiza en una rama feature separada sin afectar `main`.

## Scope

### In Scope
- Blueprint Flask `/intramural/` con GET (React shell) y POST (upload + detección)
- Frontend React: `index.html`, `main.tsx`, `page.tsx` en `frontend/src/pages/intramural/`
- Orquestador `detect_all.py` + normalizador `normalized_rows.py` en `app/services/intramural/`
- Constantes `app/constants/intramural.py` (solo `AREA_INTRAMURAL`, vacío de reglas)
- `AREA_INTRAMURAL`, permiso `intramural` en `ALLOWED_PERMISOS`, entrada en `DASHBOARD_AREAS`
- Dispatcher `if area == AREA_INTRAMURAL` en `exporter.py` (solo transversales)
- Registro de blueprint con `url_prefix="/intramural"` en `app/__init__.py`
- Entry point Vite en `rollupOptions.input`

### Out of Scope
- Reglas de negocio específicas de intramural (no existen aún)
- Modificación de detectores transversales (se reusan tal cual)
- Tests de integración (se agregan en fase de implementación)

## Capabilities

### New Capabilities
- `intramural-deteccion`: Nueva área Intramural con upload de Excel + detección usando
  únicamente reglas transversales existentes.

### Modified Capabilities
- `admin-users-permissions`: Se agrega permiso `intramural` a `ALLOWED_PERMISOS` y
  entrada en `DASHBOARD_AREAS`.

## Approach

Copiar estructura de urgencias y simplificar: (1) constantes base, (2) Blueprint idéntico
pero con orquestador que solo llama transversales, (3) frontend React copiado renombrando
referencias, (4) registrar blueprint + permiso, (5) dispatcher en `exporter.py`,
(6) entry Vite. Todo en rama feature sin tocar `main`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/routes/intramural.py` | New | Blueprint GET + POST |
| `app/services/intramural/` | New | Package: `detect_all.py` + `normalized_rows.py` |
| `app/constants/intramural.py` | New | Constantes del dominio |
| `frontend/src/pages/intramural/` | New | React shell + bootstrap + page |
| `app/constants/base.py` | Modified | `AREA_INTRAMURAL`, `ALLOWED_PERMISOS`, `DASHBOARD_AREAS` |
| `app/services/exporter.py` | Modified | Dispatcher para `AREA_INTRAMURAL` |
| `app/__init__.py` | Modified | Registrar `intramural_bp` |
| `frontend/vite.config.ts` | Modified | Entry point en `rollupOptions.input` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `@permiso_requerido("intramural")` da 403 si no está en ALLOWED_PERMISOS | Low | Agregar permiso ANTES del Blueprint |
| Vite build falla sin entry explícito | Low | Agregar en `rollupOptions.input` simultáneamente |
| Columnas Excel incompatibles con transversales | Medium | Validar headers mínimos en pruebas manuales |
| Normalizador referencia keys de urgencias accidentalmente | Low | Crear desde 0, copiar solo lo transversal |

## Rollback Plan

1. Revertir commits en orden inverso (Vite → Blueprint → constantes → servicios nuevos).
2. Cada archivo nuevo se elimina; cada modificación se revierte con `git checkout`.
3. Al ser rama feature, main nunca se ve afectado.

## Success Criteria

- [ ] GET `/intramural/` renderiza React shell sin errores
- [ ] POST `/intramural/` con Excel válido retorna detección de transversales
- [ ] Permiso `intramural` funciona en `@permiso_requerido` y `DASHBOARD_AREAS`
- [ ] Vite build produce entry para intramural sin errores
- [ ] Ningún archivo de urgencias/odontologia/equipos_basicos fue modificado
