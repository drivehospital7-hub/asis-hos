-- =============================================================================
-- Phase 3: IDE Contrato Odontología — condition tree from legacy detector
-- =============================================================================
-- Migrates: app/services/odontologia/ide_contrato.py (detect_ide_contrato_odontologia)
-- Rule: For each (entidad, PyP-status), the IDE must match an expected set.
-- Covers top 8 entities (ESS118, ESSC18, EPSS41, EPSI05, EPSIC5, RES001, 0001, 86).
-- Remaining entities (EPS037, ESS062, ESSC62, EPSS005, EPSC005, 86000) stay in legacy.
-- =============================================================================

BEGIN;

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'ide_contrato_odontologia_valido',
    'Valida que el IDE Contrato corresponda a la entidad y tipo de procedimiento (PyP vs No PyP) en Odontología.',
    'odontologia',
    'active',
    1,
    40,
    'error',
    TRUE
);

WITH
rule AS (SELECT id FROM reglas WHERE nombre = 'ide_contrato_odontologia_valido'),
PYP AS (SELECT ARRAY['890203','990203','990212','997002','997106','997107','997301','P0000011']::text[] AS codes),
-- Root: OR
root AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, NULL, 'composite', 'OR', NULL, NULL, 0 FROM rule
    RETURNING id
),
-- 1. ESS118 + PyP
b1 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 0 FROM rule, root
    RETURNING id
),
b1_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b1.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"'::jsonb, 0 FROM rule, b1
),
b1_p AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b1.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 1 FROM rule, b1
),
b1_n AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b1.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b1
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b1_n.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["970","974"]'::jsonb, 0 FROM rule, b1_n;

-- 2. ESS118 + NO PyP
WITH
b2 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 1 FROM rule, root
    RETURNING id
),
b2_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b2.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"'::jsonb, 0 FROM rule, b2
),
b2_np AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b2.id, 'composite', 'NOT', NULL, NULL, 1 FROM rule, b2
    RETURNING id
),
b2_np_i AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b2_np.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 0 FROM rule, b2_np
),
b2_ni AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b2.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b2
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b2_ni.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["969","973"]'::jsonb, 0 FROM rule, b2_ni;

-- 3. ESSC18 + PyP
WITH
b3 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 2 FROM rule, root
    RETURNING id
),
b3_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b3.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC18"'::jsonb, 0 FROM rule, b3
),
b3_p AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b3.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 1 FROM rule, b3
),
b3_n AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b3.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b3
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b3_n.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["975"]'::jsonb, 0 FROM rule, b3_n;

-- 4. ESSC18 + NO PyP
WITH
b4 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 3 FROM rule, root
    RETURNING id
),
b4_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b4.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC18"'::jsonb, 0 FROM rule, b4
),
b4_np AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b4.id, 'composite', 'NOT', NULL, NULL, 1 FROM rule, b4
    RETURNING id
),
b4_np_i AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b4_np.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 0 FROM rule, b4_np
),
b4_ni AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b4.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b4
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b4_ni.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["968"]'::jsonb, 0 FROM rule, b4_ni;

-- 5. EPSS41 + PyP
WITH
b5 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 4 FROM rule, root
    RETURNING id
),
b5_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b5.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS41"'::jsonb, 0 FROM rule, b5
),
b5_p AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b5.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 1 FROM rule, b5
),
b5_n AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b5.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b5
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b5_n.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["955","958"]'::jsonb, 0 FROM rule, b5_n;

-- 6. EPSS41 + NO PyP
WITH
b6 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 5 FROM rule, root
    RETURNING id
),
b6_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b6.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS41"'::jsonb, 0 FROM rule, b6
),
b6_np AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b6.id, 'composite', 'NOT', NULL, NULL, 1 FROM rule, b6
    RETURNING id
),
b6_np_i AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b6_np.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 0 FROM rule, b6_np
),
b6_ni AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b6.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b6
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b6_ni.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["956","959"]'::jsonb, 0 FROM rule, b6_ni;

-- 7. EPSI05 + PyP
WITH
b7 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 6 FROM rule, root
    RETURNING id
),
b7_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b7.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSI05"'::jsonb, 0 FROM rule, b7
),
b7_p AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b7.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 1 FROM rule, b7
),
b7_n AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b7.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b7
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b7_n.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["977"]'::jsonb, 0 FROM rule, b7_n;

