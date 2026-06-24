-- =============================================================================
-- Phase 6: revision_cantidad (simplified group-by version)
-- Rule: Flag invoices where total quantity > 1 (simplified from legacy).
-- Domain: urgencias
-- Evaluation: group-by → sum aggregation
-- 
-- NOTE: This is a simplified engine version. The full legacy detector
-- (revision_cantidad.py) handles special codes (02+Lab=No, 09/12, 903883,
-- V03AN0101, etc.) via per-row logic. Those complex rules remain in the
-- legacy Python detector until full condition tree modeling is developed.
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
SELECT 'revision_cantidad_urgencias',
       'Revisión necesaria: cantidad anómala por factura (suma > 1)',
       'urgencias', 'active', 1, 40, 'warning', true,
       '[{"group_by": "numero_factura", "aggregations": [{"function": "sum", "field": "cantidad", "target": "sum_cantidad"}]}]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'revision_cantidad_urgencias' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'revision_cantidad_urgencias' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: gt(invoice.sum_cantidad, 1)
    -- Total quantity across group > 1 → MATCH
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'gt', 'invoice.sum_cantidad', '1', 0);
END $$;
