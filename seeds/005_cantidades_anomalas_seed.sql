-- =============================================================================
-- Seed: cantidades_anomalas (3 reglas separadas)
-- Cada regla detecta un tipo distinto de cantidad anomala
-- =============================================================================

BEGIN;

-- ========== REGLA 1: Consultas con cantidad >= 2 ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'cantidad_consultas_anomalas',
    'Consultas con cantidad >= 2 se consideran anomalas.',
    'transversal',
    'active',
    1,
    30,
    'warning',
    TRUE
);

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0
FROM reglas r WHERE r.nombre = 'cantidad_consultas_anomalas';

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'eq', 'invoice.tipo_procedimiento',
       '"Consultas"'::jsonb, 0
FROM reglas r WHERE r.nombre = 'cantidad_consultas_anomalas';

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, c.id, 'atomic', 'gte', 'invoice.cantidad',
       '2'::jsonb, 1
FROM reglas r
JOIN condiciones c ON c.regla_id = r.id AND c.padre_id IS NULL
WHERE r.nombre = 'cantidad_consultas_anomalas';

-- ========== REGLA 2: Cualquier tipo con cantidad > 10 ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'cantidad_general_anomalas',
    'Cualquier tipo de procedimiento con cantidad > 10 se considera anomalo.',
    'transversal',
    'active',
    1,
    30,
    'warning',
    TRUE
);

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0
FROM reglas r WHERE r.nombre = 'cantidad_general_anomalas';

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'gt', 'invoice.cantidad',
       '10'::jsonb, 0
FROM reglas r WHERE r.nombre = 'cantidad_general_anomalas';

-- ========== REGLA 3: PyP con cantidad >= 3 ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'cantidad_pyp_anomalas',
    'Convenio PyP con cantidad >= 3 se considera anomalo.',
    'transversal',
    'active',
    1,
    30,
    'warning',
    TRUE
);

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0
FROM reglas r WHERE r.nombre = 'cantidad_pyp_anomalas';

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'eq', 'invoice.convenio_facturado',
       '"Promocion y Prevencion"'::jsonb, 0
FROM reglas r WHERE r.nombre = 'cantidad_pyp_anomalas';

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, c.id, 'atomic', 'gte', 'invoice.cantidad',
       '3'::jsonb, 1
FROM reglas r
JOIN condiciones c ON c.regla_id = r.id AND c.padre_id IS NULL
WHERE r.nombre = 'cantidad_pyp_anomalas';

COMMIT;

SELECT 'cantidades_anomalas rules seeded' as msg;
