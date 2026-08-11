-- =============================================================================
-- Migration Engine F4: centro_costo_intramural_valido
-- Rule: Centro de costo rules for Intramural via centro_costo_intramural evaluator.
-- Domain: intramural
-- Evaluator: centro_costo_intramural (common rules 1-9 + 5 intramural-specific)
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'centro_costo_intramural_valido',
       'Centro de costo no valido en Intramural',
       'intramural', 'active', 1, 25, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'centro_costo_intramural_valido' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'centro_costo_intramural_valido' AND version = 1
);

-- Single atomic condition: centro_costo_intramural evaluator
-- The evaluator handles all common rules (1-9, without REGLA3) + 5 intramural-specific
-- rules (REGLA3-INTRAMURAL, REGLA6/REVERSE6, REGLA7/REVERSE7, REGLA10/REVERSE10,
-- REGLA_RESPONSABLE_URGENCIAS) internally.
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'centro_costo_intramural_valido' AND version = 1),
    NULL,
    'atomic',
    'centro_costo_intramural',
    'invoice.centro_costo',
    NULL,
    0
);
