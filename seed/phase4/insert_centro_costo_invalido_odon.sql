-- =============================================================================
-- Phase 4: centro_costo_odontologia_valido
-- Rule: Flag invoices where centro_costo is NOT in the valid Odontología list.
-- Domain: odontologia
-- Condition: NOT(in(centro_costo, valid_centers))
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'centro_costo_odontologia_valido', 'Centro de costo no válido en Odontología', 'odontologia', 'active', 1, 25, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'centro_costo_odontologia_valido' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'centro_costo_odontologia_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: NOT
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Child: in(centro_costo, valid_centers)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.centro_costo',
        '["ODONTOLOGIA","SERVICIOS ODONTOLOGIA -EXTRAMURALES"]', 0);
END $$;
