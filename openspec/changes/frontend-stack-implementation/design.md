# Design: React + Vite Frontend Integration

## Technical Approach

Hybrid Flask+React MPA: `frontend/` Vite project builds per-page entry points to `app/static/react-dist/`. Flask serves a thin `react_shell.html` that extends existing `base.html` — sidebar, auth, and layout stay server-rendered. Each React page reads server-provided data from `window.__INITIAL_DATA__` on mount. Phase 1 targets only `abiertas-urgencias`, matching `data/import/abiertas-urgencias.tsx` pixel-for-pixel.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Vite project location | `frontend/` vs `app/react/` | `frontend/` avoids Python tool confusion (noise in `pip list`, `pytest` scanning node_modules) | `frontend/` at repo root |
| Dev serving | Vite proxy (HMR) vs Flask serves built | Proxy needs CORS, extra Flask config; built files are simplest for Phase 1 | Flask serves built artifacts |
| Build output | `app/static/react-dist/` vs symlink | Direct folder under Flask static → free serving via `/static/react-dist/` | `<project>/app/static/react-dist/` |
| Asset discovery | Vite manifest.json vs glob | Manifest is the Vite-native approach, robust against hash changes | Use `manifest.json` from Vite build |
| Data injection | `window.__INITIAL_DATA__` vs inline script tag | `__INITIAL_DATA__` is simpler and keeps template clean | Jinja2 sets JSON in `react_shell.html` |
| Collapsible cards | shadcn Collapsible vs state toggle | tsx reference uses `useState` — no Collapsible import. Follow the reference. | Plain `useState<boolean>` |
| Routing | TanStack Router vs no router | MPA means Flask handles URL → page mapping. No SPA router needed. | No router (Phase 1) |
| Tailwind version | CDN only vs npm only vs both | npm Tailwind v4 is required for `@tailwindcss/vite` plugin; CDN stays for legacy pages | Both: CDN in `base.html`, npm in Vite build, same CSS vars in both |

## Data Flow

```
Flask HTTP Request  ──→  /abiertas-urgencias/react
                              │
                              ▼
                    Route handler fetches data
                    (schedule, user info, permissions)
                              │
                              ▼
                    Renders react_shell.html
                    with __INITIAL_DATA__ JSON
                              │
                              ▼
                    Browser loads:
                      base.html (sidebar, auth, layout)
                        └─ react_shell.html (extends)
                            ├─ <div id="root">
                            └─ <script src="react-dist/...">
                              │
                              ▼
                    React mount → reads window.__INITIAL_DATA__
                              │
                              ▼
                    React renders AbiertasUrgenciasPage
                              │
                              ├─ GET /abiertas-urgencias/api/schedule  (mount)
                              ├─ POST /abiertas-urgencias/api/schedule (save)
                              └─ DELETE /abiertas-urgencias/api/schedule (delete)
```

All API calls use `credentials: "same-origin"` — Flask session cookie flows automatically.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/package.json` | Create | Vite project: React 19, TypeScript, Tailwind v4, shadcn/ui, lucide-react |
| `frontend/vite.config.ts` | Create | Multi-page rollup input, build → `../app/static/react-dist/`, manifest |
| `frontend/tsconfig.json` | Create | TypeScript config with `@/` path alias → `./src/` |
| `frontend/index.html` | Create | Per-page HTML shell (Vite entry for multi-page) |
| `frontend/src/main.tsx` | Create | Shared entry: reads `__INITIAL_DATA__` + renders page |
| `frontend/src/styles/globals.css` | Create | `@import "tailwindcss"` + shadcn CSS vars matching `main.css` oklch tokens |
| `frontend/src/lib/utils.ts` | Create | `cn()` from `clsx` + `tailwind-merge` |
| `frontend/src/components/ui/button.tsx` | Create | shadcn button (added via `npx shadcn@latest add button`) |
| `frontend/src/components/ui/card.tsx` | Create | shadcn card (added via `npx shadcn@latest add card`) |
| `frontend/src/components/breadcrumbs.tsx` | Create | Custom nav with `ChevronRight` separator |
| `frontend/src/components/page-title.tsx` | Create | PageTitle: eyebrow + h1 + description + actions slot |
| `frontend/src/pages/abiertas-urgencias/main.tsx` | Create | Entry: imports + renders `AbiertasUrgenciasPage` |
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Create | Main component: 3 cards, schedule table, asignar section |
| `app/templates/react_shell.html` | Create | Extends `base.html` — `<div id="root">` + `__INITIAL_DATA__` + script |
| `app/routes/abiertas_urgencias.py` | Modify | Add `GET /abiertas-urgencias/react` serving `react_shell.html` |
| `.gitignore` | Modify | Add `frontend/node_modules/`, `app/static/react-dist/` |
| `app/__init__.py` | No change | Existing `abiertas_urgencias_bp` already registered; new route lives in same blueprint |

## Key Code Patterns

### `vite.config.ts`

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/static/react-dist/",
  build: {
    outDir: "../app/static/react-dist",
    emptyOutDir: true,
    cssCodeSplit: false,
    manifest: "manifest.json",   // ← asset discovery for Flask
    rollupOptions: {
      input: [
        path.resolve(__dirname, "index.html"),
        // Future pages add entries here:
        // path.resolve(__dirname, "src/pages/other-page/index.html"),
      ],
    },
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
```

