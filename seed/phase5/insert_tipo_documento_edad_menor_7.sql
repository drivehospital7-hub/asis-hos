-- =============================================================================
-- Phase 5: tipo_documento_edad_menor_7
-- Rule: Flag invoices where age < 7 and tipo_identificacion is NOT "RC".
-- Domain: transversal
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'tipo_documento_edad_menor_7',
       'Tipo de identificación incorrecto para menor de 7 años (debe ser RC)',
       'transversal', 'active', 1, 30, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'tipo_documento_edad_menor_7' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
    _not_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_documento_edad_menor_7' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: AND
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Child 1: lt(date.edad, 7)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'lt', 'date.edad', '7', 0);

    -- Child 2: NOT(eq(tipo_identificacion, "RC"))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _not_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"RC"', 0);
END $$;
