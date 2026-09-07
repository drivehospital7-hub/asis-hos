-- =============================================================================
-- 014_seed_final_unseeded_rules.sql
--
-- Seeds the FINAL 6 engine rules with no seed coverage anywhere in seed/ or
-- seeds/ (verified), ported faithfully from the live dev-active trees in
-- asis_hos (read-only SELECT; prod writes out of scope, Ref #1).
-- Idempotent by-name pattern like 010/011/012/013: each rule is upserted
-- ON CONFLICT (nombre, version = 1) and its condition tree is deleted +
-- rebuilt, so re-running is a no-op. Never hardcodes live row IDs, never uses
-- BEGIN/COMMIT or MAX(id) parenting (011 no-transaction-control rule).
--
-- Rules seeded (6 total, all estado='active', activo=true, v1):
--   Odontologia (1, dominio='odontologia'):
--     1. ide_contrato_odontologia_valido    (111 conds = OR root + 20 AND
--                                              branches; the seeds/phase3/
--                                              insert_ide_contrato_odon.sql
--                                              partial file covers only the top
--                                              8 entities and is NOT used)
--   Transversal (1, dominio='transversal'):
--     2. detect_duplicados_base             (1 cond all_values_match +
--                                              group_by factura params)
--   Urgencias (4, dominio='urgencias'):
--     3. duplicados_farmacia_v2             (1 cond all_values_match +
--                                              group_by factura + FARMACIA
--                                              filter params)
--     4. ide_contrato_reverse_urgencias_valido (21 conds = OR root + 5 AND
--                                              branches; seeds/phase3/
--                                              insert_ide_contrato_reverse.sql
--                                              EXISTS but uses BEGIN/COMMIT +
--                                              MAX(id)-style parenting, so the
--                                              tree is rewritten clean by-name
--                                              instead)
--     5. revision_cantidad_v2               (1 cond gt group.sum_cantidad +
--                                              group_by factura sum params)
--     6. sala_obs_check_set                 (4 conds = AND root +
--                                              set_intersects + NOT[
--                                              set_contains_all] + group_by
--                                              factura collect_set params)
-- Total: 139 condiciones (111 + 1 + 1 + 21 + 1 + 4).
--
-- Catalogs: NONE. cat_in audit over the 6 live trees returns 0 rows (verified
-- read-only); the distinct operadores/fuentes are eq/in/NOT/AND/OR on
-- invoice.* plus group.* evaluator conds (all_values_match, gt,
-- set_intersects, set_contains_all). No catalog keys referenced, none seeded.
--
-- Source deltas / fidelity notes (live-active shape wins, same policy as 012):
--   - ide_contrato_odontologia_valido: 20 AND branches alternate shapes —
--     even orden (0,2,...,18): eq entidad + in codigo[8] + NOT[in ide_contrato];
--     odd orden (1,3,...,19): eq entidad + NOT[in codigo[8]] + NOT[in ide_contrato].
--     Shared codigo list (8): 890203, 990203, 990212, 997002, 997106, 997107,
--     997301, P0000011. Orden values are live-verbatim (contiguous 0-19; the
--     live id gap 382-391 is a deleted range, not a missing branch).
--   - ide_contrato_reverse_urgencias_valido: 5 AND branches, each
--     eq ide_contrato + NOT[codigo check]; branches 970/974 use `in`
--     (3 codes each), branches 986/839/842 use single `eq` (906340).
--   - Group-shape rules keep their live `group.*` fuentes verbatim
--     (group.collect_value_counts / group.sum_cantidad /
--     group.collect_set_codigo), resolved by the GroupEvaluator provider path,
--     plus their live group_by parametros verbatim (group_by factura).
--   - Composite valor_esperado normalized to SQL NULL (010/011/012/013 + prod
--     convention; engine-equivalent).
--   - descripcion values are live-verbatim (incl. 'código' with accent in the
--     reverse rule).
--
-- Version drift: identity is (nombre, version); this migration authors a single
-- active v1 per rule and never mass-retires sibling versions (lifecycle belongs
-- to the rule CRUD), same policy as 013.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema guards (same as 010/011/012/013): widen condiciones.operador, normalize
-- condiciones.valor_esperado to jsonb. Guarded; rerun-safe, additive only.
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
-- ODONTOLOGÍA (1)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- ide_contrato_odontologia_valido (odontologia, 111 conds, live-faithful)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'ide_contrato_odontologia_valido', 'IDE Contrato debe corresponder a la entidad y tipo de procedimiento (PyP vs No PyP) en Odontologia.', 'odontologia', 'active', 1, 40, 'error', true, NULL
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
    od_0 INT;
    od_1 INT;
    od_2 INT;
    od_3 INT;
    od_4 INT;
    od_5 INT;
    od_6 INT;
    od_7 INT;
    od_8 INT;
    od_9 INT;
    od_10 INT;
    od_11 INT;
    od_12 INT;
    od_13 INT;
    od_14 INT;
    od_15 INT;
    od_16 INT;
    od_17 INT;
    od_18 INT;
    od_19 INT;
    od_20 INT;
    od_21 INT;
    od_22 INT;
    od_23 INT;
    od_24 INT;
    od_25 INT;
    od_26 INT;
    od_27 INT;
    od_28 INT;
    od_29 INT;
    od_30 INT;
    od_31 INT;
    od_32 INT;
    od_33 INT;
    od_34 INT;
    od_35 INT;
    od_36 INT;
    od_37 INT;
    od_38 INT;
    od_39 INT;
    od_40 INT;
    od_41 INT;
    od_42 INT;
    od_43 INT;
    od_44 INT;
    od_45 INT;
    od_46 INT;
    od_47 INT;
    od_48 INT;
    od_49 INT;
    od_50 INT;
    od_51 INT;
    od_52 INT;
    od_53 INT;
    od_54 INT;
    od_55 INT;
    od_56 INT;
    od_57 INT;
    od_58 INT;
    od_59 INT;
    od_60 INT;
    od_61 INT;
    od_62 INT;
    od_63 INT;
    od_64 INT;
    od_65 INT;
    od_66 INT;
    od_67 INT;
    od_68 INT;
    od_69 INT;
    od_70 INT;
    od_71 INT;
    od_72 INT;
    od_73 INT;
    od_74 INT;
    od_75 INT;
    od_76 INT;
    od_77 INT;
    od_78 INT;
    od_79 INT;
    od_80 INT;
    od_81 INT;
    od_82 INT;
    od_83 INT;
    od_84 INT;
    od_85 INT;
    od_86 INT;
    od_87 INT;
    od_88 INT;
    od_89 INT;
    od_90 INT;
    od_91 INT;
    od_92 INT;
    od_93 INT;
    od_94 INT;
    od_95 INT;
    od_96 INT;
    od_97 INT;
    od_98 INT;
    od_99 INT;
    od_100 INT;
    od_101 INT;
    od_102 INT;
    od_103 INT;
    od_104 INT;
    od_105 INT;
    od_106 INT;
    od_107 INT;
    od_108 INT;
    od_109 INT;
    od_110 INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'ide_contrato_odontologia_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0) RETURNING id INTO od_0;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO od_1;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_1, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"', 0) RETURNING id INTO od_2;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_1, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_3;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_1, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_4;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_4, 'atomic', 'in', 'invoice.ide_contrato', '["970", "974"]', 0) RETURNING id INTO od_5;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 1) RETURNING id INTO od_6;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_6, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"', 0) RETURNING id INTO od_7;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_6, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_8;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_8, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_9;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_6, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_10;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_10, 'atomic', 'in', 'invoice.ide_contrato', '["969", "973"]', 0) RETURNING id INTO od_11;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 2) RETURNING id INTO od_12;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_12, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC18"', 0) RETURNING id INTO od_13;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_12, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_14;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_12, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_15;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_15, 'atomic', 'in', 'invoice.ide_contrato', '["975"]', 0) RETURNING id INTO od_16;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 3) RETURNING id INTO od_17;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_17, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC18"', 0) RETURNING id INTO od_18;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_17, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_19;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_19, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_20;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_17, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_21;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_21, 'atomic', 'in', 'invoice.ide_contrato', '["968"]', 0) RETURNING id INTO od_22;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 4) RETURNING id INTO od_23;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_23, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS41"', 0) RETURNING id INTO od_24;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_23, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_25;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_23, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_26;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_26, 'atomic', 'in', 'invoice.ide_contrato', '["955", "958"]', 0) RETURNING id INTO od_27;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 5) RETURNING id INTO od_28;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_28, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS41"', 0) RETURNING id INTO od_29;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_28, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_30;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_30, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_31;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_28, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_32;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_32, 'atomic', 'in', 'invoice.ide_contrato', '["956", "959"]', 0) RETURNING id INTO od_33;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 6) RETURNING id INTO od_34;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_34, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSI05"', 0) RETURNING id INTO od_35;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_34, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_36;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_34, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_37;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_37, 'atomic', 'in', 'invoice.ide_contrato', '["977"]', 0) RETURNING id INTO od_38;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 7) RETURNING id INTO od_39;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_39, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSI05"', 0) RETURNING id INTO od_40;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_39, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_41;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_41, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_42;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_39, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_43;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_43, 'atomic', 'in', 'invoice.ide_contrato', '["976", "978"]', 0) RETURNING id INTO od_44;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 8) RETURNING id INTO od_45;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_45, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPS037"', 0) RETURNING id INTO od_46;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_45, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_47;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_45, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_48;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_48, 'atomic', 'in', 'invoice.ide_contrato', '["961"]', 0) RETURNING id INTO od_49;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 9) RETURNING id INTO od_50;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_50, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPS037"', 0) RETURNING id INTO od_51;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_50, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_52;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_52, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_53;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_50, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_54;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_54, 'atomic', 'in', 'invoice.ide_contrato', '["962"]', 0) RETURNING id INTO od_55;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 10) RETURNING id INTO od_56;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_56, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS062"', 0) RETURNING id INTO od_57;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_56, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_58;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_56, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_59;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_59, 'atomic', 'in', 'invoice.ide_contrato', '["922"]', 0) RETURNING id INTO od_60;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 11) RETURNING id INTO od_61;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_61, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS062"', 0) RETURNING id INTO od_62;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_61, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_63;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_63, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_64;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_61, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_65;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_65, 'atomic', 'in', 'invoice.ide_contrato', '["921"]', 0) RETURNING id INTO od_66;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 12) RETURNING id INTO od_67;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_67, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC62"', 0) RETURNING id INTO od_68;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_67, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_69;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_67, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_70;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_70, 'atomic', 'in', 'invoice.ide_contrato', '["863"]', 0) RETURNING id INTO od_71;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 13) RETURNING id INTO od_72;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_72, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESSC62"', 0) RETURNING id INTO od_73;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_72, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_74;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_74, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_75;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_72, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_76;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_76, 'atomic', 'in', 'invoice.ide_contrato', '["862"]', 0) RETURNING id INTO od_77;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 14) RETURNING id INTO od_78;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_78, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS005"', 0) RETURNING id INTO od_79;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_78, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_80;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_78, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_81;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_81, 'atomic', 'in', 'invoice.ide_contrato', '["933"]', 0) RETURNING id INTO od_82;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 15) RETURNING id INTO od_83;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_83, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSS005"', 0) RETURNING id INTO od_84;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_83, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_85;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_85, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_86;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_83, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_87;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_87, 'atomic', 'in', 'invoice.ide_contrato', '["934"]', 0) RETURNING id INTO od_88;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 16) RETURNING id INTO od_89;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_89, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSC005"', 0) RETURNING id INTO od_90;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_89, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_91;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_89, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_92;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_92, 'atomic', 'in', 'invoice.ide_contrato', '["932"]', 0) RETURNING id INTO od_93;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 17) RETURNING id INTO od_94;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_94, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"EPSC005"', 0) RETURNING id INTO od_95;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_94, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_96;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_96, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_97;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_94, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_98;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_98, 'atomic', 'in', 'invoice.ide_contrato', '["931"]', 0) RETURNING id INTO od_99;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 18) RETURNING id INTO od_100;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_100, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"86000"', 0) RETURNING id INTO od_101;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_100, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 1) RETURNING id INTO od_102;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_100, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_103;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_103, 'atomic', 'in', 'invoice.ide_contrato', '["920"]', 0) RETURNING id INTO od_104;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_0, 'composite', 'AND', NULL, NULL, 19) RETURNING id INTO od_105;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_105, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"86000"', 0) RETURNING id INTO od_106;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_105, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO od_107;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_107, 'atomic', 'in', 'invoice.codigo', '["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]', 0) RETURNING id INTO od_108;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_105, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO od_109;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, od_109, 'atomic', 'in', 'invoice.ide_contrato', '["919"]', 0) RETURNING id INTO od_110;
