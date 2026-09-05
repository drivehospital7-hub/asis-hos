-- =============================================================================
-- Phase 2: profesional_odontologia_valido
-- Rule: Flag invoices where codigo_profesional is NOT in the valid Odontología list.
-- Domain: odontologia
-- Condition: NOT(in(codigo_profesional, ["03424","03007","01329","01251","01330","03698"]))
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'profesional_odontologia_valido', 'Profesional no válido en Odontología', 'odontologia', 'active', 1, 40, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'profesional_odontologia_valido' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
    _not_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'profesional_odontologia_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: NOT
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Child: in(codigo_profesional, valid_codes)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.codigo_profesional',
        '["03424","03007","01329","01251","01330","03698"]', 0);
END $$;