### Flask: asset discovery & route

**`app/routes/abiertas_urgencias.py`** — add:

```python
import json
from pathlib import Path

@abiertas_urgencias_bp.get("/react")
@permiso_requerido("facturas_abiertas")
def abiertas_urgencias_react():
    """React shell for Abiertas Urgencias."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "facturas_abiertas:write" in permisos

    # Read Vite manifest to find hashed asset filename
    manifest_path = Path(app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "index.html", "file")

    return render_template(
        "react_shell.html",
        entry_js=entry_js,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "is_auth": True,
        },
    )


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")
```

### `react_shell.html`

```html
{% extends "base.html" %}

{% block title %}Abiertas Urgencias — React{% endblock %}

{% block content %}
<div id="root"></div>
<script>
  window.__INITIAL_DATA__ = {{ initial_data | tojson | safe }};
</script>
<script src="{{ url_for('static', filename='react-dist/' + entry_js) }}"></script>
{% endblock %}
```

### `globals.css` — theme sync

```css
@import "tailwindcss";

@theme {
  /* Match main.css oklch tokens exactly */
  --color-background: oklch(0.975 0.012 85);
  --color-foreground: oklch(0.22 0.03 165);
  --color-primary: oklch(0.32 0.055 165);
  --color-primary-foreground: oklch(0.975 0.012 85);
  --color-secondary: oklch(0.42 0.07 162);
  --color-secondary-foreground: oklch(0.98 0 0);
  --color-muted: oklch(0.94 0.012 100);
  --color-muted-foreground: oklch(0.45 0.025 160);
  --color-card: oklch(1 0 0);
  --color-card-foreground: oklch(0.22 0.03 165);
  --color-border: oklch(0.88 0.015 130);
  /* ... remaining tokens from main.css */
}
```

The shadcn `components.json` will reference these `@theme` tokens. Keep both `main.css` (CDN) and `globals.css` (npm) in sync — same oklch values, declared once in the `@theme` block.

## Interfaces / Contracts

```typescript
// Data flowing from Flask → React
interface InitialData {
  can_write: boolean;
  username: string;
  is_auth: boolean;
}

// Schedule day row (matches Flask API response)
interface ScheduleDay {
  dia: number;
  manana: string;
  tarde: string;
  noche: string;
}

// PageTitle component props
interface PageTitleProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

// Breadcrumbs component props
interface BreadcrumbsProps {
  items: Array<{ label: string; href?: string }>;
}
```

## Component Architecture

```
AbiertasUrgenciasPage
├── Breadcrumbs          items=[{ label: "Abiertas Urgencias" }]
├── PageTitle            eyebrow, title, description, actions (Button "Volver a control")
├── AssignSection        collapsible Card: textarea + Asignar button
│   └── [ResponsableResultTable]  (rendered after processing, inline in same card)
├── ScheduleSection      collapsible Card: ScheduleTable (3 shifts + empty state)
└── WarningCard          Card: AlertCircle + "Editar" + "Cargar" buttons
```

