-- =============================================================================
-- Migration Engine F17: centro_costo_urgencias detallado — OR trees
--
-- Revives the dead `centro_costo_urgencias` engine rule (legacy
-- app/services/urgencias/centro_costo_urgencias.py, 17 branches, no engine
-- seed — lookup returns `Rule not found`). detect_all.py already evaluates
-- `centro_costo_urgencias` (+ `_valido`) and filters by prioridad, so seeding
-- these trees is zero-orchestrator-change: the existing valido + detallado
-- sum picks v1 up automatically.
--
-- Trees (cat_in + eq only, never inline `in`):
--   p1 `centro_costo_urgencias` v1 (regla.prioridad=1, root OR, 90 conds):
--     F14 shared block (REGLA9/1/REV1/2/REV2/3/REV3/4/REV4/REV9/8, byte-clone
--     of 14_centro_costo_comun.sql) + REGLA5 (cat_in lab + eq ESS118 +
--     eq Intramural + NOT(lab variants)) + REVERSE5-tipo + REVERSE5-codigo
--     (CN admits lab OR lab_rev; non-CN admits lab only) +
--     INTRAMURAL_OTRAS_ENTIDADES + AMBULATORIA_PYP.
--   p2 `centro_costo_urgencias_cross` v1 (regla.prioridad=2, root OR, 7 conds):
--     2 cross tipo-factura AND-subtrees. Separate rule because the engine
--     problem dict carries no per-branch prioridad — prioridad survives only
--     at regla.prioridad level.
--
-- Catalogs (dominio 'urgencias', WHERE NOT EXISTS, byte-match frozensets):
--   centro_costo_laboratorio_urg      (CODIGOS_LABORATORIO_URGENCIAS, 15 codes)
--   centro_costo_laboratorio_urg_rev  (CODIGOS_LABORATORIO_URGENCIAS_REVERSE, 1 code)
--
-- Untouched by design: _valido trees, legacy file, detect_all.py,
-- 14_centro_costo_comun.sql (clone source only, never re-applied).
-- Rollback: deactivate v1 (estado='inactive') or revert; engine falls back
-- to _valido-only; legacy file untouched.
-- =============================================================================

-- ══════════════════════════════════════════════════════════════════════════
-- Catalogos seeds: constant sets for cat_in evaluator lookups
-- ══════════════════════════════════════════════════════════════════════════

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centro_costo_laboratorio_urg',
       '["903437","903866","903867","9062082","903833","903828","902209","906340","904903","902206","906129","906127","907009","906305","903427"]'::jsonb,
       'urgencias',
       'Códigos de laboratorio que exigen centro APOYO DIAGNOSTICO-LABORATOR CLINICO (CODIGOS_LABORATORIO_URGENCIAS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centro_costo_laboratorio_urg');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centro_costo_laboratorio_urg_rev',
       '["904902"]'::jsonb,
       'urgencias',
       'Código de laboratorio admitido solo con tipo_identificacion=CN (CODIGOS_LABORATORIO_URGENCIAS_REVERSE)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centro_costo_laboratorio_urg_rev');

-- ══════════════════════════════════════════════════════════════════════════
-- Rules: upsert by (nombre, version), never hardcoded live IDs
-- ══════════════════════════════════════════════════════════════════════════

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'centro_costo_urgencias', 'Centro de costo detallado en Urgencias — REGLAs 1-9/REVERSE + laboratorio ESS118 + intramural/ambulatoria (p1)', 'urgencias', 'active', 1, 1, 'error', true, NULL
)
ON CONFLICT (nombre, version) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros;

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'centro_costo_urgencias_cross', 'Cruces tipo-factura de centro de costo en Urgencias (p2)', 'urgencias', 'active', 1, 2, 'error', true, NULL
)
ON CONFLICT (nombre, version) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros;

-- ══════════════════════════════════════════════════════════════════════════
-- P1 tree: centro_costo_urgencias v1 (prioridad=1)
-- ══════════════════════════════════════════════════════════════════════════

