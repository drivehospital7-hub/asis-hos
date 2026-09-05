-- =============================================================================
-- Migration Engine F14: centro_costo_comun — OR tree replacing evaluator
--
-- Replaces the black-box centro_costo_check evaluator with proper AND/OR/NOT
-- condition trees for 4 rules: hospitalizacion, equipos_basicos, odontologia,
-- and urgencias. Each REGLA from CentroCostoCheckEvaluator becomes a sub-tree.
--
-- The tree uses cat_in(catalog_key, invoice.field) for DB-backed constant sets.
-- Case-insensitive matching via CatalogInEvaluator's new strip+upper fallback.
-- =============================================================================

DO $$
DECLARE
    _rule_names TEXT[] := ARRAY[
        'centro_costo_hospitalizacion_valido',
        'centro_costo_equipos_basicos_valido',
        'centro_costo_odontologia_valido',
        'centro_costo_urgencias_valido'
    ];
    _rule_name TEXT;
    _regla_id INT;
    -- Node ID variables (reused per iteration)
    cd_root INT; cd_r9 INT; cd_r9_n INT;
    cd_r1 INT; cd_r1_n1 INT; cd_r1_n2 INT;
    cd_rev1 INT; cd_rev1_n INT; cd_rev1_and INT;
    cd_r2 INT; cd_r2_n INT;
    cd_rev2 INT; cd_rev2_n INT;
    cd_r3 INT; cd_r3_n INT;
    cd_rev3 INT; cd_rev3_n INT;
    cd_r4 INT; cd_r4_n INT;
    cd_rev4 INT; cd_rev4_n INT;
    cd_rev9 INT; cd_rev9_n INT;
    cd_r8 INT; cd_r8_n INT;
    cd_invalid_centro INT;
