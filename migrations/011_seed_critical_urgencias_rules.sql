-- =============================================================================
-- 011_seed_critical_urgencias_rules.sql
--
-- Seeds the CRITICAL urgencias engine rules + catalogs by (nombre, version),
-- never by hardcoded live IDs. Idempotent DELETE+INSERT pattern like 010:
-- each rule is upserted ON CONFLICT (nombre, version = 1) and its condition
-- tree is deleted + rebuilt, so re-running is a no-op.
--
-- Rules seeded (all dominio='urgencias', estado='active', activo=true, v1):
--   1. cups_equivalentes            (13 conds, src seed/phase1/insert_cups_equivalentes.sql)
--   2. mal_capitado                 (9 conds,  src seed/phase1/insert_mal_capitado.sql)
--   3. cantidades_urgencias         (3 conds,  src seed/phase1/insert_cantidades_urgencias.sql)
--   4. cantidades_soat_urgencias    (5 conds,  src seed/phase1/insert_cantidades_soat_urgencias.sql)
--   5. copago_entidad_valido        (5 conds,  src seeds/003_copago_entidad_seed.sql,
--                                    MAX(id)-parenting rewritten as a DO block)
--   6. ide_contrato_urgencias_valido (123 conds = OR root + 26 branches,
--                                    src seeds/phase3/insert_ide_contrato_urg.sql,
--                                    MAX(id)-parenting rewritten as data loops)
--   7. centro_costo_urgencias_valido (2 conds, src seed/phase4/insert_centro_costo_invalido_urg.sql)
--      The (nombre, v1) upsert flips estado='active', activo=true over the
--      8 retired dev versions, yielding exactly ONE active version. Sibling
--      versions are NOT mass-retired here: version lifecycle belongs to the
--      rule CRUD, and clobbering a legitimately newer active version would
--      be destructive. UTF-8 literals used (seed \uXXXX escapes decode to
--      the same jsonb values; catalog spelling from 13_catalogos used).
--   8. revision_entidad_86          (1 cond,  src seed/phase1/insert_revision_entidad_86.sql;
--                                    listed source, outside the critical set,
--                                    seeded because the engine path needs it)
--
-- Catalogs seeded (additive WHERE NOT EXISTS, never overwritten):
--   - centros_costo_validos_urgencias (8 centers, src seed/migracion-engine/13_catalogos_centro_costo.sql)
--   - profesionales_urgencias         (23 codes, src 010 — snapshot reused verbatim)
--   - facturadores_urgencias          (4 names, src 13_catalogos_centro_costo.sql)
--   - codigos_exceptuados_responsable_urgencias (["735301"], src 13_catalogos_centro_costo.sql)
--
-- cat_in audit: NONE of the trees seeded here uses operador='cat_in' (inline
-- sets only, faithful to the phase1/phase3/phase4/copago sources). The catalogs
-- serve sibling rules: profesionales_urgencias -> profesional_urgencias_valido
-- (rule 26) and profesional_hospitalizacion_valido (010);
-- centros_costo_validos_urgencias -> centro_costo_*_valido trees (14);
-- facturadores_urgencias + codigos_exceptuados_responsable_urgencias ->
-- REGLA_RESPONSABLE_URGENCIAS in centro_costo_intramural_valido (15).
--
-- Excluded (noted, not seeded):
--   - ide_contrato_reverse_urgencias_valido (no seed exists anywhere)
--   - centro_costo equipos_basicos / odontologia phase4 files (other domains)
--   - retired-version history (active v1 only)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema guards (same as 010): widen condiciones.operador, normalize
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