State lives in `AbiertasUrgenciasPage` via `useState` — no global store needed for Phase 1.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (React) | Component render, collapsible toggle | Vitest + React Testing Library (deferred to Phase 2 per proposal) |
| Integration | Vite build produces expected assets in `react-dist/` | Manual `npm run build` + verify `manifest.json` has entry |
| Integration | Flask route returns `react_shell.html` with data | `pytest` — `client.get("/abiertas-urgencias/react")` asserts 200, response contains `__INITIAL_DATA__` |
| E2E | Page renders visually matching tsx reference | Manual browser check (Phase 1, no Playwright yet) |

## Migration / Rollout

No data migration. The existing Jinja2 route at `/abiertas-urgencias/` is untouched. The new React route at `/abiertas-urgencias/react` is additive. Rollback: remove the `/react` route, template, and `frontend/` directory. Zero risk to existing functionality.

## Execution Steps

1. **Scaffold**: `npm create vite@latest frontend -- --template react-ts` then `cd frontend && npm install`
2. **Install deps**: `npx shadcn@latest init` (configure `@/` alias, CSS vars), then `npx shadcn@latest add button card`
3. **Add packages**: `npm install lucide-react clsx tailwind-merge`
4. **Config**: Write `vite.config.ts` (multi-page, manifest, output dir), `tsconfig.json` path aliases, `postcss.config.js`
5. **Theme**: Write `src/styles/globals.css` with `@theme` oklch tokens matching `main.css`
6. **Utilities**: Write `src/lib/utils.ts` (`cn()`)
7. **Components**: Create `breadcrumbs.tsx`, `page-title.tsx`, `ui/button.tsx`, `ui/card.tsx`
8. **Page**: Create `src/pages/abiertas-urgencias/main.tsx` and `page.tsx` matching the tsx reference
9. **Entry**: Create `frontend/index.html` with `<div id="root">` + `<script type="module" src="/src/main.tsx">`
10. **Build**: Run `npm run build` → verify output in `app/static/react-dist/` with `manifest.json`
11. **Flask template**: Write `app/templates/react_shell.html` extending `base.html`
12. **Flask route**: Add `/abiertas-urgencias/react` to `abiertas_urgencias.py` with `_get_manifest_asset()` helper
13. **`.gitignore`**: Add `frontend/node_modules/` and `app/static/react-dist/`
14. **Verify**: `pytest` passes, `/abiertas-urgencias/react` renders correct components

---

