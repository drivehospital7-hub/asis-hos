-- Rule 61 must have one OR root. Move only its two known loose code conditions
-- under that root, preserving their existing relative order.
DO $$
DECLARE
    or_root_id integer;
BEGIN
    SELECT id
    INTO or_root_id
    FROM condiciones
    WHERE regla_id = 61
      AND padre_id IS NULL
      AND tipo = 'composite'
      AND operador = 'OR'
    ORDER BY id
    LIMIT 1;

    IF or_root_id IS NULL THEN
        RAISE EXCEPTION 'Rule 61 OR root was not found';
    END IF;

    WITH loose_conditions AS (
        SELECT
            c.id,
            row_number() OVER (ORDER BY c.orden, c.id) - 1 AS relative_order
        FROM condiciones c
        WHERE c.regla_id = 61
          AND c.padre_id IS NULL
          AND c.tipo = 'atomic'
          AND c.fuente_datos = 'invoice.codigo'
          AND c.valor_esperado #>> '{}' IN ('906317', '906249')
    ), next_order AS (
        SELECT COALESCE(MAX(orden), -1) + 1 AS value
        FROM condiciones
        WHERE padre_id = or_root_id
    )
    UPDATE condiciones c
    SET padre_id = or_root_id,
        orden = next_order.value + loose.relative_order
    FROM loose_conditions loose
    CROSS JOIN next_order
    WHERE c.id = loose.id;
END $$;