-- ---------------------------------------------------------------------------
-- Catalogs (additive only)
-- ---------------------------------------------------------------------------
INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'centros_costo_validos_urgencias',
       '["URGENCIAS", "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", "APOYO DIAGNOSTICO-LABORATOR CLINICO", "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN", "HOSPITALIZACIÓN - ESTANCIA GENERAL", "APOYO DIAGNOSTICO-IMAGENOLOGIA", "TRASLADOS", "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"]'::jsonb,
       'urgencias', 'Centros de costo válidos para Urgencias (CENTROS_COSTO_VALIDOS_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_validos_urgencias');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias',
       '["03568", "01235", "01960", "03493", "03822", "01293", "02249", "03799", "03222", "03384", "03154", "01289", "03628", "03893", "03710", "01868", "03742", "03857", "03365", "03730", "02217", "03374", "03255"]'::jsonb,
       'urgencias', 'Codigos de profesionales validos', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'facturadores_urgencias',
       '["ARIAS CULCHA ANGIE CAROLINA", "ESPAÑA DIAZ LORENY ALEJANDRA", "MEZA FERNANDEZ CARLOS OMAR", "PAEZ YULIETH DANIELA"]'::jsonb,
       'urgencias', 'Facturadores de Urgencias (FACTURADORES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'facturadores_urgencias');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_exceptuados_responsable_urgencias',
       '["735301"]'::jsonb,
       'intramural', 'Códigos exceptuados de REGLA_RESPONSABLE_URGENCIAS (CODIGOS_EXCEPTUADOS_RESPONSABLE_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_exceptuados_responsable_urgencias');

-- ===========================================================================
-- 1. cups_equivalentes (src seed/phase1/insert_cups_equivalentes.sql)
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'cups_equivalentes', 'Código CUPS con equivalente conocido detectado', 'urgencias', 'active', 1, 5, 'error', true, NULL
, 'Cups-Equivalentes', NULL, NULL, NULL)
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros,
    grupo_error = EXCLUDED.grupo_error,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
    _b3_id INT;
    _b3_not_id INT;
    _b4_id INT;
    _b5_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cups_equivalentes' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.codigo', '"890201"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.codigo', '"129B01"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 2)
    RETURNING id INTO _b3_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b3_id, 'atomic', 'eq', 'invoice.codigo', '"890205"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b3_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _b3_not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b3_not_id, 'atomic', 'in', 'invoice.codigo_entidad_cobrar', '["ESS118", "ESSC18"]', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 3)
    RETURNING id INTO _b4_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b4_id, 'atomic', 'eq', 'invoice.codigo', '"939402"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b4_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 4)
    RETURNING id INTO _b5_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b5_id, 'atomic', 'eq', 'invoice.codigo', '"12333"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _b5_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 1);
END $$;

-- ===========================================================================
-- 2. mal_capitado (src seed/phase1/insert_mal_capitado.sql)
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'mal_capitado', 'Factura mal capitada detectada (código FEV/CAP entidad)', 'urgencias', 'active', 1, 30, 'error', true, NULL
, 'MAL CAPITADO', 'codigo,procedimiento', 'ide_contrato,ide_contrato_actual', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros,
    grupo_error = EXCLUDED.grupo_error,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
    _g1_id INT;
    _g1_not_id INT;
    _g2_id INT;
    _g2_not_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'mal_capitado' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _g1_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g1_id, 'atomic', 'in', 'invoice.codigo', '["G03XB01", "A02BB01"]', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g1_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _g1_not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g1_not_id, 'atomic', 'contains', 'invoice.numero_factura', '"FEV"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'AND', NULL, NULL, 1)
    RETURNING id INTO _g2_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g2_id, 'atomic', 'contains', 'invoice.numero_factura', '"CAP"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g2_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _g2_not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _g2_not_id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"ESS118"', 0);
END $$;

-- ===========================================================================
-- 3. cantidades_urgencias (src seed/phase1/insert_cantidades_urgencias.sql)
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'cantidades_urgencias', 'Cantidad excedida (>1) para código de urgencias restringido', 'urgencias', 'active', 1, 20, 'error', true, NULL
, 'Cantidades', 'codigo,procedimiento', 'cantidad', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros,
    grupo_error = EXCLUDED.grupo_error,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cantidades_urgencias' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.codigo',
            '["05DSB01", "5DSB01", "890601", "890701", "129B02", "12333"]', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gt', 'invoice.cantidad', '1', 1);
END $$;

-- ===========================================================================
-- 4. cantidades_soat_urgencias (src seed/phase1/insert_cantidades_soat_urgencias.sql)
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'cantidades_soat_urgencias', 'Cantidad SOAT no es 1 para código restringido en urgencias', 'urgencias', 'active', 1, 25, 'error', true, NULL
, 'Cantidades SOAT', 'codigo,procedimiento', 'cantidad', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros,
    grupo_error = EXCLUDED.grupo_error,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
    _not_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cantidades_soat_urgencias' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tarifario', '"SOAT"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.codigo',
            '["39145", "38114", "38915", "39131"]', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'NOT', NULL, NULL, 2)
    RETURNING id INTO _not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _not_id, 'atomic', 'eq', 'invoice.cantidad', '1', 0);