DO $$
DECLARE
    _regla_id INT;
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
    cd_r5 INT; cd_r5_n1 INT; cd_r5_n2 INT;
    cd_rv5t INT; cd_rv5t_or INT; cd_rv5t_n INT;
    cd_rv5c INT; cd_rv5c_or INT; cd_rv5c_oor INT;
    cd_rv5c_cc INT; cd_rv5c_cc_n1 INT; cd_rv5c_cc_n2 INT;
    cd_rv5c_cn INT; cd_rv5c_cn_n1 INT; cd_rv5c_cn_n2 INT;
    cd_intra INT; cd_intra_n1 INT; cd_intra_n2 INT; cd_intra_n3 INT;
    cd_amb INT; cd_amb_n INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'centro_costo_urgencias' AND version = 1;
    IF _regla_id IS NULL THEN
        RETURN;
    END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: OR — any True child = MATCH (detection)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO cd_root;

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

    -- REGLA1: AND(eq(cod_tipo, "02"), eq(lab, "No"), NOT(cat_in(exceptuados)), NOT(eq(centro, DIAG)))
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

    -- REGLA3: AND(cat_in("centro_costo_pyp", codigo), NOT(eq(centro, PYP)))
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

    -- REVERSE3: AND(eq(centro, PYP), NOT(cat_in("centro_costo_pyp", codigo)))
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

    -- REGLA4: AND(cat_in("centro_costo_quirofano", codigo), NOT(eq(centro, QUIROFANO)))
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

    -- REVERSE4: AND(eq(centro, QUIROFANO), NOT(cat_in("centro_costo_quirofano", codigo)))
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

    -- REVERSE9: AND(eq(centro, FARMACIA), NOT(eq(tarifario, "Suminstros, Medicamentos")))
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

    -- REGLA8: AND(cat_in("centro_costo_hospitalizacion", codigo), NOT(eq(centro, HOSP)))
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

    -- REGLA5: lab code + ESS118 + Intramural + centro not LAB/LAB.
    -- AND(cat_in(lab, codigo), eq(entidad, ESS118), eq(tipo, Intramural),
    --     NOT(eq(centro, LAB)), NOT(eq(centro, LAB.)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 11)
    RETURNING id INTO cd_r5;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r5, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_laboratorio_urg'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r5, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', to_jsonb('ESS118'::text), 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r5, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', to_jsonb('Intramural'::text), 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r5, 'composite', 'NOT', NULL, NULL, 3)
    RETURNING id INTO cd_r5_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r5_n1, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-LABORATOR CLINICO'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r5, 'composite', 'NOT', NULL, NULL, 4)
    RETURNING id INTO cd_r5_n2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_r5_n2, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-LABORATOR CLINICO.'::text), 0);

    -- REVERSE5-tipo: centro LAB/LAB. + tipo != Intramural.
    -- AND(OR(eq(centro, LAB), eq(centro, LAB.)), NOT(eq(tipo, Intramural)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 12)
    RETURNING id INTO cd_rv5t;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5t, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO cd_rv5t_or;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5t_or, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-LABORATOR CLINICO'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5t_or, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-LABORATOR CLINICO.'::text), 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5t, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_rv5t_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5t_n, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', to_jsonb('Intramural'::text), 0);

    -- REVERSE5-codigo: centro LAB/LAB. + tipo Intramural + codigo not valid.
    -- CN admits OR(cat_in(lab), cat_in(lab_rev)); non-CN admits cat_in(lab) only.
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 13)
    RETURNING id INTO cd_rv5c;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO cd_rv5c_or;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_or, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-LABORATOR CLINICO'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_or, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-LABORATOR CLINICO.'::text), 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', to_jsonb('Intramural'::text), 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c, 'composite', 'OR', NULL, NULL, 2)
    RETURNING id INTO cd_rv5c_oor;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_oor, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO cd_rv5c_cc;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cc, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO cd_rv5c_cc_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cc_n1, 'atomic', 'eq', 'invoice.tipo_identificacion', to_jsonb('CN'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cc, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_rv5c_cc_n2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cc_n2, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_laboratorio_urg'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_oor, 'composite', 'AND', NULL, NULL, 1)
    RETURNING id INTO cd_rv5c_cn;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cn, 'atomic', 'eq', 'invoice.tipo_identificacion', to_jsonb('CN'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cn, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_rv5c_cn_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cn_n1, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_laboratorio_urg'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cn, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO cd_rv5c_cn_n2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_rv5c_cn_n2, 'atomic', 'cat_in', 'invoice.codigo', to_jsonb('centro_costo_laboratorio_urg_rev'::text), 0);

    -- INTRAMURAL_OTRAS_ENTIDADES: Intramural + entidad != ESS118 + centro not LAB/LAB.
    -- AND(eq(tipo, Intramural), NOT(eq(entidad, ESS118)),
    --     NOT(eq(centro, LAB)), NOT(eq(centro, LAB.)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 14)
    RETURNING id INTO cd_intra;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_intra, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', to_jsonb('Intramural'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_intra, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_intra_n1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_intra_n1, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', to_jsonb('ESS118'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_intra, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO cd_intra_n2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_intra_n2, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-LABORATOR CLINICO'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_intra, 'composite', 'NOT', NULL, NULL, 3)
    RETURNING id INTO cd_intra_n3;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_intra_n3, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('APOYO DIAGNOSTICO-LABORATOR CLINICO.'::text), 0);

    -- AMBULATORIA_PYP: AND(eq(tipo, Ambulatoria), NOT(eq(centro, PYP)))
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 15)
    RETURNING id INTO cd_amb;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_amb, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', to_jsonb('Ambulatoria'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_amb, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO cd_amb_n;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_amb_n, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN'::text), 0);

END $$;

-- ══════════════════════════════════════════════════════════════════════════
-- P2 rule: centro_costo_urgencias_cross v1 (prioridad=2)
-- ══════════════════════════════════════════════════════════════════════════

DO $$
DECLARE
    _regla_id INT;
    cd_root INT; cd_x1 INT; cd_x2 INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'centro_costo_urgencias_cross' AND version = 1;
    IF _regla_id IS NULL THEN
        RETURN;
    END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: OR — any True child = MATCH (detection)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO cd_root;

    -- Cross 1: Hospitalización + centro URGENCIAS → deberia HOSPITALIZACIÓN.
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO cd_x1;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_x1, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', to_jsonb('Hospitalización'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_x1, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('URGENCIAS'::text), 1);

    -- Cross 2: Urgencias + centro HOSPITALIZACIÓN → deberia URGENCIAS.
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'AND', NULL, NULL, 1)
    RETURNING id INTO cd_x2;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_x2, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', to_jsonb('Urgencias'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_x2, 'atomic', 'eq', 'invoice.centro_costo', to_jsonb('HOSPITALIZACIÓN - ESTANCIA GENERAL'::text), 1);

END $$;