END $$;

-- ===========================================================================
-- TRANSVERSAL (1)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- detect_duplicados_base (transversal, 1 cond, live-faithful)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'detect_duplicados_base', 'Detecta grupos de farmacia donde todos los pares (codigo, cantidad) aparecen al menos 2 veces', 'transversal', 'active', 1, 35, 'warning', true, '[{"group_by": "factura", "aggregations": [{"fields": ["codigo", "cantidad"], "function": "collect_value_counts"}]}]'::jsonb
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
    ddb_0 INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'detect_duplicados_base' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'all_values_match', 'group.collect_value_counts', '2', 0) RETURNING id INTO ddb_0;
END $$;

-- ===========================================================================
-- URGENCIAS (4)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- duplicados_farmacia_v2 (urgencias, 1 cond, live-faithful)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'duplicados_farmacia_v2', 'Detecta grupos de farmacia donde todos los pares estan duplicados (filtrado por tipo=FARMACIA)', 'urgencias', 'active', 1, 35, 'warning', true, '[{"group_by": "factura", "aggregations": [{"fields": ["codigo", "cantidad"], "function": "collect_value_counts"}], "filter_field": "tipo_factura_descripcion", "filter_value": "FARMACIA"}]'::jsonb
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
    df2_0 INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'duplicados_farmacia_v2' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'all_values_match', 'group.collect_value_counts', '2', 0) RETURNING id INTO df2_0;
