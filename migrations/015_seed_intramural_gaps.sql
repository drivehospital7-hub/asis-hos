-- =============================================================================
-- 015_seed_intramural_gaps.sql
--
-- Seeds 4 of the 7 intramural GAP rules (Ref #1) as active v1 by
-- (nombre, version), idempotent ON CONFLICT + DELETE+rebuild pattern like
-- 010/011/012/013/014. Never hardcodes live row IDs, never uses
-- BEGIN/COMMIT or MAX(id) parenting (011 no-transaction-control rule).
--
-- Seeded (4 total, all dominio='intramural', estado='active', v1):
--   1. bacteriologas_cronograma       (1 cond, cronograma_check on
--                                        invoice.codigo_profesional;
--                                        src seed/migracion-engine/
--                                        09_bacteriologas_cronograma.sql
--                                        verbatim: filters + bypasses live
--                                        inside CronogramaCheckEvaluator)
--   2. centro_costo_intramural_valido (100 conds = OR root + 18 AND
--                                        branches; src seed/migracion-engine/
--                                        15_centro_costo_intramural.sql
--                                        verbatim — the F15 OR tree that
--                                        replaces the deprecated
--                                        centro_costo_intramural evaluator.
--                                        This ALIGNS F15: its DO block did
--                                        SELECT id ... IF NULL RETURN (dangling);
--                                        after 015 the rule exists, so F15 is
--                                        a no-op re-application, not a skip.)
--   3. duplicado_id_codigo_05         (1 cond gte invoice.count '2' +
--                                        group_by (identificacion, codigo,
--                                        codigo_dx_principal) filter
--                                        codigo_tipo_procedimiento='05';
--                                        src seed/migracion-engine/
--                                        07_duplicado_id_codigo_05.sql
--                                        verbatim. KNOWN v1 DELTA (same class
--                                        as the 013 revision_cantidad_urgencias
--                                        delta): the 993505 + facturadores-
--                                        urgencias exclusions live in
--                                        intramural/detect_all.py post-
--                                        processing (lines ~298-354), which
--                                        runs at wiring time — not in v1
--                                        group params (single filter_field
--                                        only, engine.py). Wiring follow-up.)
--   4. revision_cantidad_intramural    (1 cond revision_cantidad_intramural
--                                        on invoice.cantidad; src
--                                        seed/migracion-engine/
--                                        06_revision_cantidad_intramural.sql
--                                        verbatim: cascade 02+Lab=No→>2,
--                                        03/04→>13, general→>1 + specific
--                                        limit 901101:3, all from
--                                        app/constants/intramural.py)
--
-- Explicitly NOT seeded (3 — documented skips, need product input):
--   - ide_contrato_simple: IdeContratoSimpleEvaluator loads catalog key
--     'ide_simple_rules', seeded NOWHERE (0 hits in migrations/). The ~800
--     pairs live in app/services/intramural/ide_contrato_rules.py but the v1
--     catalog scope (all 898? subset?) + tree polarity (NOT wrapper unevidenced
--     for intramural) need a product decision. Q: seed the full 898-pair list
--     as catalog 'ide_simple_rules'? tree = NOT[ide_simple_check]? dedup rule
--     for duplicate (codigo, entidad) pairs?
--   - pym_rutas_dx: PymRutasDxEvaluator.pre_scan_sheet is NEVER called by the
--     engine (0 refs outside the evaluator); empty cache → evaluate returns
--     True (skip) for every factura → a seeded rule would be DEAD on arrival.
--     Q: who calls pre_scan_sheet in the engine path (RuleBasedDetector?
--     engine?) or should the evaluator drop the pre-scan requirement? plus
--     tree polarity (NOT wrapper unevidenced).
--   - duplicado_id_codigo_02_lab: legacy requires tipo=02 AND laboratorio=Si
--     (duplicado_id_codigo.py), but group params support a SINGLE filter_field
--     (group_evaluator.py, engine.py) — seed 08 (filter 02 only) would flag
--     Lab=No groups the legacy explicitly excludes, contradicting the rule's
--     own name. Q: extend group params to dual-filter/exclusions, or split the
--     rule, or accept over-flagging?
--
-- Catalogs: NONE written here. The F15 tree's 12 cat_in keys are all seeded by
-- 011/012/013 (facturadores_urgencias, codigos_exceptuados_responsable_urgencias,
-- codigos_exceptuados, centro_costo_pyp, centro_costo_quirofano,
-- centro_costo_hospitalizacion, centros_costo_pyp_intramural,
-- centros_costo_laboratorio_validos, codigos_tipo_procedimiento_laboratorio,
-- codigos_excluidos_vacunacion, codigos_tipo_procedimiento_ambulatorio,
-- codigos_exceptuados_ambulatorio — verified).
--
-- Fidelity notes (live-code shape wins, same policy as 012/014):
--   - REGLA6 carries the evaluator/F15 lab guard NOT(tipo in TIPO_LAB AND
--     lab=Si); the legacy detector comment lacks it — evaluator +
--     test_intramural_engine_f4 are the tested contract, tree mirrors them.
--   - revision cascade uses the constants (02→2, 03/04→13, general→1);
--     stale prose saying ">12" (evaluator docstring, legacy docstring) loses
--     to CANTIDAD_MAX_03_04=13.
--   - Composite valor_esperado normalized to SQL NULL (010/011/012/013/014 +
--     prod convention; engine-equivalent).
--   - descripcion / prioridad / severidad values are verbatim from the
--     seed/migracion-engine/05-09 files (the only regla-level values in repo
--     for these names).
--
-- Version drift: identity is (nombre, version); this migration authors a single
-- active v1 per rule and never mass-retires sibling versions (lifecycle belongs
-- to the rule CRUD), same policy as 013/014.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema guards (same as 010/011/012/013/014): widen condiciones.operador,
-- normalize condiciones.valor_esperado to jsonb. Guarded; rerun-safe, additive.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'condiciones' AND column_name = 'operador'
          AND character_maximum_length IS DISTINCT FROM 50
    ) THEN
        ALTER TABLE condiciones ALTER COLUMN operador TYPE varchar(50);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'condiciones' AND column_name = 'valor_esperado'
          AND udt_name IS DISTINCT FROM 'jsonb'
    ) THEN
        ALTER TABLE condiciones ALTER COLUMN valor_esperado TYPE jsonb
            USING valor_esperado::jsonb;
    END IF;
