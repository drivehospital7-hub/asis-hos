-- =============================================================================
-- Migration Engine F16: sala_observacion_valido — OR tree replacing evaluator
--
-- Replaces the black-box SalaObservacionEvaluator (sala_obs_check) with a
-- proper AND/OR/NOT condition tree. Same pattern as centro_costo (F14/F15).
--
-- The evaluator had a known bug: estancia ≤ 2h returned False even when the
-- sala code was wrong. Sub-rule 6 explicitly detects this case.
--
-- ±1h tolerance at the 6h boundary due to date.horas(int) vs evaluator(float).
-- Accepted for clinical rules (±1h does not change treatment classification).
-- =============================================================================

-- ══════════════════════════════════════════════════════════════════════════
-- Catalogos seeds: constant sets for cat_in evaluator lookups
-- ══════════════════════════════════════════════════════════════════════════

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'sala_codes',
       '["5DSB01","05DSB01","129B02","38114","38915"]'::jsonb,
       'urgencias',
       'Códigos de sala de observación activadores (SALA_CODES)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'sala_codes');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'entidades_ess',
       '["ESS118","ESSC18"]'::jsonb,
       'urgencias',
       'Entidades ESS que usan 05DSB01 para >6h (ENTITIES_05DSB01)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'entidades_ess');

-- ══════════════════════════════════════════════════════════════════════════
-- Rule: sala_observacion_valido — replace evaluator with condition tree
-- ══════════════════════════════════════════════════════════════════════════