-- 8. EPSI05 + NO PyP
WITH
b8 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 7 FROM rule, root
    RETURNING id
),
b8_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b8.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSI05"'::jsonb, 0 FROM rule, b8
),
b8_np AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b8.id, 'composite', 'NOT', NULL, NULL, 1 FROM rule, b8
    RETURNING id
),
b8_np_i AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b8_np.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 0 FROM rule, b8_np
),
b8_ni AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b8.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b8
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b8_ni.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["976","978"]'::jsonb, 0 FROM rule, b8_ni;

-- 9. EPSIC5 + PyP
WITH
b9 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 8 FROM rule, root
    RETURNING id
),
b9_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b9.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSIC5"'::jsonb, 0 FROM rule, b9
),
b9_p AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b9.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 1 FROM rule, b9
),
b9_n AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b9.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b9
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b9_n.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["979"]'::jsonb, 0 FROM rule, b9_n;

-- 10. EPSIC5 + NO PyP
WITH
b10 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 9 FROM rule, root
    RETURNING id
),
b10_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b10.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSIC5"'::jsonb, 0 FROM rule, b10
),
b10_np AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b10.id, 'composite', 'NOT', NULL, NULL, 1 FROM rule, b10
    RETURNING id
),
b10_np_i AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b10_np.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 0 FROM rule, b10_np
),
b10_ni AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b10.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b10
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b10_ni.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["967"]'::jsonb, 0 FROM rule, b10_ni;

-- 11. RES001 + PyP
WITH
b11 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 10 FROM rule, root
    RETURNING id
),
b11_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b11.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"RES001"'::jsonb, 0 FROM rule, b11
),
b11_p AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b11.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 1 FROM rule, b11
),
b11_n AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b11.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b11
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b11_n.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["993"]'::jsonb, 0 FROM rule, b11_n;

-- 12. RES001 + NO PyP
WITH
b12 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 11 FROM rule, root
    RETURNING id
),
b12_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b12.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"RES001"'::jsonb, 0 FROM rule, b12
),
b12_np AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b12.id, 'composite', 'NOT', NULL, NULL, 1 FROM rule, b12
    RETURNING id
),
b12_np_i AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b12_np.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 0 FROM rule, b12_np
),
b12_ni AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b12.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b12
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b12_ni.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["992"]'::jsonb, 0 FROM rule, b12_ni;

-- 13. 0001 + PyP
WITH
b13 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 12 FROM rule, root
    RETURNING id
),
b13_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b13.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"0001"'::jsonb, 0 FROM rule, b13
),
b13_p AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b13.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 1 FROM rule, b13
),
b13_n AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b13.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b13
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b13_n.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["17"]'::jsonb, 0 FROM rule, b13_n;

-- 14. 0001 + NO PyP
WITH
b14 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 13 FROM rule, root
    RETURNING id
),
b14_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b14.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"0001"'::jsonb, 0 FROM rule, b14
),
b14_np AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b14.id, 'composite', 'NOT', NULL, NULL, 1 FROM rule, b14
    RETURNING id
),
b14_np_i AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b14_np.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 0 FROM rule, b14_np
),
b14_ni AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b14.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b14
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b14_ni.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["984"]'::jsonb, 0 FROM rule, b14_ni;

-- 15. 86 + NO PyP (only NO PyP rule for "86")
WITH
b15 AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, root.id, 'composite', 'AND', NULL, NULL, 14 FROM rule, root
    RETURNING id
),
b15_e AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b15.id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"86"'::jsonb, 0 FROM rule, b15
),
b15_np AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b15.id, 'composite', 'NOT', NULL, NULL, 1 FROM rule, b15
    RETURNING id
),
b15_np_i AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b15_np.id, 'atomic', 'in', 'invoice.codigo',
        (SELECT to_jsonb(codes) FROM PYP), 0 FROM rule, b15_np
),
b15_ni AS (
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    SELECT rule.id, b15.id, 'composite', 'NOT', NULL, NULL, 2 FROM rule, b15
    RETURNING id
)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT rule.id, b15_ni.id, 'atomic', 'in', 'invoice.ide_contrato',
    '["911"]'::jsonb, 0 FROM rule, b15_ni;

COMMIT;