END $$;

-- ===========================================================================
-- 5. copago_entidad_valido (src seeds/003_copago_entidad_seed.sql)
-- Logic: AND(NOT(IN(cod_entidad, ["1","0001"])), NOT(EQ(vlr_copago, 0)))
-- The original MAX(id)-parenting is rewritten as a DO block so reruns and
-- concurrent trees cannot mis-parent nodes.
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'copago_entidad_valido', 'Detecta filas donde Cod Entidad no es default y Vlr. Copago no es 0.', 'urgencias', 'active', 1, 25, 'error', true, NULL
, 'Copago vs Entidad', 'codigo,procedimiento', 'Ent: {entidad_cobrar}, Copago: {vlr_copago}', 'Vlr. Copago debe ser 0 cuando entidad no es default')
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros,
    grupo_error = EXCLUDED.grupo_error,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
    _not1_id INT;
    _not2_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'copago_entidad_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _not1_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _not1_id, 'atomic', 'in', 'invoice.codigo_entidad_cobrar', '["1", "0001"]', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _not2_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _not2_id, 'atomic', 'eq', 'invoice.vlr_copago', '0', 0);
END $$;

-- ===========================================================================
-- 6. ide_contrato_urgencias_valido (src seeds/phase3/insert_ide_contrato_urg.sql)
-- OR root + 26 branches (orden 0-25): 16 simple exact (entidad+codigo->IDE),
-- 2 multiple (IDE set), 8 generic entidad->IDE (7 single + MIN001 set).
-- Data loops replace the original MAX(id)-parenting; tree shape, orden values
-- and fuente_datos ('invoice.ide_contrato' on NOT nodes) match the source.
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'ide_contrato_urgencias_valido', 'Valida IDE Contrato en Urgencias. Cubre reglas simples (codigo+entidad->IDE unico), multiples y genericas de entidad.', 'urgencias', 'active', 1, 45, 'error', true, NULL
, 'IDE Contrato', 'codigo,procedimiento', 'ide_contrato_actual,ide_contrato', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros,
    grupo_error = EXCLUDED.grupo_error,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    rid integer;
    root_id integer;
    branch_id integer;
    not_id integer;
    ord integer := 0;
    simple TEXT[][] := ARRAY[
        ARRAY['EPSI05', '906340', '986'],
        ARRAY['EPSI05', '861801', '977'],
        ARRAY['EPSIC5', '861801', '979'],
        ARRAY['ESS118', '906340', '839'],
        ARRAY['ESS118', '890405', '974'],
        ARRAY['ESS118', '890205', '970'],
        ARRAY['ESSC18', '906340', '842'],
        ARRAY['ESSC18', '861801', '975'],
        ARRAY['EPS037', '906340', '962'],
        ARRAY['EPS037', '861801', '961'],
        ARRAY['EPSS41', '906340', '959'],
        ARRAY['EPSS41', '861801', '958'],
        ARRAY['ESS062', '861801', '922'],
        ARRAY['ESSC62', '861801', '863'],
        ARRAY['86000', '861801', '920'],
        ARRAY['RES004', '861801', '908']
    ];
    multi TEXT[][] := ARRAY[
        ARRAY['ESS118', '735301', '970', '974'],
        ARRAY['ESS118', '861801', '970', '974']
    ];
    generic TEXT[][] := ARRAY[
        ARRAY['86', '911'],
        ARRAY['5177', '917'],
        ARRAY['RES001', '992'],
        ARRAY['AT1306', '867'],
        ARRAY['000124', '874'],
        ARRAY['EPSS005', '934'],
        ARRAY['EPSC005', '931']
    ];
    triple TEXT[];
    pair TEXT[];
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'ide_contrato_urgencias_valido' AND version = 1;
    IF rid IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO root_id;

    FOREACH triple SLICE 1 IN ARRAY simple LOOP
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, root_id, 'composite', 'AND', NULL, NULL, ord)
        RETURNING id INTO branch_id;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, branch_id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', to_jsonb(triple[1]), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, branch_id, 'atomic', 'eq', 'invoice.codigo', to_jsonb(triple[2]), 1);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, branch_id, 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2)
        RETURNING id INTO not_id;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, not_id, 'atomic', 'eq', 'invoice.ide_contrato', to_jsonb(triple[3]), 0);

        ord := ord + 1;
    END LOOP;

    FOREACH triple SLICE 1 IN ARRAY multi LOOP
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, root_id, 'composite', 'AND', NULL, NULL, ord)
        RETURNING id INTO branch_id;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, branch_id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', to_jsonb(triple[1]), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, branch_id, 'atomic', 'eq', 'invoice.codigo', to_jsonb(triple[2]), 1);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, branch_id, 'composite', 'NOT', 'invoice.ide_contrato', NULL, 2)
        RETURNING id INTO not_id;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, not_id, 'atomic', 'in', 'invoice.ide_contrato', to_jsonb(ARRAY[triple[3], triple[4]]), 0);

        ord := ord + 1;
    END LOOP;

    FOREACH pair SLICE 1 IN ARRAY generic LOOP
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, root_id, 'composite', 'AND', NULL, NULL, ord)
        RETURNING id INTO branch_id;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, branch_id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', to_jsonb(pair[1]), 0);

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, branch_id, 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1)
        RETURNING id INTO not_id;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, not_id, 'atomic', 'eq', 'invoice.ide_contrato', to_jsonb(pair[2]), 0);

        ord := ord + 1;
    END LOOP;

    -- MIN001 multiple -> IDE 910 or 918 (orden 25)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'AND', NULL, NULL, ord)
    RETURNING id INTO branch_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, branch_id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', to_jsonb('MIN001'::text), 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, branch_id, 'composite', 'NOT', 'invoice.ide_contrato', NULL, 1)
    RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'in', 'invoice.ide_contrato', to_jsonb(ARRAY['910', '918']), 0);