BEGIN
    FOREACH _rule_name IN ARRAY _rule_names LOOP
        SELECT id INTO _regla_id FROM reglas WHERE nombre = _rule_name AND version = 1;
        IF _regla_id IS NULL THEN
            CONTINUE;
        END IF;

        DELETE FROM condiciones WHERE regla_id = _regla_id;

        -- ===================================================================
        -- Root: OR — any True child = MATCH (detection)
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
        RETURNING id INTO cd_root;

        -- ===================================================================
        -- REGLA9: Tarifario = farmacia → centro = FARMACIA
        -- AND(eq(tarifario, "Suminstros, Medicamentos"), NOT(eq(centro, FARMACIA)))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 0)
        RETURNING id INTO cd_r9;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r9, 'atomic', 'eq', 'invoice.tarifario', to_jsonb('Suminstros, Medicamentos'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r9, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_r9_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r9_n, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO TERAPEUTICO-FARMACIA E INSUMOS.'::text), 0);

        -- ===================================================================
        -- REGLA1: cod_tipo=02 + lab=No + not exceptuado → centro=APOYO_DIAG
        -- AND(eq(cod_tipo, "02"), eq(lab, "No"), NOT(cat_in(exceptuados, codigo)), NOT(eq(centro, DIAG)))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 1)
        RETURNING id INTO cd_r1;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r1, 'atomic', 'eq', 'invoice.codigo_tipo_procedimiento', to_jsonb('02'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r1, 'atomic', 'eq', 'invoice.laboratorio', to_jsonb('No'::text), 1);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r1, 'composite', 'NOT', NULL, NULL, 2)
        RETURNING id INTO cd_r1_n1;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r1_n1, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('codigos_exceptuados'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r1, 'composite', 'NOT', NULL, NULL, 3)
        RETURNING id INTO cd_r1_n2;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r1_n2, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-IMAGENOLOGIA'::text), 0);

        -- ===================================================================
        -- REVERSE1: centro=APOYO_DIAG → cod_tipo=02 + lab=No
        -- AND(eq(centro, DIAG), NOT(AND(eq(cod_tipo, "02"), eq(lab, "No"))))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 2)
        RETURNING id INTO cd_rev1;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev1, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-IMAGENOLOGIA'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev1, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_rev1_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev1_n, 'composite', 'AND', NULL, NULL, 0)
        RETURNING id INTO cd_rev1_and;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev1_and, 'atomic', 'eq', 'invoice.codigo_tipo_procedimiento', to_jsonb('02'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev1_and, 'atomic', 'eq', 'invoice.laboratorio', to_jsonb('No'::text), 1);

        -- ===================================================================
        -- REGLA2: cod_tipo=14 (traslados) → centro=TRASLADOS
        -- AND(eq(cod_tipo, "14"), NOT(eq(centro, TRASLADOS)))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 3)
        RETURNING id INTO cd_r2;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r2, 'atomic', 'eq', 'invoice.codigo_tipo_procedimiento', to_jsonb('14'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r2, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_r2_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r2_n, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('TRASLADOS'::text), 0);

        -- ===================================================================
        -- REVERSE2: centro=TRASLADOS → cod_tipo=14
        -- AND(eq(centro, TRASLADOS), NOT(eq(cod_tipo, "14")))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 4)
        RETURNING id INTO cd_rev2;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev2, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('TRASLADOS'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev2, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_rev2_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev2_n, 'atomic', 'eq', 'invoice.codigo_tipo_procedimiento', to_jsonb('14'::text), 0);

        -- ===================================================================
        -- REGLA3: codigo PyP → centro=PYP
        -- AND(cat_in("centro_costo_pyp", codigo), NOT(eq(centro, PYP)))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 5)
        RETURNING id INTO cd_r3;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r3, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_pyp'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r3, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_r3_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r3_n, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN'::text), 0);

        -- ===================================================================
        -- REVERSE3: centro=PYP → codigo PyP
        -- AND(eq(centro, PYP), NOT(cat_in("centro_costo_pyp", codigo)))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 6)
        RETURNING id INTO cd_rev3;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev3, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev3, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_rev3_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev3_n, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_pyp'::text), 0);

        -- ===================================================================
        -- REGLA4: codigo quirofano → centro=QUIROFANO
        -- AND(cat_in("centro_costo_quirofano", codigo), NOT(eq(centro, QUIROFANO)))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 7)
        RETURNING id INTO cd_r4;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r4, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_quirofano'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r4, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_r4_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r4_n, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO'::text), 0);

        -- ===================================================================
        -- REVERSE4: centro=QUIROFANO → codigo quirofano
        -- AND(eq(centro, QUIROFANO), NOT(cat_in("centro_costo_quirofano", codigo)))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 8)
        RETURNING id INTO cd_rev4;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev4, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev4, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_rev4_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev4_n, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_quirofano'::text), 0);

        -- ===================================================================
        -- REVERSE9: centro=FARMACIA → tarifario farmacia
        -- AND(eq(centro, FARMACIA), NOT(eq(tarifario, "Suminstros, Medicamentos")))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 9)
        RETURNING id INTO cd_rev9;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev9, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO TERAPEUTICO-FARMACIA E INSUMOS.'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev9, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_rev9_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_rev9_n, 'atomic', 'eq', 'invoice.tarifario', to_jsonb('Suminstros, Medicamentos'::text), 0);

        -- ===================================================================
        -- REGLA8: codigo hospitalizacion → centro=HOSPITALIZACION
        -- AND(cat_in("centro_costo_hospitalizacion", codigo), NOT(eq(centro, HOSP)))
        -- ===================================================================
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 10)
        RETURNING id INTO cd_r8;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r8, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_hospitalizacion'::text), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r8, 'composite', 'NOT', NULL, NULL, 1)
        RETURNING id INTO cd_r8_n;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, cd_r8_n, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('HOSPITALIZACIÓN - ESTANCIA GENERAL'::text), 0);

        -- URGENCIAS: any center outside the authoritative valid-center catalog
        -- must be detected independently of cross-field rules.
        IF _rule_name = 'centro_costo_urgencias_valido' THEN
            INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
            VALUES (_regla_id, cd_root, 'composite', 'NOT', NULL, NULL, 11)
            RETURNING id INTO cd_invalid_centro;

            INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
            VALUES (_regla_id, cd_invalid_centro, 'atomic', 'cat_in', 'invoice.centro_costo', to_jsonb('centros_costo_validos_urgencias'::text), 0);
        END IF;

    END LOOP;
END $$;
