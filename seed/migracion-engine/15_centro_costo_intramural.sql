-- =============================================================================
-- Migration Engine F15: centro_costo_intramural — OR tree replacing evaluator
--
-- Replaces the black-box centro_costo_intramural evaluator with a proper
-- AND/OR/NOT condition tree for the intramural rule.
--
-- Tree = common rules (minus REGLA3/REVERSE3) + intramural-specific rules:
--   REGLA3-INTRAMURAL / REVERSE3-INTRAMURAL, REGLA10/REVERSE10,
--   REGLA6/REVERSE6, REGLA7/REVERSE7, REGLA_RESPONSABLE_URGENCIAS
-- =============================================================================

DO $$
DECLARE
    _regla_id INT;
    cd_root INT; cd_r9 INT; cd_r9_n INT;
    cd_r1 INT; cd_r1_n1 INT; cd_r1_n2 INT;
    cd_rev1 INT; cd_rev1_n INT; cd_rev1_and INT;
    cd_r2 INT; cd_r2_n INT;
    cd_rev2 INT; cd_rev2_n INT;
    cd_r4 INT; cd_r4_n INT;
    cd_rev4 INT; cd_rev4_n INT;
    cd_rev9 INT; cd_rev9_n INT;
    cd_r8 INT; cd_r8_n INT;
    -- Intramural-specific
    cd_r3i INT; cd_r3i_n INT;
    cd_rev3i INT; cd_rev3i_n INT;
    cd_r10 INT; cd_r10_n INT;
    cd_rev10 INT; cd_rev10_or INT; cd_rev10_or_n1 INT; cd_rev10_or_and INT; cd_rev10_or_and_n1 INT; cd_rev10_or_and_n2 INT;
    cd_r6 INT; cd_r6_n1 INT; cd_r6_n2 INT; cd_r6_n3 INT; cd_r6_n4 INT; cd_r6_n4_and INT;
    cd_rev6 INT; cd_rev6_or INT; cd_rev6_or_n INT;
    cd_r7 INT; cd_r7_n1 INT; cd_r7_n2 INT;
    cd_rev7 INT; cd_rev7_n INT;
    cd_resp INT; cd_resp_n1 INT; cd_resp_n2 INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'centro_costo_intramural_valido' AND version = 1;
    IF _regla_id IS NULL THEN
        RETURN;
    END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- ===================================================================
    -- Root: OR — any True child = MATCH (detection)
    -- ===================================================================
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO cd_root;

    -- ═══════════════════════════════════════════════════════════════════
    -- COMMON REGLAS (same as centro_costo_comun, WITHOUT REGLA3/REVERSE3)
    -- ═══════════════════════════════════════════════════════════════════

    -- REGLA9: AND(eq(tarifario, "Suminstros, Medicamentos"), NOT(eq(centro, FARMACIA)))
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

    -- REGLA1: AND(eq(cod_tipo, "02"), eq(lab, "No"), NOT(cat_in(exceptuados, codigo)), NOT(eq(centro, DIAG)))
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

    -- REVERSE1: AND(eq(centro, DIAG), NOT(AND(eq(cod_tipo, "02"), eq(lab, "No"))))
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

    -- REGLA2: AND(eq(cod_tipo, "14"), NOT(eq(centro, TRASLADOS)))
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

    -- REVERSE2: AND(eq(centro, TRASLADOS), NOT(eq(cod_tipo, "14")))
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

    -- REGLA4: AND(cat_in("centro_costo_quirofano"), NOT(eq(centro, QUIROFANO)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 5)
    RETURNING id INTO cd_r4;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r4, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_quirofano'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r4, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_r4_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r4_n, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO'::text), 0);

    -- REVERSE4: AND(eq(centro, QUIROFANO), NOT(cat_in("centro_costo_quirofano")))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 6)
    RETURNING id INTO cd_rev4;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev4, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev4, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_rev4_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev4_n, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_quirofano'::text), 0);

    -- REVERSE9: AND(eq(centro, FARMACIA), NOT(eq(tarifario, "Suminstros, Medicamentos")))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 7)
    RETURNING id INTO cd_rev9;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev9, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO TERAPEUTICO-FARMACIA E INSUMOS.'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev9, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_rev9_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev9_n, 'atomic', 'eq', 'invoice.tarifario', to_jsonb('Suminstros, Medicamentos'::text), 0);

    -- REGLA8: AND(cat_in("centro_costo_hospitalizacion"), NOT(eq(centro, HOSP)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 8)
    RETURNING id INTO cd_r8;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r8, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_hospitalizacion'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r8, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_r8_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r8_n, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('HOSPITALIZACIÓN - ESTANCIA GENERAL'::text), 0);

    -- ═══════════════════════════════════════════════════════════════════
    -- INTRAMURAL-SPECIFIC REGLAS
    -- ═══════════════════════════════════════════════════════════════════

    -- REGLA3-INTRAMURAL: codigo PyP → centro PyP Intramural
    -- AND(cat_in("centro_costo_pyp"), NOT(cat_in("centros_costo_pyp_intramural", centro)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 9)
    RETURNING id INTO cd_r3i;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r3i, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_pyp'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r3i, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_r3i_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r3i_n, 'atomic', 'cat_in', 'invoice.centro_costo', to_jsonb('centros_costo_pyp_intramural'::text), 0);

    -- REVERSE3-INTRAMURAL: centro PyP Intramural → codigo PyP
    -- AND(cat_in("centros_costo_pyp_intramural", centro), NOT(cat_in("centro_costo_pyp", codigo)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 10)
    RETURNING id INTO cd_rev3i;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev3i, 'atomic', 'cat_in', 'invoice.centro_costo', to_jsonb('centros_costo_pyp_intramural'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev3i, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_rev3i_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev3i_n, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_pyp'::text), 0);

    -- REGLA10: tipo=02/05 + Lab=Si → LABORATORIO CLINICO
    -- AND(cat_in("codigos_tipo_procedimiento_laboratorio", cod_tipo), eq(lab, "Si"), NOT(cat_in("centros_costo_laboratorio_validos", centro)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 11)
    RETURNING id INTO cd_r10;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r10, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', to_jsonb('codigos_tipo_procedimiento_laboratorio'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r10, 'atomic', 'eq', 'invoice.laboratorio', to_jsonb('Si'::text), 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r10, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO cd_r10_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r10_n, 'atomic', 'cat_in', 'invoice.centro_costo', to_jsonb('centros_costo_laboratorio_validos'::text), 0);

    -- REVERSE10: centro=LAB → tipo in TIPO_LAB + Lab=Si (with exceptuados)
    -- AND(cat_in("centros_costo_laboratorio_validos", centro), OR(NOT(cat_in("codigos_tipo_procedimiento_laboratorio", cod_tipo)), AND(NOT(cat_in("codigos_exceptuados", codigo)), NOT(eq(lab,"Si")))))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 12)
    RETURNING id INTO cd_rev10;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10, 'atomic', 'cat_in', 'invoice.centro_costo', to_jsonb('centros_costo_laboratorio_validos'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10, 'composite', 'OR', NULL, NULL, 1)
    RETURNING id INTO cd_rev10_or;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10_or, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO cd_rev10_or_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10_or_n1, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', to_jsonb('codigos_tipo_procedimiento_laboratorio'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10_or, 'composite', 'AND', NULL, NULL, 1)
    RETURNING id INTO cd_rev10_or_and;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10_or_and, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO cd_rev10_or_and_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10_or_and_n1, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('codigos_exceptuados'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10_or_and, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_rev10_or_and_n2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev10_or_and_n2, 'atomic', 'eq', 'invoice.laboratorio', to_jsonb('Si'::text), 0);

    -- REGLA6: tipo=05 → SALUD PUBLICA (unless lab=Si handles REGLA10)
    -- AND(eq(cod_tipo,"05"), NOT(cat_in(excl_vac)), NOT(cat_in(pyp)), NOT(eq(centro,salud)), NOT(AND(cat_in(tip_lab), eq(lab,"Si"))))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 13)
    RETURNING id INTO cd_r6;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6, 'atomic', 'eq', 'invoice.codigo_tipo_procedimiento', to_jsonb('05'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_r6_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6_n1, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('codigos_excluidos_vacunacion'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO cd_r6_n2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6_n2, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_pyp'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6, 'composite', 'NOT', NULL, NULL, 3)
    RETURNING id INTO cd_r6_n3;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6_n3, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('SALUD PUBLICA-VACUNACION  REGULAR'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6, 'composite', 'NOT', NULL, NULL, 4)
    RETURNING id INTO cd_r6_n4;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6_n4, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO cd_r6_n4_and;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6_n4_and, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', to_jsonb('codigos_tipo_procedimiento_laboratorio'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r6_n4_and, 'atomic', 'eq', 'invoice.laboratorio', to_jsonb('Si'::text), 1);

    -- REVERSE6: centro=SALUD PUBLICA → tipo=05 + not excluidos
    -- AND(eq(centro, salud), OR(NOT(eq(cod_tipo, "05")), cat_in(excl_vac, codigo)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 14)
    RETURNING id INTO cd_rev6;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev6, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('SALUD PUBLICA-VACUNACION  REGULAR'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev6, 'composite', 'OR', NULL, NULL, 1)
    RETURNING id INTO cd_rev6_or;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev6_or, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO cd_rev6_or_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev6_or_n, 'atomic', 'eq', 'invoice.codigo_tipo_procedimiento', to_jsonb('05'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev6_or, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('codigos_excluidos_vacunacion'::text), 1);

    -- REGLA7: tipo=03/04 → SERVICIOS AMBULATORIOS
    -- AND(cat_in("codigos_tipo_procedimiento_ambulatorio"), NOT(cat_in("codigos_exceptuados_ambulatorio")), NOT(eq(centro, ambulatorio)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 15)
    RETURNING id INTO cd_r7;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r7, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', to_jsonb('codigos_tipo_procedimiento_ambulatorio'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r7, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_r7_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r7_n1, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('codigos_exceptuados_ambulatorio'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r7, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO cd_r7_n2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r7_n2, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS'::text), 0);

    -- REVERSE7: centro=SERVICIOS AMBULATORIOS → tipo=03/04
    -- AND(eq(centro, ambulatorio), NOT(cat_in("codigos_tipo_procedimiento_ambulatorio")))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 16)
    RETURNING id INTO cd_rev7;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev7, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev7, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_rev7_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rev7_n, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', to_jsonb('codigos_tipo_procedimiento_ambulatorio'::text), 0);

    -- REGLA_RESPONSABLE_URGENCIAS: facturador + tipo 01/04 → URG/HOSP
    -- AND(cat_in("facturadores_urgencias", responsable), in(cod_tipo,["01","04"]), NOT(cat_in("codigos_exceptuados_responsable_urgencias", codigo)), NOT(in(centro, ["URGENCIAS","HOSPITALIZACIÓN - ESTANCIA GENERAL"])))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 17)
    RETURNING id INTO cd_resp;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_resp, 'atomic', 'cat_in', 'invoice.responsable_cierra', to_jsonb('facturadores_urgencias'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_resp, 'atomic', 'in', 'invoice.codigo_tipo_procedimiento', '["01","04"]'::jsonb, 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_resp, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO cd_resp_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_resp_n1, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('codigos_exceptuados_responsable_urgencias'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_resp, 'composite', 'NOT', NULL, NULL, 3)
    RETURNING id INTO cd_resp_n2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_resp_n2, 'atomic', 'in', 'invoice.centro_costo', '["URGENCIAS","HOSPITALIZACIÓN - ESTANCIA GENERAL"]'::jsonb, 0);

END $$;