DO $$
DECLARE
    _regla_id INT;
    -- Node ID variables
    cd_root_and INT; cd_root_or INT;
    cd_sr1 INT; cd_sr1_not INT;
    cd_sr2 INT; cd_sr2_not INT;
    cd_sr3 INT; cd_sr3_not_soat INT; cd_sr3_not INT;
    cd_sr4 INT; cd_sr4_not_soat INT; cd_sr4_not_ess INT; cd_sr4_not INT;
    cd_sr5 INT; cd_sr5_not_soat INT; cd_sr5_not INT;
    cd_sr6 INT; cd_sr6_not INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'sala_observacion_valido' AND version = 1;
    IF _regla_id IS NULL THEN
        RETURN;
    END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- ===================================================================
    -- Root: AND wrapper for tipo_factura_descripcion filter
    -- Primero filtramos solo facturas Urgencias (mismo filtro que el evaluador)
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO cd_root_and;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root_and, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', to_jsonb('Urgencias'::text), 0);

    -- ===================================================================
    -- Root: OR — any True child = MATCH (detection)
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root_and, 'composite', 'OR', NULL, NULL, 1)
    RETURNING id INTO cd_root_or;

    -- ===================================================================
    -- Sub-rule 1: SOAT, >6h → necesita 38114
    -- AND(eq(tarifario, "SOAT"), gt(date.horas, 6), cat_in(sala_codes, codigo), NOT(eq(codigo, "38114")))
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root_or, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO cd_sr1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr1, 'atomic', 'eq', 'invoice.tarifario', to_jsonb('SOAT'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr1, 'atomic', 'gt', 'date.horas', 6, 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr1, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('sala_codes'::text), 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr1, 'composite', 'NOT', NULL, NULL, 3)
    RETURNING id INTO cd_sr1_not;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr1_not, 'atomic', 'eq', 'invoice.codigo', to_jsonb('38114'::text), 0);

    -- ===================================================================
    -- Sub-rule 2: SOAT, 2-6h → necesita 38915
    -- AND(eq(tarifario, "SOAT"), gte(date.horas, 2), lte(date.horas, 6),
    --     cat_in(sala_codes, codigo), NOT(eq(codigo, "38915")))
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root_or, 'composite', 'AND', NULL, NULL, 1)
    RETURNING id INTO cd_sr2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr2, 'atomic', 'eq', 'invoice.tarifario', to_jsonb('SOAT'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr2, 'atomic', 'gte', 'date.horas', 2, 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr2, 'atomic', 'lte', 'date.horas', 6, 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr2, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('sala_codes'::text), 3);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr2, 'composite', 'NOT', NULL, NULL, 4)
    RETURNING id INTO cd_sr2_not;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr2_not, 'atomic', 'eq', 'invoice.codigo', to_jsonb('38915'::text), 0);

    -- ===================================================================
    -- Sub-rule 3: No-SOAT, >6h, ESS → necesita 05DSB01
    -- AND(NOT(eq(tarifario, "SOAT")), gt(date.horas, 6),
    --     cat_in(entidades_ess, codigo_entidad_cobrar),
    --     cat_in(sala_codes, codigo), NOT(eq(codigo, "05DSB01")))
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root_or, 'composite', 'AND', NULL, NULL, 2)
    RETURNING id INTO cd_sr3;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr3, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO cd_sr3_not_soat;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr3_not_soat, 'atomic', 'eq', 'invoice.tarifario', to_jsonb('SOAT'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr3, 'atomic', 'gt', 'date.horas', 6, 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr3, 'atomic', 'cat_in', 'invoice.codigo_entidad_cobrar', to_jsonb('entidades_ess'::text), 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr3, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('sala_codes'::text), 3);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr3, 'composite', 'NOT', NULL, NULL, 4)
    RETURNING id INTO cd_sr3_not;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr3_not, 'atomic', 'eq', 'invoice.codigo', to_jsonb('05DSB01'::text), 0);

    -- ===================================================================
    -- Sub-rule 4: No-SOAT, >6h, No-ESS → necesita 129B02
    -- AND(NOT(eq(tarifario, "SOAT")), gt(date.horas, 6),
    --     NOT(cat_in(entidades_ess, codigo_entidad_cobrar)),
    --     cat_in(sala_codes, codigo), NOT(eq(codigo, "129B02")))
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root_or, 'composite', 'AND', NULL, NULL, 3)
    RETURNING id INTO cd_sr4;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr4, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO cd_sr4_not_soat;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr4_not_soat, 'atomic', 'eq', 'invoice.tarifario', to_jsonb('SOAT'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr4, 'atomic', 'gt', 'date.horas', 6, 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr4, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO cd_sr4_not_ess;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr4_not_ess, 'atomic', 'cat_in', 'invoice.codigo_entidad_cobrar', to_jsonb('entidades_ess'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr4, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('sala_codes'::text), 3);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr4, 'composite', 'NOT', NULL, NULL, 4)
    RETURNING id INTO cd_sr4_not;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr4_not, 'atomic', 'eq', 'invoice.codigo', to_jsonb('129B02'::text), 0);

    -- ===================================================================
    -- Sub-rule 5: No-SOAT, 2-6h → necesita 5DSB01
    -- AND(NOT(eq(tarifario, "SOAT")), gte(date.horas, 2), lte(date.horas, 6),
    --     cat_in(sala_codes, codigo), NOT(eq(codigo, "5DSB01")))
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root_or, 'composite', 'AND', NULL, NULL, 4)
    RETURNING id INTO cd_sr5;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr5, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO cd_sr5_not_soat;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr5_not_soat, 'atomic', 'eq', 'invoice.tarifario', to_jsonb('SOAT'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr5, 'atomic', 'gte', 'date.horas', 2, 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr5, 'atomic', 'lte', 'date.horas', 6, 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr5, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('sala_codes'::text), 3);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr5, 'composite', 'NOT', NULL, NULL, 4)
    RETURNING id INTO cd_sr5_not;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr5_not, 'atomic', 'eq', 'invoice.codigo', to_jsonb('5DSB01'::text), 0);

    -- ===================================================================
    -- Sub-rule 6 (bug fix): ≤2h → solo 5DSB01 permitido
    -- AND(lte(date.horas, 2), cat_in(sala_codes, codigo), NOT(eq(codigo, "5DSB01")))
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root_or, 'composite', 'AND', NULL, NULL, 5)
    RETURNING id INTO cd_sr6;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr6, 'atomic', 'lte', 'date.horas', 2, 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr6, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('sala_codes'::text), 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr6, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO cd_sr6_not;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_sr6_not, 'atomic', 'eq', 'invoice.codigo', to_jsonb('5DSB01'::text), 0);

END $$;
