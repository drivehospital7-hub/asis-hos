-- =============================================================================
-- Migration Engine F3: cantidades_hospitalizacion
-- Rule: If cantidad > 8 → flag as warning (simple threshold for Hospitalización).
-- Domain: hospitalizacion
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'cantidades_hospitalizacion',
       'Cantidad mayor a 8 en hospitalización',
       'hospitalizacion', 'active', 1, 25, 'warning', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'cantidades_hospitalizacion' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'cantidades_hospitalizacion' AND version = 1
);

-- Single atomic condition: gt(cantidad, 8)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'cantidades_hospitalizacion' AND version = 1),
    NULL,
    'atomic',
    'gt',
    'invoice.cantidad',
    '8',
    0
);
