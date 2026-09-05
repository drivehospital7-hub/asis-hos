-- =============================================================================
-- Phase 1: cantidades_soat_urgencias
-- Rule: SOAT + restricted code + cantidad != 1 → problem detected.
-- Domain: urgencias
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'cantidades_soat_urgencias', 'Cantidad SOAT no es 1 para código restringido en urgencias', 'urgencias', 'active', 1, 25, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'cantidades_soat_urgencias' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
    _not_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cantidades_soat_urgencias' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: AND
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Child 1: eq(tarifario, "SOAT")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tarifario', '"SOAT"', 0);

    -- Child 2: in(codigo, restricted_codes)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.codigo',
            '["39145", "38114", "38915", "39131"]', 1);

    -- Child 3: NOT — composite
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO _not_id;

    -- Child 3.1: eq(cantidad, 1) — inside NOT
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _not_id, 'atomic', 'eq', 'invoice.cantidad', '1', 0);
END $$;
