# Tasks: Limpia Templates Jinja Huérfanos

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~4,900 (4,855 deletions + ~10 additions) |
| 400-line budget risk | **High** |
| Chained PRs recommended | **Yes** |
| Suggested split | PR 1 (Code + Tests) → PR 2 (File deletions) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: **Yes**
Chained PRs recommended: **Yes**
Chain strategy: **feature-branch-chain**
400-line budget risk: **High**

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Convert fallbacks to JSON + remove `login_legacy` + update tests | PR 1 | 5 files, ~96 changed lines. Base = feature/tracker branch. |
| 2 | Delete 12 orphan files (9 templates + 3 CSS) | PR 2 | Base = PR #1 branch. ~4,855 deletions, zero additions. Pure deletion, low cognitive load despite size. |

**Why feature-branch-chain and not stacked-to-main**: PR 2 (deletions) depends on PR 1 (tests must pass first). A feature branch lets both accumulate before merging to main, with rollback safety — revert the tracker branch, not two individual PRs.

## Phase 1: Core Code Changes + Test Updates (PR 1)

- [x] 1.1 `app/routes/urgencias.py` — Replace `render_template("urgencias.html", **ctx)` on L78 and L90 with `jsonify({"status":"error","data":{},"errors":["..."]}), 400`
- [x] 1.2 `app/routes/excel_headers.py` — Replace `render_template("excel_headers.html", **ctx)` on L97 and L109 with `jsonify({"status":"error","data":{},"errors":["..."]}), 400`
- [x] 1.3 `app/__init__.py` — Remove `"auth.login_legacy"` from `PUBLIC_ENDPOINTS` frozenset
- [x] 1.4 `tests/services/test_favicon_titles.py` — Remove `login.html`, `import_facturas.html`, `usuarios.html` from `TEMPLATES`; remove `login.html` from `TITLE_TEMPLATES`; remove `test_login_html_title()` method
- [x] 1.5 `tests/services/test_visual_redesign.py` — Remove `TestHomeTemplate` class; remove `TestAbiertasUrgenciasTemplate` class; remove `test_legacy_abiertas_urgencias_css_exists`; remove `ordenado_facturado.html` and `derechos.html` from `test_template_extends_base` parametrize; remove `test_standalone_templates_have_tailwind`
- [x] 1.6 **Verify**: `pytest -v` passes with 0 failures; all preserved pages still render

## Phase 2: Delete Orphan Files (PR 2)

- [x] 2.1 `app/templates/` — Delete 9 orphan templates: `home.html`, `login.html`, `usuarios.html`, `import_facturas.html`, `derechos.html`, `abiertas_urgencias.html`, `ordenado_facturado.html`, `urgencias.html`, `excel_headers.html`
- [x] 2.2 `app/static/css/legacy/` — Delete 3 orphan CSS: `abiertas_urgencias.css`, `derechos.css`, `urgencias.css`
- [x] 2.3 **Verify**: `pytest -v` passes; `app/templates/` contains only 5 preserved files: `base.html`, `control_errores.html`, `react_shell.html`, `react_standalone.html`, `unauthorized.html`
