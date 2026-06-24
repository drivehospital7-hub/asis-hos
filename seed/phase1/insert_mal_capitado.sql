-- =============================================================================
-- Phase 1: mal_capitado
-- Rule: Detect mal capitado patterns.
--   Pattern 1: codes G03XB01/A02BB01 with factura NOT containing "FEV"
--   Pattern 2: factura contains "CAP" with entidad != "ESS118"
-- Domain: urgencias
-- Note: uses 'contains' as temporary stand-in for startswith (Phase 5 adds startswith).
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'mal_capitado', 'Factura mal capitada detectada (código FEV/CAP entidad)', 'urgencias', 'active', 1, 30, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'mal_capitado' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
    _g1_id INT;
    _g1_not_id INT;
    _g2_id INT;
    _g2_not_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'mal_capitado' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: OR
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Group 1: AND (pattern 1 — code without FEV)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _g1_id;

    -- G1.1: in(codigo, ["G03XB01", "A02BB01"])
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g1_id, 'atomic', 'in', 'invoice.codigo', '["G03XB01", "A02BB01"]', 0);

    -- G1.2: NOT
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g1_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _g1_not_id;

    -- G1.2.1: contains(factura, "FEV")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g1_not_id, 'atomic', 'contains', 'invoice.numero_factura', '"FEV"', 0);

    -- Group 2: AND (pattern 2 — CAP without ESS118)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 1)
    RETURNING id INTO _g2_id;

    -- G2.1: contains(factura, "CAP")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g2_id, 'atomic', 'contains', 'invoice.numero_factura', '"CAP"', 0);

    -- G2.2: NOT
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g2_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _g2_not_id;

    -- G2.2.1: eq(entidad, "ESS118")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g2_not_id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"', 0);
END $$;
