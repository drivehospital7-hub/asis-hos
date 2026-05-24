## Exploration: Estandarización Visual y CSS

### Current State

**Stack CSS**: 100% custom — sin Bootstrap, Tailwind, ni ningún framework externo. Sin CDNs, sin icon fonts, sin imágenes externas. Sin favicon.

**Archivos CSS**: Solo 2 archivos en `app/static/css/`:
- `base.css` (367 líneas) — Reset, custom properties (:root), layout (`.layout__*`), typography, home page, area cards
- `components.css` (537 líneas) — Componentes reutilizables BEM-lite: card, form, buttons, alerts, table, modal, login modal, disabled/auth states

**JS**: Solo 2 archivos en `app/static/js/` — `auth.js` (60 líneas) y `form-loading.js` (43 líneas). Sin framework JS frontend.

**Assets**: CERO imágenes, iconos, fuentes o favicon en `static/`. Todos los iconos son SVG inline en los templates.

**Templates**: 12 archivos HTML. 8 heredan de `base.html`, 3 son standalone (sin herencia), `unauthorized.html` extiende base.html sin contenido.
- **Standalone**: `login.html`, `usuarios.html`, `import_facturas.html`
- **Heredan**: `home.html`, `urgencias.html`, `control_errores.html`, `abiertas_urgencias.html`, `ordenado_facturado.html`, `excel_headers.html`, `derechos.html`, `unauthorized.html`

**Problemas críticos detectados**:

1. **Duplicación masiva de CSS vía `<style>` embebidos** — 8 templates tienen bloques `<style>`. Dos templates (`control_errores.html` ~1115 líneas, `abiertas_urgencias.html` ~541 líneas) re-definen COMPLETAMENTE componentes que ya existen en components.css: `.table`, `.btn`, `.btn--primary`, `.btn--secondary`, `.badge`, `.empty-state`, `.modal`, `.btn--small`, etc. Esto es mantenimiento imposible y estilo que diverge.

2. **82 estilos inline** repartidos en todos los templates — para `display:none`, colores, paddings, widths. Concentrados principalmente en `control_errores.html` (JS que inyecta HTML con `style=`), `ordenado_facturado.html`, `excel_headers.html`.

3. **Redefinición inconsistente de botones** — Cada template que se toma el trabajo redefine `.btn--primary` con su propio color:
   - `components.css`: `#4a6fa5` (azul-gris)
   - `control_errores.html`: `#0f172a` (casi negro) + `transform: translateY(-1px)` + box-shadow
   - `abiertas_urgencias.html`: `#0f172a` (casi negro)
   - `login.html`: `#0066cc` (azul brillante)
   - `usuarios.html`: `#0066cc` + `#cc3300` para danger + `#6c757d` para secondary
   - `import_facturas.html`: `#007bff` (azul Bootstrap)

4. **Custom Properties subutilizadas** — Las variables CSS de `:root` en base.css están bien definidas (paleta, espaciado, tipografía, bordes, sombras), pero los bloques `<style>` embebidos y los estilos inline usan valores hardcodeados (`#64748b`, `#e2e8f0`, `#0f172a`, `#3b82f6`, `#94a3b8`) ignorando completamente el design system.

5. **Layout duplicado** — `.layout__header` está definido 2 veces en base.css (líneas 6-10 y 181-185) con propiedades casi idénticas.

6. **Login inconsistente** — `login.html` es standalone con su propio set de CSS (fondo `#f5f5f5`, botón `#0066cc`, card `max-width:360px`). El login modal (easter egg) en base.html usa CSS de components.css (`.login-modal`, `max-width:20rem`). NO comparten estilos. Visualmente diferentes.

7. **`usuarios.html` standalone** — No extiende base.html, tiene su propio `<style>`, su propia navbar (inexistente, solo un link "← Volver al inicio"), sus propios flash messages. No tiene nav del layout principal.

8. **`import_facturas.html` standalone** — Similar, sin nav, sin layout, sin consistencia visual con el resto del sistema.

9. **Estados faltantes** — No hay `:focus-visible` globalmente (solo en `control_errores.html`), los modales no tienen animación de entrada, el empty state está definido en components.css pero no se usa consistentemente, falta estado `:focus` para `btn--ghost`.

10. **Responsive casi inexistente** — Solo `control_errores.html` y `abiertas_urgencias.html` tienen `@media (max-width: 768px)` queries. base.css no tiene ningún breakpoint.

11. **No hay página de loading/error global** — `unauthorized.html` solo extiende base.html con `{% block content %}{% endblock %}` vacío.

12. **`home.html`** — Es el template más limpio. Usa exclusivamente clases de `base.css` (`.area-card__*`, `.home__*`). Sin estilos inline, sin `<style>` embebido. Modelo a seguir.

### Affected Areas

