# Proposal: Cronograma Bacteriólogas

## Intent

Panel para gestionar el cronograma mensual de bacteriólogas (5 profesionales). El usuario pega texto copiado de Excel (TSV) con la distribución de turnos y el sistema lo persiste en JSON, lo muestra en tabla, y permite detectar qué bacterióloga está de servicio según fecha/hora.

## Scope

### In Scope
- Blueprint Flask + Service CRUD (mismo patrón que `abiertas_urgencias`)
- Parseo TSV → JSON (3 turnos: mañana/tarde/noche)
- Persistencia en `app/data/cronograma_bacteriologas.json`
- React page: pegar texto, guardar, ver cronograma en tabla, eliminar
- Asignación automática: dado fecha+turno → bacterióloga
- Solo admin (`*` permiso)
- Sidebar nav + Vite entry

### Out of Scope
- Envío a Control de Errores (es dominio de facturación, no aplica)
- Integración con flujo de facturación (es panel independiente)
- DB persistence (se mantiene JSON como abiertas_urgencias)

## Capabilities

### New Capabilities
- `cronograma-bacteriologas`: Schedule management for bacteriólogas — TSV paste, JSON persistence, schedule view, delete.

### Modified Capabilities
None (pure new feature, no spec-level behavior changes).

## Approach

### Backend (3 archivos nuevos, 1 modificación)

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `app/routes/cronograma_bacteriologas.py` | New | Blueprint: GET/POST/DELETE `/api/schedule`. Usa `@admin_requerido`. |
| `app/services/cronograma_bacteriologas_service.py` | New | Service CRUD. Mismo patrón: `_mes_actual()`, `get_horario()`, `save_horario()`, `delete_horario()`. |
| `app/data/cronograma_bacteriologas.json` | New | Archivo JSON (se crea automáticamente en el primer save). |
| `app/__init__.py` | Modify | Registrar blueprint con prefix `/cronograma-bacteriologas`. |

### Frontend (5 archivos nuevos, 2 modificaciones)

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `frontend/src/pages/cronograma-bacteriologas/index.html` | New | Shell HTML |
| `frontend/src/pages/cronograma-bacteriologas/main.tsx` | New | Entry React con `<AppLayout>` |
| `frontend/src/pages/cronograma-bacteriologas/page.tsx` | New | Componente: textarea paste + save + tabla de horario + detección de turno |
| `frontend/src/pages/cronograma-bacteriologas/utils.ts` | New | `parseScheduleText()`, `calcularBacteriologa()`, helper functions |
| `frontend/src/pages/cronograma-bacteriologas/constants.ts` | New | `NOMBRE_MAP` para mapeo de iniciales a nombres completos (5 bacteriólogas) |
| `frontend/vite.config.ts` | Modify | Agregar entrada en `rollupOptions.input` |
| `frontend/src/components/app-sidebar.tsx` | Modify | Agregar nav item con permiso `*` |

### JSON Structure
```json
{
  "mes": 6,
  "anio": 2026,
  "columnas": ["07:00-13:00", "13:00-19:00", "19:00-07:00"],
  "dias": [
    { "dia": 1, "manana": "KAREN", "tarde": "LISBETH", "noche": "VALENTINA" }
  ],
  "total_dias": 30
}
```

### Parseo TSV
Mismo patrón que `abiertas-urgencias/utils.ts`:
- Split por `\t`, detectar header con "DIA"/"DÍA"
- Parsear filas: `dia` (int) + 3 columnas de nombre
- Normalizar nombres cortos vía `NOMBRE_MAP`

### Detección de turno
`calcularBacteriologa(fechaStr)`:
1. Parsear fecha
2. Determinar turno por hora: mañana 06:30-12:29, tarde 12:30-18:29, noche 18:30-06:29
3. Lookup en schedule por día + turno
4. Mapear nombre corto → completo vía NOMBRE_MAP
5. Noche cruzando medianoche: si hora < 06:30, usar día anterior

### Permisos
- Backend: `@admin_requerido` (solo `*` permiso)
- Frontend: `can_write` basado en permisos (visible para admins)

## Riesgos

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| Formato TSV distinto al esperado | Baja | Parseo tolerante (fallback sin header, detecta columnas por patrón) |
| Conflicto con bacteriólogas en otros módulos | Baja | Panel independiente, no toca lógica existente |

## Rollback Plan

Revertir cambios: desregistrar blueprint, borrar archivos nuevos, revertir `__init__.py`, `vite.config.ts`, `app-sidebar.tsx`.

## Dependencias

Ninguna. Feature autónoma.

## Success Criteria

- [ ] Admin puede pegar TSV → parsear → guardar en JSON
- [ ] Admin puede ver cronograma en tabla
- [ ] Admin puede eliminar cronograma
- [ ] Dada una fecha, devuelve la bacterióloga de turno
- [ ] Usuarios sin `*` permiso no pueden acceder
