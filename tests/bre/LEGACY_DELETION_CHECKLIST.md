# Legacy-Route Deletion Checklist — PASS

Change `migracion-procesar-bre-unificado`, task 3.1. Branch
`feature/procesamiento-unificado`. NO direct-to-main merge — deletions land
via the feature-branch chain only. No deletions executed by this checklist.

## Scratch diff (main...HEAD, app/routes/)

- Deleted: `urgencias.py` (-206), `odontologia_equipos_basicos.py` (-168).
- Added: `procesar.py` (+223, unified POST /procesar, AREA_UNIFICADA).
- `app/__init__.py`: legacy blueprints unregistered, `procesar_bp` at /procesar.

## Main fixes review — none lost

- `sheet_name` passthrough: preserved in `procesar.py`. `header_row`/`sheet_id`
  + `build_excel_headers_form_context` ctx was dead code on main (built, never
  passed to `detect_problems_only`) — nothing to port.
- Missing-columns guard + temp cleanup before return: preserved (200 + message).
- Permission compat: `users_store.py` migrates old perms to `procesar`. Preserved.
- Accepted deltas (per `unificar-rutas-procesamiento` design): route-level
  `normalize_text` cosmetic only (service layer normalizes; parity 2.1-2.3
  GREEN); EB error status 200→400 hardening; grouping by tipo_factura.

## Out of scope (not signed here)

- `excel_headers.py`, `genderize_api.py` deletions — separate changes.
- Stale tests hitting deleted URLs (`test_odontologia_equipos_basicos`,
  `test_routes_fec_factura`, `test_stacked_integration`) — owned by
  `unificar-rutas-procesamiento` follow-up, noted in openspec verify-report.

## Prod gate (task 3.2)

- Dry-run `scripts/prod_baseline.py`: users.json `f2bc4c48…57756aa` unchanged,
  base.py `60743225…34ab68` unchanged, rerun-stable, guard aborts on prod
  names, zero prod connections. Pinned in `tests/bre/prod_digests.json`.

Signed: sdd-apply Slice 3, 2026-09-05. Status: PASS.