END $$;


-- ===========================================================================
-- INTRAMURAL (4)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. bacteriologas_cronograma (src seed/migracion-engine/09 verbatim:
--    1 cond cronograma_check on invoice.codigo_profesional)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'bacteriologas_cronograma', 'Bacterióloga debe estar en cronograma del día — Intramural tipo 02/05 con Laboratorio=Si', 'intramural', 'active', 1, 60, 'error', true, '[]'::jsonb
)
ON CONFLICT (nombre, version) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros;

DO $$
DECLARE
    _regla_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'bacteriologas_cronograma' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'cronograma_check', 'invoice.codigo_profesional', NULL, 0);
END $$;

-- ---------------------------------------------------------------------------
-- 2. centro_costo_intramural_valido (src seed/migracion-engine/15 verbatim:
--    OR tree replacing the deprecated centro_costo_intramural evaluator.
--    100 conds = OR root + 18 AND branches + nested composites.)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'centro_costo_intramural_valido', 'Centro de costo no valido en Intramural', 'intramural', 'active', 1, 25, 'error', true, NULL
)
ON CONFLICT (nombre, version) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros;

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

-- ---------------------------------------------------------------------------
-- 3. duplicado_id_codigo_05 (src seed/migracion-engine/07 verbatim:
--    group_by (identificacion, codigo, codigo_dx_principal) filter
--    codigo_tipo_procedimiento='05', single gte count>=2)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, parametros, severidad, activo)
VALUES (
    'duplicado_id_codigo_05', 'Duplicados ID+Código para tipo=05 — grupos de (identificacion, codigo, dx_principal) con count >= 2', 'intramural', 'active', 1, 50,
    '[{"group_by": ["identificacion", "codigo", "codigo_dx_principal"], "filter_field": "codigo_tipo_procedimiento", "filter_value": "05", "aggregations": [{"function": "group_size", "target": "count"}, {"function": "collect_group_keys", "field": "numero_factura", "target": "facturas"}]}]'::jsonb,
    'warning', true
)
ON CONFLICT (nombre, version) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros;

DO $$
DECLARE
    _regla_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'duplicado_id_codigo_05' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'gte', 'invoice.count', '2', 0);
END $$;

-- ---------------------------------------------------------------------------
-- 4. revision_cantidad_intramural (src seed/migracion-engine/06 verbatim:
--    1 cond revision_cantidad_intramural on invoice.cantidad; cascade
--    02+Lab=No→>2, 03/04→>13, general→>1 + specific 901101:3)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'revision_cantidad_intramural', 'Cantidad fuera de rango en Intramural — requiere revision manual', 'intramural', 'active', 1, 25, 'warning', true
)
ON CONFLICT (nombre, version) DO UPDATE SET
    descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros;

DO $$
DECLARE
    _regla_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'revision_cantidad_intramural' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'revision_cantidad_intramural', 'invoice.cantidad', NULL, 0);
END $$;

-- ---------------------------------------------------------------------------
-- Lineage: seeded v1 rows are their own base (same as 009/011/012/013/014).
-- ---------------------------------------------------------------------------
UPDATE reglas SET rule_base_id = id
WHERE nombre IN ('bacteriologas_cronograma', 'centro_costo_intramural_valido',
                 'duplicado_id_codigo_05', 'revision_cantidad_intramural')
  AND version = 1
  AND rule_base_id IS NULL;
