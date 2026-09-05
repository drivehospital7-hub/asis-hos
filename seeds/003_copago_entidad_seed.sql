-- =============================================================================
-- Seed: copago_entidad_valido
-- Lógica: AND(NOT(IN(cod_entidad, ["1","0001"])), NOT(EQ(vlr_copago, 0)))
-- =============================================================================

BEGIN;

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'copago_entidad_valido',
    'Detecta filas donde Cod Entidad no es default y Vlr. Copago no es 0.',
    'urgencias',
    'active',
    1,
    25,
    'error',
    TRUE
);

-- Root: AND (padre = NULL)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0
FROM reglas r WHERE r.nombre = 'copago_entidad_valido';

-- NOT(IN(cod_entidad)) — padre = root AND
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'composite', 'NOT', NULL, NULL, 0
FROM reglas r WHERE r.nombre = 'copago_entidad_valido';

-- IN(cod_entidad, ["1","0001"]) — padre = last NOT
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'in', 'invoice.codigo_entidad_cobrar',
       '["1", "0001"]'::jsonb, 0
FROM reglas r WHERE r.nombre = 'copago_entidad_valido';

-- NOT(EQ(vlr_copago, 0)) — padre = root AND (donde padre IS NULL)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, c.id, 'composite', 'NOT', NULL, NULL, 1
FROM reglas r
JOIN condiciones c ON c.regla_id = r.id AND c.padre_id IS NULL
WHERE r.nombre = 'copago_entidad_valido';

-- EQ(vlr_copago, 0) — padre = last NOT(EQ)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'eq', 'invoice.vlr_copago',
       '0'::jsonb, 0
FROM reglas r WHERE r.nombre = 'copago_entidad_valido';

COMMIT;

SELECT 'copago_entidad_valido seeded' as msg;
