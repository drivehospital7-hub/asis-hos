-- =============================================================================
-- Migration Engine F4: revision_cantidad_intramural
-- Rule: Cascade threshold check for Intramural quantity revisions.
-- Domain: intramural
-- Evaluator: revision_cantidad_intramural (cascade: 02+Lab=No→>2, 03/04→>13, general→>1)
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'revision_cantidad_intramural',
       'Cantidad fuera de rango en Intramural — requiere revision manual',
       'intramural', 'active', 1, 25, 'warning', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'revision_cantidad_intramural' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'revision_cantidad_intramural' AND version = 1
);

-- Single atomic condition: revision_cantidad_intramural evaluator
-- The evaluator implements the cascade internally:
-- 1. tipo=02 + Lab=No → Cant > 2
-- 2. tipo=03/04 → Cant > 13
-- 3. General → Cant > 1
-- With specific code limits (CODIGOS_LIMITE_ESPECIFICO_INTRAMURAL) checked first.
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'revision_cantidad_intramural' AND version = 1),
    NULL,
    'atomic',
    'revision_cantidad_intramural',
    'invoice.cantidad',
    NULL,
    0
);
