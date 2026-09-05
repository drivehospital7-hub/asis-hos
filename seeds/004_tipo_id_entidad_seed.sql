-- =============================================================================
-- Seed: tipo_identificacion_entidad (2 reglas)
-- Regla 1: AS/MS requieren Cod Entidad = 86000
-- Regla 2: Cod Entidad = 86000 solo valido para AS/MS
-- =============================================================================

BEGIN;

-- ========== REGLA 1: AS/MS requieren Cod Entidad = 86000 ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'tipo_id_requiere_entidad_86000',
    'AS o MS como tipo identificacion requieren Cod Entidad Cobrar = 86000.',
    'transversal',
    'active',
    1,
    20,
    'error',
    TRUE
);

-- Root: AND
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0
FROM reglas r WHERE r.nombre = 'tipo_id_requiere_entidad_86000';

-- Child 1: IN(tipo, ["AS","MS"])
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'in', 'invoice.tipo_identificacion',
       '["AS", "MS"]'::jsonb, 0
FROM reglas r WHERE r.nombre = 'tipo_id_requiere_entidad_86000';

-- Child 2: NOT(EQ(cod_entidad, "86000"))
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, c.id, 'composite', 'NOT', NULL, NULL, 1
FROM reglas r
JOIN condiciones c ON c.regla_id = r.id AND c.padre_id IS NULL
WHERE r.nombre = 'tipo_id_requiere_entidad_86000';

-- Child 2a: EQ(cod_entidad, "86000") inside NOT
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar',
       '86000'::jsonb, 0
FROM reglas r WHERE r.nombre = 'tipo_id_requiere_entidad_86000';

-- ========== REGLA 2: Cod Entidad = 86000 solo valido para AS/MS ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'entidad_86000_requiere_as_ms',
    'Cod Entidad Cobrar = 86000 solo es valido para tipo identificacion AS o MS.',
    'transversal',
    'active',
    1,
    20,
    'error',
    TRUE
);

-- Root: AND
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0
FROM reglas r WHERE r.nombre = 'entidad_86000_requiere_as_ms';

-- Child 1: EQ(cod_entidad, "86000")
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'eq', 'invoice.codigo_entidad_cobrar',
       '86000'::jsonb, 0
FROM reglas r WHERE r.nombre = 'entidad_86000_requiere_as_ms';

-- Child 2: NOT(IN(tipo, ["AS","MS"]))
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, c.id, 'composite', 'NOT', NULL, NULL, 1
FROM reglas r
JOIN condiciones c ON c.regla_id = r.id AND c.padre_id IS NULL
WHERE r.nombre = 'entidad_86000_requiere_as_ms';

-- Child 2a: IN(tipo, ["AS","MS"]) inside NOT
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c2.id) FROM condiciones c2 WHERE c2.regla_id = r.id), 'atomic', 'in', 'invoice.tipo_identificacion',
       '["AS", "MS"]'::jsonb, 0
FROM reglas r WHERE r.nombre = 'entidad_86000_requiere_as_ms';

COMMIT;

SELECT 'tipo_identificacion_entidad rules seeded' as msg;
