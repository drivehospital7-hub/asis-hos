## Exploration: Separar Odontología de Equipos Básicos

### Current State

**Equipos Básicos ya existe como módulo separado a nivel de servicios**, pero NO tiene independencia a nivel de rutas, frontend ni permisos.

El flujo actual es:

1. **Checkbox en el formulario de Odontología**: En `app/templates/excel_headers.html` (línea 91) hay un checkbox `equipos_basicos` dentro del formulario de upload de Odontología. También hay JS que cambia las reglas mostradas según el estado del checkbox (líneas 774-850).

2. **Ruta `/odontologia/` (POST)**: `app/routes/excel_headers.py` línea 84 — lee `request.form.get("equipos_basicos") == "on"` y lo pasa a `detect_problems_only()`.

3. **Dispatcher en `exporter.py`**: `_do_detect_problems()` (línea 161) evalúa `area_effective = AREA_EQUIPOS_BASICOS if equipos_basicos else area` y llama a `detect_all_problems_equipos_basicos()` o `detect_all_problems_odontologia()` según corresponda.

4. **Dos detectores separados**: Ambos `detect_all.py` ya existen como módulos independientes:
   - `app/services/odontologia/detect_all.py`
   - `app/services/equipos_basicos/detect_all.py`

5. **Reutilización compartida**: El módulo de equipos básicos REUTILIZA dos detectores de odontología:
   - `app/services/odontologia/centro_costo.py` — `detect_centro_costo_odontologia()` llamado con `centros_validos=[CENTRO_COSTO_EQUIPOS_BASICOS]`
   - `app/services/odontologia/ide_contrato.py` — `detect_ide_contrato_odontologia()` sin cambios
   - `app/services/odontologia/normalized_rows.py` — `build_odontologia_normalized_rows()` compartido

6. **Confusión de permisos**: El permiso `equipos_basicos` actualmente da acceso a DOS funcionalidades distintas:
   - La feature de "Equipos Básicos" (checkbox + detección diferenciada)
   - La página "Ordenado y Facturado" (`/ordenado-facturado`) que es un cruce de reportes completamente diferente

7. **Frontend React**: La página React de Odontología (`frontend/src/pages/odontologia/page.tsx`) NO tiene el checkbox de equipos básicos ni los profesionales de equipos básicos. Solo la template Jinja legacy (`excel_headers.html`) tiene esta funcionalidad.

### Affected Areas

**Servicios backend:**
- `app/services/exporter.py` — dispatcher que decide qué detect_all() llamar según `equipos_basicos` bool
- `app/services/equipos_basicos/detect_all.py` — orquestador (ya existe, no hay que crearlo)
- `app/services/equipos_basicos/profesionales.py` — detector específico (ya existe)
- `app/services/odontologia/centro_costo.py` — compartido con EB, necesita wrapper o parámetro
- `app/services/odontologia/ide_contrato.py` — compartido con EB, sin cambios necesarios
- `app/services/odontologia/normalized_rows.py` — compartido con EB, sin cambios necesarios

**Routes:**
- `app/routes/excel_headers.py` — ruta actual `/odontologia/` que maneja ambos modos vía checkbox. Habría que crear nueva ruta y limpiar el checkbox.
- `app/routes/ordenado_facturado.py` — este es OTRO feature, pero comparte permiso `equipos_basicos`
- `app/routes/home.py` — potencialmente agregar navegación a la nueva área

**Constants:**
- `app/constants/base.py` — define `AREA_EQUIPOS_BASICOS`, `ALLOWED_PERMISOS` (tiene `equipos_basicos`)
- `app/constants/odontologia.py` — tiene las constantes de equipos básicos (profesionales, thresholds) mezcladas con odontología
- `app/constants/columnas.py` — tiene `CENTRO_COSTO_EQUIPOS_BASICOS`, `EQUIPOS_BASICOS_REVISION_HEADERS`, `EQUIPOS_BASICOS_COLUMNS_TO_KEEP`

**Frontend/templates:**
- `app/templates/excel_headers.html` — template Jinja legacy con el checkbox y JS de cambio de reglas
- `frontend/src/pages/odontologia/page.tsx` — React page actual, sin soporte para equipos básicos
- `frontend/src/pages/odontologia/main.tsx` — entry point React
- `frontend/src/components/app-sidebar.tsx` — navegación, hoy asocia `equipos_basicos` a "Ordenado y Facturado"
- `app/static/react-dist/src/pages/odontologia/index.html` — HTML generado para la React SPA

**Templates legacy (Jinja):**
- `app/templates/base.html` — navegación lateral con endpoint map (línea 83: `'equipos_basicos': 'ordenado_facturado.ordenado_facturado_react'`)
- `app/templates/home.html` — verifica permiso `equipos_basicos` para mostrar link

**Tests:**
- `tests/services/test_equipos_basicos_detect_all.py` — tests del orquestador EB
- `tests/services/test_equipos_basicos_profesionales.py` — tests del detector EB
- `tests/services/test_exporter_error_paths.py` — prueba `detect_all_problems_equipos_basicos` con mock
- `tests/services/test_constants_package.py` — tests de constantes

**Configuración de permisos:**
- `app/templates/usuarios.html` — checkbox `equipos_basicos` en formulario de usuarios
- `app/utils/users_store.py` — template de permisos que incluye `equipos_basicos`
- `frontend/src/pages/usuarios/page.tsx` — React page de usuarios con permiso `equipos_basicos`

### Approaches

