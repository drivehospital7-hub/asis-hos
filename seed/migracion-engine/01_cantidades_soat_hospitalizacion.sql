-- =============================================================================
-- Migration Engine F1: cantidades_soat_hospitalizacion
-- Rule: If tarifario = "SOAT" AND cantidad > 2 → flag as warning.
-- Domain: hospitalizacion
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'cantidades_soat_hospitalizacion',
       'Cantidad mayor a 2 en tarifario SOAT para hospitalización',
       'hospitalizacion', 'active', 1, 25, 'warning', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'cantidades_soat_hospitalizacion' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'cantidades_soat_hospitalizacion' AND version = 1
);

-- Root: AND
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'cantidades_soat_hospitalizacion' AND version = 1),
    NULL,
    'composite',
    'AND',
    NULL,
    NULL,
    0
);

-- Child 1: eq(tarifario, "SOAT")
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT
    r.id,
    (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id),
    'atomic',
    'eq',
    'invoice.tarifario',
    '"SOAT"',
    0
FROM reglas r WHERE r.nombre = 'cantidades_soat_hospitalizacion' AND r.version = 1;

-- Child 2: gt(cantidad, 2)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT
    r.id,
    (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id),
    'atomic',
    'gt',
    'invoice.cantidad',
    '2',
    1
FROM reglas r WHERE r.nombre = 'cantidades_soat_hospitalizacion' AND r.version = 1;
