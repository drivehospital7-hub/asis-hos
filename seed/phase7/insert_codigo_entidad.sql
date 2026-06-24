-- =============================================================================
-- Phase 7: codigo_entidad (transversal — all domains)
-- Rule: Flag rows where the Entidad Afiliación text may be malformed.
-- =============================================================================
--
-- SIMPLIFIED PLACEHOLDER VERSION
-- -----------------------------
-- The legacy detector (app/services/transversales/codigo_entidad.py):
--   1. Extracts code from "Entidad Afiliación" via regex /\{([A-Z0-9]+)\}/
--   2. Compares extracted code with "Cód Entidad Cobrar"
--   3. Flags mismatches
--
-- Current engine limitation: the tree evaluator cannot yet perform two-step
-- evaluation (extract → compare) within a single atomic condition because
-- valor_esperado is static JSONB and cannot reference another row column.
--
-- PLACEHOLDER APPROACH (this seed):
--   NOT(contains(invoice.entidad_afiliacion, "{"))
-- Detects rows where the entidad_afiliacion text does NOT contain a "{"
-- character. Since valid entity affiliation texts include codes in the
-- format {CODE}, the absence of "{" indicates a malformed entry.
-- This catches malformed/missing entity codes but does NOT perform the
-- full code comparison of the legacy detector.
--
-- FUTURE ENHANCEMENT:
--   Implement two-step composite evaluation (extract → compare) or a
--   dedicated provider that pre-extracts the code from entidad_afiliacion
--   to match the legacy detector's full behavior.
--
-- Domain: transversal (applies to all: odontologia, urgencias, equipos_basicos)
-- =============================================================================

-- Idempotent insert for the rule
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'codigo_entidad', 'Entidad Afiliación carece de código de entidad en formato esperado', 'transversal', 'active', 1, 40, 'warning', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'codigo_entidad' AND version = 1
);

-- Clean old conditions for this rule version
DELETE FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'codigo_entidad' AND version = 1);

-- Root: NOT composite node
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'codigo_entidad' AND version = 1),
    NULL,
    'composite',
    'NOT',
    NULL,
    NULL,
    0
);

-- Child of NOT: contains(invoice.entidad_afiliacion, "{")
-- If the text contains "{" → has code pattern → OK (NOT inverts)
-- If the text does NOT contain "{" → malformed → problem detected
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'codigo_entidad' AND version = 1),
    (SELECT id FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'codigo_entidad' AND version = 1) AND tipo = 'composite' AND operador = 'NOT'),
    'atomic',
    'contains',
    'invoice.entidad_afiliacion',
    '"{"'::jsonb,
    0
);
