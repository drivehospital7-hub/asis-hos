# Tasks: CAP exception — ESS118 / EPSS41 in CUPS sin contrato

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~108 (18 src + 90 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: RED — Tests first

- [ ] 1.1 Extend `_make_mock_session()` helper: add `cap_cups: dict[int, list[str]] | None = None` param, flatten into `[(id_nota_hoja, cups), ...]` as 4th `.all()` side_effect entry
- [ ] 1.2 Test: CAP + ESS118 + CUPS in nota_hoja id=3 → no error (CAP exception applies)
- [ ] 1.3 Test: CAP + EPSS41 + CUPS in nota_hoja id=2 → no error (CAP exception applies)
- [ ] 1.4 Test: CAP + ESS118 + CUPS NOT in nota_hoja id=3 → error (fails validation)
- [ ] 1.5 Test: CAP + EPSS41 + CUPS NOT in nota_hoja id=2 → error (fails validation)
- [ ] 1.6 Test: CAP + ESS118 + nota_hoja id=3 vacía → error (fails closed)
- [ ] 1.7 Test: No-CAP factura + ESS118 + CUPS no contratado → error (standard validation)

## Phase 2: GREEN — Implementation

- [ ] 2.1 Batch pre-load: add query for `NotasTecnicas.id_nota_hoja.in_([2, 3])` inside the `try` block, after `nota1_results`, split into `nota_cap_cups: dict[int, set[str]]`
- [ ] 2.2 Row-loop branch: insert after urgencias exception (line 224), before `entidades_con_datos` (line 227): check `factura_num.upper().startswith("CAP")` + `cod_entidad` → redirect to `nota_cap_cups[3]` or `nota_cap_cups[2]`

## Phase 3: VERIFY

- [ ] 3.1 Run `python -m pytest -v tests/services/test_detect_cups_sin_contrato.py` — all 35 tests pass (28 existing + 7 new)
