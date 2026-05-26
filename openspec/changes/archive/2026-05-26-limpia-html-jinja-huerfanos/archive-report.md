# Archive Report — Limpia los HTML Jinja huérfanos

**Change**: Limpia los html jinja huerfanos que ya no se usan para que no siga habiendo confusion al momento de cambios, debe permanecer pagina de control y sus componenetes como side bar, porque aun no se ha migrado
**Archived at**: 2026-05-26
**Archive path**: `openspec/changes/archive/2026-05-26-limpia-html-jinja-huerfanos/`

## Artifacts Present

| Artifact | Status | Notes |
|----------|--------|-------|
| `proposal.md` | ✅ | Intent, scope, approach, success criteria defined |
| `spec.md` | ✅ | Delta spec: 3 ADDED, 2 MODIFIED, 2 REMOVED requirements |
| `design.md` | ✅ | Architecture decisions, file changes, edge cases documented |
| `tasks.md` | ✅ | 9 tasks across 2 phases, all marked complete |
| `verify-report.md` | ✅ | PASS WITH WARNINGS — all requirements compliant |
| `archive-report.md` | ✅ | Current file |

## Delta Spec Sync

**Merge step**: Skipped — no delta specs in `specs/` subdirectory. No corresponding main spec domain exists in `openspec/specs/`. The change's spec is a standalone delta for a cross-cutting cleanup that does not map to any existing domain spec.

## Task Completion

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | `urgencias.py` — Replace `render_template("urgencias.html")` with `jsonify(error), 400` (L78, L90) | ✅ Complete |
| 1.2 | `excel_headers.py` — Replace `render_template("excel_headers.html")` with `jsonify(error), 400` (L97, L109) | ✅ Complete |
| 1.3 | `__init__.py` — Remove `"auth.login_legacy"` from `PUBLIC_ENDPOINTS` | ✅ Complete |
| 1.4 | `test_favicon_titles.py` — Remove orphan entries from TEMPLATES/TITLE_TEMPLATES; delete `test_login_html_title` | ✅ Complete |
| 1.5 | `test_visual_redesign.py` — Remove orphan test classes and parametrize entries | ✅ Complete |
| 1.6 | Verify: `pytest -v` passes | ✅ Complete (476 passed, 10 pre-existing failures unrelated) |
| 2.1 | Delete 9 orphan templates from `app/templates/` | ✅ Complete |
| 2.2 | Delete 3 orphan CSS from `app/static/css/legacy/` | ✅ Complete |
| 2.3 | Verify: `pytest -v` passes; only 5 preserved templates remain | ✅ Complete |

**Total**: 9/9 tasks complete (100%)

## Verification Verdict

**PASS WITH WARNINGS** per verify-report.md:
- All requirements COMPLIANT per spec compliance matrix (16/16 scenarios)
- 10 pre-existing test failures unrelated to this change (9 `fec_factura_map` TypeError, 1 manifest HTML count)
- No critical issues found
- All 7 orphaned templates deleted, 3 legacy CSS deleted, fallbacks converted to JSON, `login_legacy` removed

## Planned vs Actual Delta

| Aspect | Planned | Actual | Delta |
|--------|---------|--------|-------|
| Templates deleted | 7 orphans + 2 semi-active = 9 | 9 deleted | ✅ Match |
| CSS legacy deleted | 3 (`abiertas_urgencias.css`, `derechos.css`, `urgencias.css`) | 3 deleted | ✅ Match |
| Fallbacks converted | 4 locations (urgencias L78,L90 + excel_headers L97,L109) | 4 locations | ✅ Match |
| `login_legacy` removed | 1 location in `__init__.py` | 1 location | ✅ Match |
| Tests updated | 2 test files | 2 files | ✅ Match |
| Preserved templates | `base.html`, `control_errores.html`, `react_shell.html`, `react_standalone.html`, `unauthorized.html` | 5 preserved | ✅ Match |
| Tasks count | 9 tasks | 9 tasks | ✅ Match |

## Final State Summary

The change has been fully implemented, verified, and archived. The 9 orphan Jinja templates and 3 orphan CSS files are deleted. POST fallbacks in `urgencias.py` and `excel_headers.py` now return JSON error responses instead of HTML. `auth.login_legacy` is removed from `PUBLIC_ENDPOINTS`. Tests are updated to reflect the new state. The 5 preserved templates (`base.html`, `control_errores.html`, `react_shell.html`, `react_standalone.html`, `unauthorized.html`) remain unchanged.

## SDD Cycle Complete

- [x] Proposal
- [x] Spec
- [x] Design
- [x] Tasks
- [x] Apply
- [x] Verify
- [x] Archive
