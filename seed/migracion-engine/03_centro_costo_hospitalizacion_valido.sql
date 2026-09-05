-- =============================================================================
-- Migration Engine F3: centro_costo_hospitalizacion_valido
-- Rule: Centro de costo rules for Hospitalización via centro_costo_check evaluator.
-- Domain: hospitalizacion
-- Evaluator: centro_costo_check (REGLA1-9 + REVERSE rules)
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'centro_costo_hospitalizacion_valido',
       'Centro de costo no válido en Hospitalización',
       'hospitalizacion', 'active', 1, 25, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'centro_costo_hospitalizacion_valido' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'centro_costo_hospitalizacion_valido' AND version = 1
);

-- Single atomic condition: centro_costo_check evaluator
-- The evaluator handles all REGLA1-9 + REVERSE rules internally.
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'centro_costo_hospitalizacion_valido' AND version = 1),
    NULL,
    'atomic',
    'centro_costo_check',
    'invoice.centro_costo',
    NULL,
    0
);