1. **Separación completa (ruta + frontend + permisos independientes)**
   - Crear nueva ruta `/odontologia-equipos-basicos/` (POST para procesar y GET para React shell)
   - Crear nueva página React `frontend/src/pages/odontologia-equipos-basicos/` copiando/adaptando la de odontología
   - Agregar nuevo permiso (ej: `odontologia_equipos_basicos`) separado de `equipos_basicos`
   - Desambiguar el permiso `equipos_basicos` para que solo controle "Ordenado y Facturado"
   - Eliminar el checkbox y su JS de `excel_headers.html`
   - Limpiar `exporter.py` para que el dispatcher use el área directamente en vez de un bool
   - Mover constantes de equipos básicos a su propio archivo `app/constants/equipos_basicos.py`
   - Actualizar sidebar, navegación, y templates de usuarios
   - Actualizar tests
   - **Pros**: Separación limpia, desacoplamiento total, UX claro
   - **Cons**: Mayor esfuerzo inicial, requiere migración de permisos
   - **Effort**: High

2. **Separación solo backend (misma URL, checkbox eliminado, detección automática)**
   - Detectar automáticamente si el Excel corresponde a equipos básicos vs odontología (por centro de costo o profesionales)
   - Sin cambios de ruta, sin nuevo frontend
   - **Pros**: Mínimo esfuerzo
   - **Cons**: No resuelve la confusión de permisos ni da independencia real; detección automática es frágil
   - **Effort**: Low

3. **Separación híbrida (nueva ruta pero mismo frontend/base de constantes compartida)**
   - Crear nueva ruta y Blueprint para `/odontologia-equipos-basicos/`
   - Crear nueva página React simplificada (podría reutilizar componentes)
   - Mover constantes de EB a archivo separado
   **Pros**: Balance entre esfuerzo y limpieza
   **Cons**: Sigue compartiendo detectores de odontología (centro_costo, ide_contrato)
   **Effort**: Medium

4. **Separación con refactor de detectores compartidos**
   - Igual que Approach 1, PERO además:
   - Mover `detect_ide_contrato_odontologia()` a transversales (no es específico de odontología)
   - Idem para `detect_centro_costo_odontologia()` o crear wrapper en equipos_basicos
   - Separar `normalized_rows.py` en dos o moverlo a transversales
   - **Pros**: Arquitectura más limpia a largo plazo
   - **Cons**: Mayor riesgo de regression, más archivos tocados
   - **Effort**: High

### Recommendation

**Approach 1 (Separación completa)** con estos pasos concretos:

1. **Crear nuevo permiso** `odontologia_equipos_basicos` en `ALLOWED_PERMISOS` y templates
2. **Crear nuevo Blueprint** `app/routes/odontologia_equipos_basicos.py` (GET + POST)
3. **Crear nueva React page** `frontend/src/pages/odontologia-equipos-basicos/` (copia adaptada de odontología, con los profesionales de EB)
4. **Agregar al sidebar** como entrada independiente bajo el nuevo permiso
5. **Desambiguar permiso `equipos_basicos`** → solo "Ordenado y Facturado"
6. **Mover constantes de EB** a `app/constants/equipos_basicos.py` nuevo archivo
7. **Eliminar checkbox** de `excel_headers.html` y su JS
8. **Limpiar `exporter.py`**: cambiar `equipos_basicos: bool` por `area` directamente
9. **Actualizar tests**: los existentes para EB deberían funcionar sin cambios; crear tests para la nueva ruta

Los detectores compartidos (`centro_costo.py`, `ide_contrato.py`, `normalized_rows.py`) se dejan como están por ahora — la separación no requiere moverlos. Sí se puede considerar mover `ide_contrato` a transversales en una fase posterior.

### Risks

- **Confusión de permisos**: Si se cambia `equipos_basicos` para que solo signifique "Ordenado y Facturado", los usuarios existentes con ese permiso perderán acceso a la nueva área de odontología equipos básicos. Habrá que migrar permisos O decidir que el nuevo permiso `odontologia_equipos_basicos` se asigne por separado.
- **Template legacy**: La template `excel_headers.html` sigue siendo funcional para la vista no-React. Si hay usuarios que usan esa vista, pierden el checkbox. Habría que decidir si mantener ambas o migrar completamente.
- **Dos features bajo un mismo permiso**: El hecho de que `equipos_basicos` controle tanto la detección EB como "Ordenado y Facturado" es un problema de diseño existente. Separarlos rompe la compatibilidad de permisos hacia atrás.
- **Detectores compartidos**: `centro_costo.py` recibe `centros_validos` como parámetro, y `ide_contrato.py` es 100% compartido. Cualquier cambio futuro en odontología podría afectar a equipos básicos. No es un riesgo inmediato, pero hay que documentarlo.

### Ready for Proposal

**Sí** — la exploración está completa. Hay suficiente información para avanzar a la fase de propuesta. El cambio es viable, está bien delimitado, y la mayor parte del trabajo es crear archivos nuevos más que modificar los existentes.

La recomendación es **Approach 1** (separación completa) que requiere ~8-12 archivos nuevos y ~6-8 modificaciones. El esfuerzo estimado es **High** pero el resultado es un desacoplamiento real.

> ⚠️ **Advertencia al proponente**: La decisión clave es **qué hacer con el permiso `equipos_basicos`** — si se desambigua (rompe compatibilidad) o si el nuevo permiso `odontologia_equipos_basicos` es adicional. Discutir con el usuario antes de la propuesta.