- `app/static/css/base.css` — Custom properties, layout, home page. `.layout__header` duplicado (líneas 6 y 181). Sin responsive. Sin estados focus.
- `app/static/css/components.css` — Componentes compartidos. Muchos se sobreescriben en templates. Sin cobertura completa (falta spinner, skeleton, etc.)
- `app/templates/base.html` — Layout principal, nav, flash messages, login modal (easter egg), auth JS
- `app/templates/login.html` — Standalone, CSS duplicado sin conexión con el design system del proyecto
- `app/templates/home.html` — El más limpio, referencia de "cómo deberían verse todos"
- `app/templates/control_errores.html` — ~1115 líneas de CSS embebido, redefine todo
- `app/templates/abiertas_urgencias.html` — ~541 líneas de CSS embebido, redefine todo
- `app/templates/urgencias.html` — CSS mínimo embebido (solo `.row-fecha-cierre-vacia`)
- `app/templates/ordenado_facturado.html` — Múltiples estilos inline (al menos 10+)
- `app/templates/excel_headers.html` — Calendar grid CSS en bloque `<style>`, modales con inline `style="display:none"`
- `app/templates/derechos.html` — CSS en `<style>` para layout específico de derechos
- `app/templates/usuarios.html` — Standalone, CSS completo duplicado
- `app/templates/import_facturas.html` — Standalone, CSS completo duplicado, inline styles

### Approaches

1. **Refactor Progresivo (recomendado)** — Migrar los estilos embebidos e inline a un nuevo tier de archivos CSS (page-specific), luego unificar el design system usando las custom properties existentes, y finalmente estandarizar el visual de los standalone templates.
   - Pros: Bajo riesgo, se puede hacer en etapas, permite priorizar templates de alto uso, compatible con el workflow existente
   - Cons: Requiere más sesiones de implementación, no hay "antes/después" dramático hasta el final
   - Effort: High (pero dividido en slices)

2. **Migración Directa a Design System** — Crear un archivo `design-system.css` con tokens y componentes, refactorizar `base.css` y `components.css` para usarlo, y convertir todos los templates de una pasada.
   - Pros: Resultado consistente inmediato, una sola transformación
   - Cons: Riesgo alto de romper funcionamiento, requiere probar 12 templates simultáneamente, effort enorme en una sola tanda, difícil de review
   - Effort: High (más riesgoso)

3. **Solo Crítica: Unificar Login + Standalones** — Enfoque mínimo: refactorizar solo los 3 templates standalone (login.html, usuarios.html, import_facturas.html) para que extiendan base.html, y extraer el CSS embebido más grande (control_errores.html + abiertas_urgencias.html) a archivos page-specific.
   - Pros: Menor esfuerzo, impacto visual inmediato en login y usuarios
   - Cons: No resuelve la raíz del problema (falta de page-specific CSS tier, design system no usado)
   - Effort: Medium

### Recommendation

**Approach 1 (Refactor Progresivo)**, ejecutado en este orden:

1. **Fase 1 — Foundation**: Crear `app/static/css/pages/` directorio. Extraer el CSS embebido de `control_errores.html` → `pages/control-errores.css` y `abiertas_urgencias.html` → `pages/abiertas-urgencias.css`. Los bloques `<style>` se reemplazan por `<link>`.

2. **Fase 2 — Unificar design tokens**: Asegurar que todos los colores hardcodeados en los page CSS se reemplacen por las custom properties de base.css. Donde falten tokens, agregarlos a `:root`.

3. **Fase 3 — Estandarizar componentes**: Refactorizar `components.css` para cubrir las variantes de botón/table/badge que hoy existen solo en page CSS. Eliminar las redefiniciones en page CSS.

4. **Fase 4 — Migrar standalone templates**: Convertir `login.html`, `usuarios.html`, `import_facturas.html` para que extiendan `base.html`. Extraer CSS específico a page files.

5. **Fase 5 — Polishing**: Remover estilos inline. Agregar responsive base (breakpoint en base.css). Agregar `:focus-visible` global. Agregar favicon.

**Razón**: El Approach 1 controla el riesgo porque cada fase produce un cambio atómico y verificable. La Fase 1 sola ya limpia 1600+ líneas de templates. El projecto tiene un SDD session activo y se beneficia de cambios incrementales.

### Risks

- **Riesgo de regresión visual**: Templates como `control_errores.html` usan CSS que difiere del components.css por diseño (slate palette vs. blue-grey). Migrar a componentes compartidos puede cambiar colores intencionales. **Mitigación**: Fase 2 (tokens) antes de Fase 3 (componentes). Preservar la paleta slate en customs properties nuevas.
- **Riesgo de JS que depende de estilos específicos**: El JS en `control_errores.html` inyecta HTML con `style=` inline. Refactorizar esto requiere modificar JS que construye strings HTML.
- **Riesgo de alcance**: 3 templates standalone (`login.html`, `usuarios.html`, `import_facturas.html`) necesitan más que solo CSS — necesitan refactor de herencia de template. Esto toca tanto backend (rutas/views) como frontend.

### Ready for Proposal

Yes — el análisis está completo. El orchestrator debe decirle al usuario que se recomienda **Refactor Progresivo en 5 fases**, empezando por extraer el CSS embebido de los templates más pesados a archivos page-specific como primer cambio atómico. La exploración identificó que el login y los templates standalone necesitan cambios tanto de template (herencia) como de CSS — esto tiene implicaciones de backend que deben aclararse antes del proposal.
