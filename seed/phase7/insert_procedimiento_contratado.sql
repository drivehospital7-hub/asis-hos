-- =============================================================================
-- Phase 7: procedimiento_contratado / cups_sin_contrato (transversal)
-- Rule: Flag CUPS codes that do NOT exist in the procedimiento table catalog.
-- =============================================================================
--
-- The legacy detector (app/services/transversales/procedimiento_contratado.py)
-- performs a complex multi-table join (eps_contratado → eps_nota → nota_hoja →
-- notas_tecnicas → procedimiento) to verify that each (cups, entidad) pair
-- is contracted. It also handles edge cases like urgencias, CAP invoices,
-- and FEV authorizations.
--
-- ENGINE VERSION (this seed):
--   Simplified check: NOT(exists_in_db(invoice.codigo, {"table":"procedimiento","field":"cups"}))
--   Verifies that the CUPS code exists in the procedimiento table catalog.
--   If the code doesn't exist in the DB → MATCH (problem detected).
--
--   This is a SIMPLIFICATION of the legacy detector. It only checks catalog
--   existence, not the full contractual chain (eps_contratado → notas_tecnicas).
--   The full contractual validation (with entity-specific exceptions) requires
--   a more complex condition tree or a dedicated compound evaluator.
--
-- FUTURE ENHANCEMENT:
--   Extend the condition tree to include the full contractual chain:
--   exists_in_db(eps_contratado + nota_hoja + notas_tecnicas + procedimiento)
--   Or create a dedicated "cups_contratado" evaluator that implements the
--   full multi-table join with entity exceptions.
--
-- Domain: transversal (applies to all: odontologia, urgencias, equipos_basicos)
-- =============================================================================

-- Idempotent insert for the rule
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'cups_sin_contrato', 'CUPS no encontrado en el catálogo de procedimientos', 'transversal', 'active', 1, 35, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1
);

-- Clean old conditions for this rule version
DELETE FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1);

-- Root: NOT composite node
--   NOT(exists_in_db(invoice.codigo, procedimiento.cups))
--   If code NOT in catalog → problem detected
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

-- Child of NOT: atomic exists_in_db check
-- Check if the invoice code exists in procedimiento.cups
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1),
    (SELECT id FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1) AND tipo = 'composite' AND operador = 'NOT'),
    'atomic',
    'exists_in_db',
    'invoice.codigo',
    '{"table": "procedimiento", "field": "cups"}'::jsonb,
    0
);