END $$;

-- ---------------------------------------------------------------------------
-- ide_contrato_reverse_urgencias_valido (urgencias, 21 conds, live-faithful)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'ide_contrato_reverse_urgencias_valido', 'Valida que el código CUPS corresponda al IDE Contrato (reglas REVERSE). Cubre reglas simples sin pre-scan.', 'urgencias', 'active', 1, 46, 'error', true, NULL
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
    rv_0 INT;
    rv_1 INT;
    rv_2 INT;
    rv_3 INT;
    rv_4 INT;
    rv_5 INT;
    rv_6 INT;
    rv_7 INT;
    rv_8 INT;
    rv_9 INT;
    rv_10 INT;
    rv_11 INT;
    rv_12 INT;
    rv_13 INT;
    rv_14 INT;
    rv_15 INT;
    rv_16 INT;
    rv_17 INT;
    rv_18 INT;
    rv_19 INT;
    rv_20 INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'ide_contrato_reverse_urgencias_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0) RETURNING id INTO rv_0;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_0, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO rv_1;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_1, 'atomic', 'eq', 'invoice.ide_contrato', '"986"', 0) RETURNING id INTO rv_2;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_1, 'composite', 'NOT', 'invoice.codigo', NULL, 1) RETURNING id INTO rv_3;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_3, 'atomic', 'eq', 'invoice.codigo', '"906340"', 0) RETURNING id INTO rv_4;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_0, 'composite', 'AND', NULL, NULL, 1) RETURNING id INTO rv_5;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_5, 'atomic', 'eq', 'invoice.ide_contrato', '"839"', 0) RETURNING id INTO rv_6;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_5, 'composite', 'NOT', 'invoice.codigo', NULL, 1) RETURNING id INTO rv_7;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_7, 'atomic', 'eq', 'invoice.codigo', '"906340"', 0) RETURNING id INTO rv_8;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_0, 'composite', 'AND', NULL, NULL, 2) RETURNING id INTO rv_9;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_9, 'atomic', 'eq', 'invoice.ide_contrato', '"842"', 0) RETURNING id INTO rv_10;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_9, 'composite', 'NOT', 'invoice.codigo', NULL, 1) RETURNING id INTO rv_11;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_11, 'atomic', 'eq', 'invoice.codigo', '"906340"', 0) RETURNING id INTO rv_12;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_0, 'composite', 'AND', NULL, NULL, 3) RETURNING id INTO rv_13;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_13, 'atomic', 'eq', 'invoice.ide_contrato', '"970"', 0) RETURNING id INTO rv_14;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_13, 'composite', 'NOT', 'invoice.codigo', NULL, 1) RETURNING id INTO rv_15;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_15, 'atomic', 'in', 'invoice.codigo', '["735301", "861801", "890205"]', 0) RETURNING id INTO rv_16;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_0, 'composite', 'AND', NULL, NULL, 4) RETURNING id INTO rv_17;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_17, 'atomic', 'eq', 'invoice.ide_contrato', '"974"', 0) RETURNING id INTO rv_18;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_17, 'composite', 'NOT', 'invoice.codigo', NULL, 1) RETURNING id INTO rv_19;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, rv_19, 'atomic', 'in', 'invoice.codigo', '["735301", "861801", "890405"]', 0) RETURNING id INTO rv_20;
