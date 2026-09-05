-- =============================================================================
-- Phase 3: IDE Contrato Reverse Urgencias — condition tree
-- =============================================================================
-- Migrates: app/services/urgencias/ide_contrato_reverse.py
-- Covers: Simple reverse rules where a specific IDE → expected código(s).
-- Conditional 890405 rules (977,979,958,961,922,863,975,920,908) requiring
-- pre-scan for 861801 remain in legacy until Phase 6.
-- =============================================================================

BEGIN;

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'ide_contrato_reverse_urgencias_valido',
    'Valida que el código CUPS corresponda al IDE Contrato (reglas REVERSE). Cubre reglas simples sin pre-scan.',
    'urgencias',
    'active',
    1,
    46,
    'error',
    TRUE
);

-- Root: OR
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre = 'ide_contrato_reverse_urgencias_valido'), NULL, 'composite', 'OR', NULL, NULL, 0);

-- 1. IDE 986 → código debe ser 906340
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"986"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.codigo', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"906340"'::jsonb, 0);

-- 2. IDE 839 → código debe ser 906340
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"839"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.codigo', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"906340"'::jsonb, 0);

-- 3. IDE 842 → código debe ser 906340
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 2);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"842"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.codigo', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.codigo', '"906340"'::jsonb, 0);

-- 4. IDE 970 (ESS118) → código debe ser 735301, 861801 o 890205
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 3);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"970"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.codigo', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'in', 'invoice.codigo', '["735301","861801","890205"]'::jsonb, 0);

-- 5. IDE 974 (ESS118) → código debe ser 735301, 861801 o 890405
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'),
    (SELECT id FROM condiciones WHERE regla_id=(SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido') AND padre_id IS NULL),
    'composite', 'AND', NULL, NULL, 4);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden) VALUES
    ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'eq', 'invoice.ide_contrato', '"974"'::jsonb, 0);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones WHERE operador='AND'), 'composite', 'NOT', 'invoice.codigo', NULL, 1);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES ((SELECT id FROM reglas WHERE nombre='ide_contrato_reverse_urgencias_valido'), (SELECT MAX(id) FROM condiciones), 'atomic', 'in', 'invoice.codigo', '["735301","861801","890405"]'::jsonb, 0);

COMMIT;
