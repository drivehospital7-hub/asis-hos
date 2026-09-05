-- =============================================================================
-- Phase 1: cups_equivalentes
-- Rule: Detect CUPS codes with known substitution equivalents.
--   890201 → use 890701, 129B01 → use 129B02,
--   890205 + entity NOT in (ESS118, ESSC18) → use 890405,
--   939402 + Hospitalización → error, 12333 + Hospitalización → error
-- Domain: urgencias
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'cups_equivalentes', 'Código CUPS con equivalente conocido detectado', 'urgencias', 'active', 1, 5, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'cups_equivalentes' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;

    _b3_id INT;
    _b3_not_id INT;

    _b4_id INT;

    _b5_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cups_equivalentes' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: OR
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Branch 1: eq(codigo, "890201")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.codigo', '"890201"', 0);

    -- Branch 2: eq(codigo, "129B01")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.codigo', '"129B01"', 1);

    -- Branch 3: AND (890205 + entity NOT ESS118/ESSC18)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 2)
    RETURNING id INTO _b3_id;

    -- B3.1: eq(codigo, "890205")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b3_id, 'atomic', 'eq', 'invoice.codigo', '"890205"', 0);

    -- B3.2: NOT
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b3_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _b3_not_id;

    -- B3.2.1: in(entidad, ["ESS118", "ESSC18"])
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b3_not_id, 'atomic', 'in', 'invoice.codigo_entidad_cobrar', '["ESS118", "ESSC18"]', 0);

    -- Branch 4: AND (939402 + Hospitalización)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 3)
    RETURNING id INTO _b4_id;

    -- B4.1: eq(codigo, "939402")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b4_id, 'atomic', 'eq', 'invoice.codigo', '"939402"', 0);

    -- B4.2: eq(tipo_factura, "Hospitalización")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b4_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 1);

    -- Branch 5: AND (12333 + Hospitalización)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 4)
    RETURNING id INTO _b5_id;

    -- B5.1: eq(codigo, "12333")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b5_id, 'atomic', 'eq', 'invoice.codigo', '"12333"', 0);

    -- B5.2: eq(tipo_factura, "Hospitalización")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b5_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 1);
END $$;
