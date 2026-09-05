-- =============================================================================
-- 010_seed_hospitalizacion_engine_rules.sql
--
-- Seeds the hospitalización engine rules that app/services/hospitalizacion/
-- detect_all.py intends to evaluate but that were absent from the DB, causing
-- silent "Rule not found" gaps. Preserves the tested group-rule semantics from
-- tests/engine/test_hospitalizacion_codes_rules.py and migrates the remaining
-- legacy hospitalización detectors (cantidades, cantidades SOAT, profesional).
--
-- Rules seeded (all dominio='hospitalizacion', estado='active', activo=true):
--   - hosp_codigos_oblig_mayor24h   (group rule)
--   - hosp_codigos_oblig_menor24h   (group rule)
--   - hosp_codigos_prohibidos       (group rule, incl. SOAT variant)
--   - cantidades_hospitalizacion    (row rule, evaluador hospitalizacion_cantidad_check)
--   - cantidades_soat_hospitalizacion (row rule, evaluador hospitalizacion_cantidad_check)
--   - profesional_hospitalizacion_valido (row rule, cat_in profesionales_urgencias)
--   - ide_contrato_hospitalizacion_valido (row rule, reusa el árbol de
--     ide_contrato_urgencias_valido rule 40)
--
-- Reuses existing rules that already cover behavior (NOT duplicated here):
--   - centro_costo_hospitalizacion_valido (rule 60)
--   - cups_equivalentes_hospitalizacion   (rule 61)
--   - copago_entidad_valido               (rule 13)
--   - cups_sin_contrato                   (rule 36)
--   - ide_contrato_urgencias_valido       (rule 40) — orchestrator reuses it
--     for the hospitalización ide_contrato group.
--
-- Idempotent: each rule is upserted by (nombre, version = 1) and its condition
-- tree is replaced, so re-running is safe.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema: widen condiciones.operador to fit longer evaluator operators
-- (e.g. hospitalizacion_cantidad_check). The registry already ships operators
-- longer than the previous varchar(20) limit.
-- Hardened Slice 1: guarded by information_schema; rerun-safe, additive only.
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

-- ---------------------------------------------------------------------------
-- Schema: normalize condiciones.valor_esperado to jsonb. The model declares it
-- as JSONB and the engine relies on native deserialization of array/string
-- values (e.g. set_intersects, in). Some environments (test DB) drifted to
-- text; casting keeps values semantically identical.
-- ---------------------------------------------------------------------------
-- Hardened Slice 1: guarded by information_schema; rerun-safe.
-- ---------------------------------------------------------------------------
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
-- Support: ensure the profesionales_urgencias catalog exists (shared with rule
-- 26 professional_urgencias_valido). Only inserts when missing.
-- ---------------------------------------------------------------------------
INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias',
       '["03568", "01235", "01960", "03493", "03822", "01293", "02249", "03799", "03222", "03384", "03154", "01289", "03628", "03893", "03710", "01868", "03742", "03857", "03365", "03730", "02217", "03374", "03255"]'::jsonb,
       'urgencias', 'Codigos de profesionales validos', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias');

-- ===========================================================================
-- 1. hosp_codigos_oblig_mayor24h
-- Group rule: estancia > 24h AND missing obligatory codes.
--   OBLIG_MAYOR_24 = ["129B02", "890601H", "890601"]
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'hosp_codigos_oblig_mayor24h',
    'Estancia > 24h sin los códigos obligatorios de hospitalización (129B02, 890601H, 890601)',
    'hospitalizacion', 'active', 1, 5, 'error', true,
    '[{"group_by": "numero_factura", "filter_field": "tipo_factura_descripcion", "filter_value": "Hospitalización", "aggregations": [{"function": "compute_horas", "field1": "fec_factura", "field2": "fecha_cierre", "target": "estancia_horas"}, {"function": "collect_set", "field": "codigo", "target": "collect_set_codigo"}]}]'::jsonb
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'hosp_codigos_oblig_mayor24h' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'gt', 'invoice.estancia_horas', '24', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'set_contains_all', 'invoice.collect_set_codigo', '["129B02", "890601H", "890601"]', 0);
END $$;

-- ===========================================================================
-- 2. hosp_codigos_oblig_menor24h
-- Group rule: estancia <= 24h AND missing obligatory codes.
--   OBLIG_MENOR_24 = ["890601H", "129B02"]
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'hosp_codigos_oblig_menor24h',
    'Estancia <= 24h sin los códigos obligatorios de hospitalización (890601H, 129B02)',
    'hospitalizacion', 'active', 1, 6, 'error', true,
    '[{"group_by": "numero_factura", "filter_field": "tipo_factura_descripcion", "filter_value": "Hospitalización", "aggregations": [{"function": "compute_horas", "field1": "fec_factura", "field2": "fecha_cierre", "target": "estancia_horas"}, {"function": "collect_set", "field": "codigo", "target": "collect_set_codigo"}]}]'::jsonb
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'hosp_codigos_oblig_menor24h' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'lte', 'invoice.estancia_horas', '24', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'set_contains_all', 'invoice.collect_set_codigo', '["890601H", "129B02"]', 0);
END $$;