END $$;

-- ===========================================================================
-- 7. centro_costo_urgencias_valido (src seed/phase4/insert_centro_costo_invalido_urg.sql)
-- NOT(IN(centro_costo, valid_centers)). The phase4 seed inserts an ACTIVE v1,
-- so this is NOT a retired-only seed: the upsert below reactivates v1 even
-- where dev holds retired versions, producing exactly ONE active version.
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'centro_costo_urgencias_valido', 'Centro de costo no válido en Urgencias', 'urgencias', 'active', 1, 25, 'error', true, NULL
, 'Centros de Costo', 'codigo,procedimiento', 'centro_actual,centro_costo', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros,
    grupo_error = EXCLUDED.grupo_error,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'centro_costo_urgencias_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.centro_costo',
        '["URGENCIAS", "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", "APOYO DIAGNOSTICO-LABORATOR CLINICO", "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN", "HOSPITALIZACIÓN - ESTANCIA GENERAL", "APOYO DIAGNOSTICO-IMAGENOLOGIA", "TRASLADOS", "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"]', 0);
END $$;

-- ===========================================================================
-- 8. revision_entidad_86 (src seed/phase1/insert_revision_entidad_86.sql)
-- Listed source outside the critical set; seeded because the engine path
-- (detect_all urgencias) evaluates it. Root-level atomic, no composite root.
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'revision_entidad_86', 'Revisión necesaria para entidad 86', 'urgencias', 'active', 1, 10, 'warning', true, NULL
, 'Revision-Necesaria', NULL, NULL, NULL)
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    prioridad = EXCLUDED.prioridad,
    severidad = EXCLUDED.severidad,
    activo = true,
    parametros = EXCLUDED.parametros,
    grupo_error = EXCLUDED.grupo_error,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    _regla_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'revision_entidad_86' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '"86"', 0);
END $$;

-- ---------------------------------------------------------------------------
-- Lineage: seeded v1 rows are their own base (same as 009).
-- ---------------------------------------------------------------------------
UPDATE reglas SET rule_base_id = id
WHERE nombre IN ('cups_equivalentes', 'ide_contrato_urgencias_valido', 'mal_capitado',
                 'centro_costo_urgencias_valido', 'copago_entidad_valido',
                 'cantidades_urgencias', 'cantidades_soat_urgencias', 'revision_entidad_86')
  AND version = 1
  AND rule_base_id IS NULL;
