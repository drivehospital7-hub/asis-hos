-- =============================================================================
-- Migration Engine F5: bacteriologas_cronograma
-- Rule: CronogramaCheckEvaluator — valida profesional contra cronograma del día.
-- Domain: intramural
-- Evaluator: cronograma_check (custom evaluator)
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, parametros, severidad, activo)
SELECT 'bacteriologas_cronograma',
       'Bacterióloga debe estar en cronograma del día — Intramural tipo 02/05 con Laboratorio=Si',
       'intramural', 'active', 1, 60,
       '[]',
       'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'bacteriologas_cronograma' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'bacteriologas_cronograma' AND version = 1
);

-- Single atomic condition: cronograma_check invoca el evaluador custom
-- row_value = codigo_profesional from the sheet
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'bacteriologas_cronograma' AND version = 1),
    NULL,
    'atomic',
    'cronograma_check',
    'invoice.codigo_profesional',
    NULL,
    0
);