-- ===========================================================================
-- 3. hosp_codigos_prohibidos
-- Group rule: prohibited codes present.
--   PROHIBIDOS  = ["05DSB01", "5DSB01", "890701"]
--   SOAT_PROH   = ["39145", "38915"]  (only when tarifario = SOAT)
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'hosp_codigos_prohibidos',
    'Hospitalización con códigos prohibidos (05DSB01, 5DSB01, 890701; SOAT: 39145, 38915)',
    'hospitalizacion', 'active', 1, 7, 'error', true,
    '[{"group_by": "numero_factura", "filter_field": "tipo_factura_descripcion", "filter_value": "Hospitalización", "aggregations": [{"function": "collect_set", "field": "codigo", "target": "collect_set_codigo"}, {"function": "collect_set", "field": "tarifario", "target": "collect_set_tarifario"}]}]'::jsonb
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
    rid integer;
    root_id integer;
    soat_and_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'hosp_codigos_prohibidos' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'OR', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'set_intersects', 'invoice.collect_set_codigo', '["05DSB01", "5DSB01", "890701"]', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'AND', NULL, NULL, 1) RETURNING id INTO soat_and_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, soat_and_id, 'atomic', 'set_intersects', 'invoice.collect_set_tarifario', '["SOAT"]', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, soat_and_id, 'atomic', 'set_intersects', 'invoice.collect_set_codigo', '["39145", "38915"]', 1);
END $$;

-- ===========================================================================
-- 4. cantidades_hospitalizacion
-- Row rule: legacy detect_cantidades_hospitalizacion (non-SOAT rows).
-- Evaluador hospitalizacion_cantidad_check implementa la lógica legacy.
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'cantidades_hospitalizacion',
    'Cantidades incorrectas en Hospitalización (no SOAT)',
    'hospitalizacion', 'active', 1, 20, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'cantidades_hospitalizacion' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 0) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'eq', 'invoice.tarifario', '"SOAT"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'hospitalizacion_cantidad_check', 'invoice.cantidad', NULL, 1);
END $$;

-- ===========================================================================
-- 5. cantidades_soat_hospitalizacion
-- Row rule: legacy detect_cantidades_soat_hospitalizacion (SOAT rows only).
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'cantidades_soat_hospitalizacion',
    'Cantidades incorrectas en Hospitalización SOAT',
    'hospitalizacion', 'active', 1, 20, 'error', true, NULL
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
    rid integer;
    root_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'cantidades_soat_hospitalizacion' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tarifario', '"SOAT"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'hospitalizacion_cantidad_check', 'invoice.cantidad', NULL, 1);
END $$;

-- ===========================================================================
-- 6. profesional_hospitalizacion_valido
-- Row rule: legacy detect_profesionales_urgencias(tipos_validos={"Hospitalización"}).
-- El profesional debe existir en el catálogo profesionales_urgencias.
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'profesional_hospitalizacion_valido',
    'Profesional no válido en Hospitalización (debe estar en el listado de profesionales)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hospitalizacion_valido' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias"', 0);
END $$;

-- ===========================================================================
-- 7. ide_contrato_hospitalizacion_valido
-- Row rule: reuses the entity -> IDE contrato mappings already seeded for
-- ide_contrato_urgencias_valido (rule 40). Clones rule 40's condition tree so
-- hospitalización rows are validated against the same entity->IDE mapping.
-- If rule 40 is absent (fresh DB), the rule is created with no conditions and
-- simply evaluates to [] until the source rule is seeded.
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'ide_contrato_hospitalizacion_valido',
    'IDE Contrato no válido en Hospitalización (reusa mapeo entidad->IDE de urgencias)',
    'hospitalizacion', 'active', 1, 45, 'error', true, NULL
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
    rid integer;
    src_rid integer;
    id_map jsonb := '{}'::jsonb;
    rec record;
    new_id integer;
    parent_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'ide_contrato_hospitalizacion_valido' AND version = 1;
    SELECT id INTO src_rid FROM reglas WHERE nombre = 'ide_contrato_urgencias_valido' AND version = 1;

    DELETE FROM condiciones WHERE regla_id = rid;

    IF src_rid IS NULL THEN
        RAISE NOTICE 'ide_contrato_urgencias_valido no existe; ide_contrato_hospitalizacion_valido queda sin condiciones';
        RETURN;
    END IF;

    FOR rec IN
        SELECT * FROM condiciones WHERE regla_id = src_rid ORDER BY id
    LOOP
        IF rec.padre_id IS NULL THEN
            parent_id := NULL;
        ELSE
            parent_id := (id_map ->> rec.padre_id::text)::int;
        END IF;
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, parent_id, rec.tipo, rec.operador, rec.fuente_datos, rec.valor_esperado, rec.orden)
        RETURNING id INTO new_id;
        id_map := id_map || jsonb_build_object(rec.id::text, new_id);
    END LOOP;
END $$;