# Design Update: 3 New React Pages (Index, Control Novedades, Urgencias)

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Per-page entry | Named object keys vs array paths | Array paths keep existing `"index.html"` manifest key unchanged | Array entries in `rollupOptions.input`, manifest keys = relative paths |
| `react_shell.html` title | Hardcoded block vs `page_title` var | Dynamic avoids duplicating shell templates per page | Pass `page_title` to template, set `<title>` from it |
| Page data types | Shared `InitialData` vs per-page declaration | Each page is a separate build — no risk of type collision | Each `main.tsx` declares its own `window.__INITIAL_DATA__` |
| Urgencias file upload | `<form>` submit vs React `fetch` | `fetch` with FormData keeps experience SPA-like; existing JSON endpoint works as-is | React `fetch POST /urgencias/` with FormData, renders JSON response in ErrorCard |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/index/index.html` | Create | Vite HTML entry for Index page |
| `frontend/src/pages/index/main.tsx` | Create | Entry: renders `IndexPage`, declares `__INITIAL_DATA__` type |
| `frontend/src/pages/index/page.tsx` | Create | `IndexPage` component from `data/import/index.tsx` reference |
| `frontend/src/pages/control-novedades/index.html` | Create | Vite HTML entry for Control Novedades |
| `frontend/src/pages/control-novedades/main.tsx` | Create | Entry: renders `ControlNovedadesPage` |
| `frontend/src/pages/control-novedades/page.tsx` | Create | `ControlNovedadesPage` from `data/import/control-novedades.tsx` reference |
| `frontend/src/pages/urgencias/index.html` | Create | Vite HTML entry for Urgencias |
| `frontend/src/pages/urgencias/main.tsx` | Create | Entry: renders `UrgenciasPage` |
| `frontend/src/pages/urgencias/page.tsx` | Create | `UrgenciasPage` from `data/import/urgencias.tsx` reference |
| `frontend/src/components/status-badge.tsx` | Create | Shared `StatusBadge` with dot + tonal variants (danger, warning, success, info, neutral) |
| `frontend/src/components/ui/input.tsx` | Create | shadcn Input (via `npx shadcn@latest add input`) |
| `frontend/vite.config.ts` | Modify | Add 3 entries to `rollupOptions.input` |
| `app/templates/react_shell.html` | Modify | Dynamic title via `page_title` variable |
| `app/routes/home.py` | Modify | Add `GET /dashboard/react` route |
| `app/routes/control_errores.py` | Modify | Add `GET /control-errores/react` route |
| `app/routes/urgencias.py` | Modify | Add `GET /urgencias/react` route |

## Updated Vite Config

```ts
rollupOptions: {
  input: [
    path.resolve(__dirname, "index.html"),
    path.resolve(__dirname, "src/pages/index/index.html"),
    path.resolve(__dirname, "src/pages/control-novedades/index.html"),
    path.resolve(__dirname, "src/pages/urgencias/index.html"),
  ],
},
```

**Manifest entry keys** (array input → Vite uses relative file paths):
- `"index.html"` — abiertas urgencias (existing, unchanged)
- `"src/pages/index/index.html"` — dashboard
- `"src/pages/control-novedades/index.html"` — control novedades
- `"src/pages/urgencias/index.html"` — urgencias

> **Verify**: after first `npm run build`, inspect `app/static/react-dist/manifest.json` and confirm these keys match. If Vite uses a different key convention, adjust the `entry_key` argument in `_get_manifest_asset()` calls accordingly.

## Flask Route Patterns

Each blueprint gets a `/react` route following the existing `_get_manifest_asset` pattern — the only difference is the manifest entry key and `initial_data` content:

```python
# app/routes/home.py
@home_bp.get("/dashboard/react")
def home_react():
    """React shell for dashboard."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/index/index.html", "file")

    return render_template(
        "react_shell.html",
        page_title="Dashboard",
        entry_js=entry_js,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "kpis": [...],    # computed from data
            "areas": [...],   # filtered by permisos
        },
    )


# app/routes/control_errores.py
@control_errores_bp.get("/control-errores/react")
@permiso_requerido("control_urgencias")
def control_errores_react():
    """React shell for Control Novedades."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "control_urgencias:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/control-novedades/index.html", "file")

    meses = _compute_meses()   # service call
    novedades = get_errores()  # existing service

    return render_template(
        "react_shell.html",
        page_title="Control Novedades",
        entry_js=entry_js,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "meses": meses,
            "novedades": novedades,
        },
    )


# app/routes/urgencias.py
@urgencias_bp.get("/urgencias/react")
@permiso_requerido("urgencias")
def urgencias_react():
    """React shell for Urgencias."""
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/urgencias/index.html", "file")

    return render_template(
        "react_shell.html",
        page_title="Urgencias",
        entry_js=entry_js,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "errores": [],   # empty on load — populated after API POST
        },
    )
```

`_get_manifest_asset` can stay duplicated per route file. Extract to `app/utils/vite_manifest.py` if a 4th route appears.

## Data Flow

### Index (Dashboard)

```
GET /dashboard/react
  → home.py builds kpis[] and areas[] from database
  → renders react_shell.html with __INITIAL_DATA__
  → React IndexPage mounts, reads data, renders KPICard + AreaCard grid
```

**`initial_data`:**
```python
{
    "can_write": bool,
    "username": str,
    "kpis": [
        {"label": "Facturas del mes", "value": "1,248", "trend": "+12% vs abril"},
        {"label": "Pendientes de revisión", "value": "40", "trend": "9 novedades · 31 errores"},
        {"label": "Resueltas este mes", "value": "1,208", "trend": "Cierre al día 24"},
    ],
    "areas": [
        {"title": "Urgencias", "href": "/urgencias/react", "pending": 31,
         "pending_label": "errores", "tone": "danger"},
        # ... filtered by user permisos
    ],
}
```

### Control Novedades

```
GET /control-errores/react
  → control_errores.py computes meses[] and fetches novedades[] via existing service
  → renders react_shell.html with __INITIAL_DATA__
  → React ControlNovedadesPage mounts, reads data, renders all sections
