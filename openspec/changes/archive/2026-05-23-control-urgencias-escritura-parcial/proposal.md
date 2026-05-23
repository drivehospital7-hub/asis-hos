# Proposal: Control Urgencias — Escritura Parcial para Usuario Urgencias

## Intent

Usuario `urgencias` (permisos: `control_urgencias`, `facturas_abiertas`) necesita editar estado y observación del facturador, usar filtros, y ver tooltip de descripción/factura y modal de imágenes. Hoy PUT `/api/control-errores/<id>` usa `@permiso_requerido("control_urgencias:write")` bloqueando al usuario antes del service layer.

## Scope

### In Scope
- PUT decorator: `control_urgencias:write` → `control_urgencias`
- `update_error()`: reemplazar `session.get("ce_authenticated")` por verificación de `permisos`
- 9 JS guards: migrar de `window.ceAuth.isAuth()` a `window._canWrite`

### Out of Scope
- POST, DELETE, image endpoints (siguen en `:write`)
- Carga masiva, export, subir/borrar imágenes — no se habilitan
- Refactor de sistema auth

## Approach

1. **Backend**: PUT cambia decorator a `control_urgencias`. `update_error()` chequea permisos: si tiene `:write` (o `*`) → todos los campos; si solo `control_urgencias` → solo `{estado, observacion_facturador}`
2. **Frontend**: toda función JS que hoy usa `window.ceAuth.isAuth()` como guard pasa a `window._canWrite`. `handleCellClick` en observacion/factura usa `_canWrite` para decidir tooltip vs editor.

## Files

| File | Change |
|------|--------|
| `app/routes/control_errores.py:81` | PUT decorator: `:write` → `control_urgencias` |
| `app/services/control_errores_service.py:102-122` | `ce_authenticated` → verificación de `permisos` |
| `app/templates/control_errores.html` | 9 JS guards `ceAuth.isAuth()` → `_canWrite` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| urgencias edita campo prohibido vía API | Low | Backend lo rechaza — no hay bypass |
| Regresión en UI para `auditor` | Low | `:write` → `_canWrite = true` → igual que hoy |
| Confusión `isAuth` vs `_canWrite` | Med | Find-and-replace + test manual con ambos roles |

## Rollback

Un solo commit reversible: revertir decorator, revertir `update_error()`, revertir JS guards.

## Dependencies

- `session.get("permisos", [])` ya funcional desde migración auth
- `window._canWrite` ya expuesto en template via Jinja

## Success Criteria

- [ ] urgencias edita estado/obs_facturador vía PUT
- [ ] urgencias ve tooltip de observacion/factura y modal imágenes (read-only)
- [ ] urgencias NO crea, elimina, exporta, sube imágenes, ni abre carga masiva
- [ ] urgencias NO edita tipo_error, responsable, ni observacion (aunque envíe esos campos)
- [ ] `auditor` mantiene escritura completa — sin regresión
- [ ] No autenticado mantiene tooltips read-only (hoy)