END $$;

-- ---------------------------------------------------------------------------
-- revision_cantidad_v2 (urgencias, 1 cond, live-faithful)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'revision_cantidad_v2', 'Revision de cantidad en facturas de farmacia agrupando por factura', 'urgencias', 'active', 1, 35, 'warning', true, '[{"group_by": "factura", "aggregations": [{"field": "cantidad", "function": "sum"}], "filter_field": "tipo_factura_descripcion", "filter_value": "FARMACIA"}]'::jsonb
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
    rc2_0 INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'revision_cantidad_v2' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'gt', 'group.sum_cantidad', '1', 0) RETURNING id INTO rc2_0;
END $$;

-- ---------------------------------------------------------------------------
-- sala_obs_check_set (urgencias, 4 conds, live-faithful)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'sala_obs_check_set', 'Verifica que si hay codigos de sala de observacion, esten los obligatorios 890701 y 890601', 'urgencias', 'active', 1, 30, 'error', true, '[{"group_by": "factura", "aggregations": [{"field": "codigo", "function": "collect_set"}]}]'::jsonb
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
    so_0 INT;
    so_1 INT;
    so_2 INT;
    so_3 INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'sala_obs_check_set' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO so_0;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, so_0, 'atomic', 'set_intersects', 'group.collect_set_codigo', '["5DSB01", "05DSB01", "129B02", "38114", "38915"]', 0) RETURNING id INTO so_1;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, so_0, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO so_2;
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, so_2, 'atomic', 'set_contains_all', 'group.collect_set_codigo', '["890701", "890601"]', 0) RETURNING id INTO so_3;
END $$;

-- ---------------------------------------------------------------------------
-- Lineage: seeded v1 rows are their own base (same as 009/011/012/013).
-- ---------------------------------------------------------------------------
UPDATE reglas SET rule_base_id = id
WHERE nombre IN ('ide_contrato_odontologia_valido', 'detect_duplicados_base',
                 'duplicados_farmacia_v2', 'ide_contrato_reverse_urgencias_valido',
                 'revision_cantidad_v2', 'sala_obs_check_set')
  AND version = 1
  AND rule_base_id IS NULL;