```

**`initial_data`:**
```python
{
    "can_write": bool,
    "username": str,
    "meses": [
        {"label": "May 2026", "count": 10, "active": True},
        {"label": "Abr 2026", "count": 0, "active": False},
    ],
    "novedades": [
        {"factura": "FEV9921", "creado": "Ayer", "categoria": "Centro de Costo",
         "descripcion": "Reasignación", "facturador": "ARIAS C.", "estado": "resuelto"},
    ],
}
```

### Urgencias (file upload flow)

```
1. GET /urgencias/react
   → serves shell with empty errores[]
   → React mounts, shows upload UI only

2. User selects file + clicks "Procesar archivo"
   → React fetch POST /urgencias/ with FormData
   → existing endpoint returns JSON with errores[]
   → React stores result in state, renders ErrorCard

3. API response format (unchanged from existing):
   {
     "status": "success",
     "data": {
       "errores": [{"tipo": "...", "cantidad": N, "facturas": [...]}],
       "total_errores": 31,
     }
   }
```

## Component Architecture

```
IndexPage
├── PageTitle          (eyebrow="Mayo 2026", title, description)
├── KPICard ×3         (Card variant: icon, value, label, trend text)
└── AreaCard ×3        (Card variant: icon, title, desc, StatusBadge, ArrowRight link)

ControlNovedadesPage
├── Breadcrumbs
├── PageTitle           (eyebrow, title, desc, actions slot: Exportar/Carga masiva/Agregar)
├── MonthTabs           (horizontal tab bar, counts badge, active underline)
├── KPICard ×3          (Total registrados, Pendientes, Resueltos)
├── FilterBar           (Card: Search Input + 3 native selects + Limpiar Button)
└── ErrorTable
    ├── thead: 7 columns
    └── tbody: row per novedad
        ├── StatusBadge (categoria tone: info|neutral)
        ├── StatusBadge (estado tone: warning|success, dot)
        └── Button ×3 (Eye, Pencil, Trash2 — icon variant ghost)

UrgenciasPage
├── Breadcrumbs
├── PageTitle
├── UploadCard          (Card: drop-zone label, file info, Info alert, Button "Procesar")
└── ErrorCard           (Card: danger header with total, category StatusBadge, table + Button "Controlar")
```

## New Components

### status-badge.tsx

```tsx
interface StatusBadgeProps {
  children: React.ReactNode;
  tone: "danger" | "warning" | "success" | "info" | "neutral";
  dot?: boolean;
}
```

Tone → CSS mapping uses `@theme` tokens (e.g. `bg-danger/10 text-danger`, `bg-warning/15 text-warning-foreground`). The `dot` prop renders a `span` with `rounded-full w-1.5 h-1.5` before text.

> **Note**: references (`index.tsx`, `control-novedades.tsx`) import both `PageTitle` and `StatusBadge` from `@/components/status-badge`. But `PageTitle` already lives at `@/components/page-title.tsx`. The page `.tsx` files should import from the correct paths — this is a reference artifact from TanStack Router scaffolding.

### shadcn Input

```bash
cd frontend && npx shadcn@latest add input
```

## react_shell.html Update

Replace hardcoded `<title>` with dynamic variable:

```html
{% block title %}{{ page_title | default("Control de Facturación") }} — React{% endblock %}
```

## Updated Execution Steps (append to existing 14)

15. **Components**: Create `frontend/src/components/status-badge.tsx`; run `npx shadcn@latest add input` in `frontend/`
16. **Pages**: Create `src/pages/index/`, `src/pages/control-novedades/`, `src/pages/urgencias/` — each with `index.html`, `main.tsx`, `page.tsx`
17. **Config**: Update `vite.config.ts` — add 3 array entries to `rollupOptions.input`
18. **Template**: Update `react_shell.html` — replace hardcoded title with `{{ page_title }}`
19. **Routes**: Add `/dashboard/react` to `home.py`, `/control-errores/react` to `control_errores.py`, `/urgencias/react` to `urgencias.py` — each with correct manifest entry key and `initial_data`
20. **Build**: `npm run build` → verify 4 entries in `manifest.json`
21. **Verify**: Each `/react` route renders correct components; urgencias `POST /urgencias/` returns JSON consumable by React page
