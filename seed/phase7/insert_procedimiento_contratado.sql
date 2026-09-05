-- =============================================================================
-- Phase 7: procedimiento_contratado / cups_sin_contrato (transversal)
-- Rule: Flag CUPS codes that are NOT contracted for the entity.
-- =============================================================================
--
-- The CupsContratadoEvaluator implements the full multi-table join
-- (eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento)
-- and all 6 exception branches (farmacia skip, urgencias nota_hoja,
-- CAP+ESS118, CAP+EPSS41, codigo_equiv fallback, FEV autorizado).
--
-- The evaluator returns True when the CUPS IS properly contracted.
-- The NOT wrapper inverts the result: NOT(True) → False = no detection,
-- NOT(False) → True = MATCH (problem detected).
--
-- See: app/services/engine/evaluators.py → CupsContratadoEvaluator
--
-- Domain: transversal (applies to all: odontologia, urgencias, equipos_basicos)
-- =============================================================================

-- Idempotent insert for the rule
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'cups_sin_contrato', 'CUPS no contratado para la entidad facturadora', 'transversal', 'active', 1, 35, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1
);

-- Clean old conditions for this rule version
DELETE FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1);

-- Root: NOT composite node
--   NOT(cups_contratado(invoice.codigo))
--   Evaluator returns True when contracted; NOT inverts to MATCH when not contracted.
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1),
    NULL,
    'composite',
    'NOT',
    NULL,
    NULL,
    0
);

-- Child of NOT: atomic cups_contratado check
-- Evaluator performs the full contractual chain + exception branches.
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1),
    (SELECT id FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1) AND tipo = 'composite' AND operador = 'NOT'),
    'atomic',
    'cups_contratado',
    'invoice.codigo',
    NULL,
    0
);
