# Proposal: Separar Odontología de Equipos Básicos

## Intent

Equipos Básicos (EB) está acoplado a Odontología mediante un checkbox en el formulario de upload, un dispatcher en `exporter.py` que bifurca por booleano, y constantes mezcladas. Esto impide que EB funcione como área independiente y obliga a usuarios con permiso solo para EB a ver la UI de Odontología. El permiso `equipos_basicos` además está sobrecargado (controla EB + "Ordenado y Facturado"). Separar completamente las dos áreas eliminando el checkbox, creando ruta/frontend/permiso propios para EB, y desambiguando el permiso legacy.

## Scope

### In Scope
- Nueva ruta Flask y Blueprint `/odontologia-equipos-basicos/` (GET + POST)
- Nueva página React `frontend/src/pages/odontologia-equipos-basicos/`
- Nuevo permiso `odontologia_equipos_basicos` (adicional, sin migración automática)
- Mover constantes EB a `app/constants/equipos_basicos.py`
- Eliminar checkbox `equipos_basicos` de `excel_headers.html` y su JS
- Limpiar `exporter.py`: dispatcher usa `area` directamente, no booleano
- Actualizar sidebar/navegación con entrada independiente
- Actualizar templates de usuarios para incluir nuevo permiso
- Tests para la nueva ruta

### Out of Scope
- Refactor de detectores compartidos (`centro_costo.py`, `ide_contrato.py`, `normalized_rows.py`)
- Migración automática de permisos legacy `equipos_basicos` → `odontologia_equipos_basicos`
- Cambios en la página "Ordenado y Facturado" (solo se desambigua el permiso)

## Capabilities

### New Capabilities
- `odontologia-equipos-basicos`: Nueva área independiente con ruta Flask, página React, permisos propios. Cubre upload + detección de problemas + exportación para equipos básicos odontología.

### Modified Capabilities
- `admin-users-permissions`: El permiso `odontologia_equipos_basicos` se agrega como opción en `ALLOWED_PERMISOS` y en los templates de creación/edición de usuarios. El permiso legacy `equipos_basicos` queda solo para "Ordenado y Facturado".

## Approach

**Separación completa (Approach 1 de exploración)**: crear todo desde cero — Blueprint, React page, permiso, constantes — y luego eliminar el acoplamiento (checkbox, dispatcher). Los detectores compartidos se mantienen como están. Pasos: (1) nuevo permiso, (2) nuevo Blueprint, (3) nueva React page, (4) mover constantes EB, (5) sidebar/navegación, (6) limpiar checkbox + dispatcher, (7) templates de usuarios, (8) tests.

## Affected Areas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `app/routes/odontologia_equipos_basicos.py` | Nuevo | Blueprint GET + POST |
| `frontend/src/pages/odontologia-equipos-basicos/` | Nuevo | Página React (adaptada de odontología) |
| `app/constants/equipos_basicos.py` | Nuevo | Constantes EB extraídas de `odontologia.py` y `columnas.py` |
| `app/templates/excel_headers.html` | Modificado | Eliminar checkbox EB + JS condicional |
| `app/services/exporter.py` | Modificado | Dispatcher usa `area` en vez de booleano |
| `app/constants/base.py` | Modificado | Agregar `odontologia_equipos_basicos` a `ALLOWED_PERMISOS` |
| `app/routes/excel_headers.py` | Modificado | Eliminar lectura de `equipos_basicos` del form |
| `frontend/src/components/app-sidebar.tsx` | Modificado | Agregar entrada EB con nuevo permiso |
| `app/templates/base.html` | Modificado | Agregar link EB a navegación lateral |
| `app/templates/home.html` | Modificado | Mostrar link EB según nuevo permiso |
| `app/templates/usuarios.html` | Modificado | Checkbox `odontologia_equipos_basicos` |
| `frontend/src/pages/usuarios/page.tsx` | Modificado | Checkbox nuevo permiso |

## Risks

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| Usuarios con `equipos_basicos` pierden acceso a EB | Medium | Decisión explícita (Option A): NO migrar. Se asigna manualmente. |
| Template legacy usada por alguien sin React | Low | Se mantiene funcional sin checkbox; el link a EB aparecerá por separado |
| Detectores compartidos causan regression | Low | Los detectores no se modifican, solo se cambia quién los llama |

## Rollback Plan

1. Restaurar `exporter.py` a versión anterior (git checkout).
2. Revertir cambios en templates (`excel_headers.html`, sidebar, usuarios).
3. Revertir `ALLOWED_PERMISOS` en `base.py`.
4. Eliminar Blueprint nuevo y React page nueva.
5. Rollback por commit individual — cada paso es reversible independientemente.

## Dependencies

- Ninguna externa. Requiere coordinación con admins para asignar el nuevo permiso a usuarios.

## Success Criteria

- [ ] Upload de Excel EB vía `/odontologia-equipos-basicos/` funciona independientemente
- [ ] Upload de Odontología vía `/odontologia/` funciona sin checkbox EB
- [ ] Usuario con solo `odontologia_equipos_basicos` ve la UI de EB pero NO Odontología
- [ ] Usuario con solo `equipos_basicos` ve "Ordenado y Facturado" pero NO EB
- [ ] Constantes EB están en `app/constants/equipos_basicos.py`
- [ ] Checkbox EB eliminado de template y JS
- [ ] Todos los tests existentes pasan sin regresión
- [ ] Tests nuevos para la ruta `/odontologia-equipos-basicos/` pasan
