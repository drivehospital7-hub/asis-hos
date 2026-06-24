-- =============================================================================
-- Phase 3: IDE Contrato Urgencias — condition tree from legacy detector
-- =============================================================================
-- Migrates: app/services/urgencias/ide_contrato_urgencias.py
-- Covers: all 15 simple exact rules, 2 multiple rules, and top 8 generic 
-- entidad→contrato rules. Insertion/conditional rules (requiring pre-scan
-- for 861801/890405) remain in legacy until Phase 6 (GroupEvaluator).
--
-- Structure: OR root → per-branch AND → atomic conditions.
-- =============================================================================

BEGIN;

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'ide_contrato_urgencias_valido',
    'Valida IDE Contrato en Urgencias. Cubre reglas simples (código+entidad→IDE único), múltiples y genéricas de entidad.',
    'urgencias',
    'active',
    1,
    45,
    'error',
    TRUE
);

-- Root: OR
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre = 'ide_contrato_urgencias_valido'), NULL, 'composite', 'OR', NULL, NULL, 0);

-- =============================================================================
-- Simple exact rules: code + entity → single expected IDE
-- Branch pattern: AND(eq entidad, eq codigo, NOT(eq ide_contrato, expected))
-- =============================================================================

-- 1. EPSI05 + 906340 → IDE 986
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre = 'ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSI05"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"906340"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"986"'::jsonb, 0);

-- 2. EPSI05 + 861801 → IDE 977
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSI05"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"977"'::jsonb, 0);

-- 3. EPSIC5 + 861801 → IDE 979
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSIC5"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"979"'::jsonb, 0);

-- 4. ESS118 + 906340 → IDE 839
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 3);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"906340"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"839"'::jsonb, 0);

-- 5. ESS118 + 890405 → IDE 974
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 4);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"890405"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"974"'::jsonb, 0);

-- 6. ESS118 + 890205 → IDE 970
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 5);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"890205"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"970"'::jsonb, 0);

-- 7. ESSC18 + 906340 → IDE 842
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 6);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC18"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"906340"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"842"'::jsonb, 0);

-- 8. ESSC18 + 861801 → IDE 975
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 7);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC18"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"975"'::jsonb, 0);

-- 9. EPS037 + 906340 → IDE 962
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 8);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPS037"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"906340"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"962"'::jsonb, 0);

-- 10. EPS037 + 861801 → IDE 961
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 9);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPS037"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"961"'::jsonb, 0);

-- 11. EPSS41 + 906340 → IDE 959
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 10);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS41"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"906340"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"959"'::jsonb, 0);

-- 12. EPSS41 + 861801 → IDE 958
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 11);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS41"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"958"'::jsonb, 0);

-- 13. ESS062 + 861801 → IDE 922
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 12);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS062"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"922"'::jsonb, 0);

-- 14. ESSC62 + 861801 → IDE 863
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 13);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC62"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"863"'::jsonb, 0);

-- 15. 86000 + 861801 → IDE 920
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 14);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"86000"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"920"'::jsonb, 0);

-- 16. RES004 + 861801 → IDE 908
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 15);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"RES004"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"908"'::jsonb, 0);

-- =============================================================================
-- Multiple rules: code + entity → any IDE from a set
-- =============================================================================

-- 17. ESS118 + 735301 → IDE 970 or 974
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 16);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"735301"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'in', 'invoice.ide_contrato', '["970","974"]'::jsonb, 0);

-- 18. ESS118 + 861801 → IDE 970 or 974
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 17);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"'::jsonb, 0),
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"861801"'::jsonb, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'in', 'invoice.ide_contrato', '["970","974"]'::jsonb, 0);

-- =============================================================================
-- Generic entidad→contrato: entity → single expected IDE (no code check needed)
-- Covers: 86, 5177, RES001, AT1306, 000124, EPSS005, EPSC005, MIN001
-- =============================================================================

-- 19. 86 → IDE 911
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 18);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"86"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"911"'::jsonb, 0);

-- 20. 5177 → IDE 917
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 19);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"5177"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"917"'::jsonb, 0);

-- 21. RES001 → IDE 992
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 20);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"RES001"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"992"'::jsonb, 0);

-- 22. AT1306 → IDE 867
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 21);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"AT1306"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"867"'::jsonb, 0);

-- 23. 000124 → IDE 874
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 22);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"000124"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"874"'::jsonb, 0);

-- 24. EPSS005 → IDE 934
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 23);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS005"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"934"'::jsonb, 0);

-- 25. EPSC005 → IDE 931
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 24);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSC005"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"931"'::jsonb, 0);

-- 26. MIN001 multiple → IDE 910 or 918
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 25);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"MIN001"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'in', 'invoice.ide_contrato', '["910","918"]'::jsonb, 0);

COMMIT;
