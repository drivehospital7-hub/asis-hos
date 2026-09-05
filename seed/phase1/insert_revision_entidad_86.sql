-- =============================================================================
-- Phase 1: revision_entidad_86
-- Rule: Flag rows where codigo_entidad_cobrar equals "86" for manual review.
-- Domain: urgencias
-- =============================================================================

-- Idempotent insert for the rule
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'revision_entidad_86', 'Revisión necesaria para entidad 86', 'urgencias', 'active', 1, 10, 'warning', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'revision_entidad_86' AND version = 1
);

-- Clean old conditions for this rule version
DELETE FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'revision_entidad_86' AND version = 1);

-- Condition: atomic eq(codigo_entidad_cobrar, "86")
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'revision_entidad_86' AND version = 1),
    NULL,
    'atomic',
    'eq',
    'invoice.codigo_entidad_cobrar',
    '"86"',
    0
);
