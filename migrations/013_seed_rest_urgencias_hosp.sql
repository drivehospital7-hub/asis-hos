-- =============================================================================
-- 013_seed_rest_urgencias_hosp.sql
--
-- Seeds the REMAINING seedable urgencias engine rules + the hospitalización
-- centro-costo rule + their catalogs, by (nombre, version), never by hardcoded
-- live IDs. Idempotent DELETE+INSERT pattern like 010/011/012: each rule is
-- upserted ON CONFLICT (nombre, version = 1) and its condition tree is deleted
-- + rebuilt, so re-running is a no-op.
--
-- Rules seeded (6 total, all estado='active', activo=true, v1):
--   Urgencias (5, dominio='urgencias'):
--     1. duplicados_farmacia                  (3 conds, src seed/final_rules.sql)
--     2. profesional_urgencias_valido         (2 conds, src seed/phase2/insert_profesionales_urg.sql)
--     3. revision_cantidad_urgencias          (1 cond + group_by params,
--                                              src seed/phase6/insert_revision_cantidad.sql)
--     4. sala_observacion_entidad             (1 cond sala_obs_check evaluator,
--                                              dev-active shape; src seed/final_rules.sql
--                                              3-cond tree is stale, see deltas)
--     5. sala_observacion_estancia_prolongada (1 cond sala_obs_check evaluator,
--                                              dev-active shape; src
--                                              seed/phase5/insert_sala_observacion_estancia.sql
--                                              3-cond tree is stale, see deltas)
--   Hospitalización (1, dominio='hospitalizacion'):
--     6. centro_costo_hospitalizacion_valido  (52 conds = OR root + 12 branches,
--                                              faithful copy of the dev-active v9
--                                              tree as a single active v1, like 011
--                                              did for centro_costo_urgencias_valido;
--                                              src seed/migracion-engine/14_centro_costo_comun.sql
--                                              base + orden-11 branch, see deltas)
-- Total: 60 condiciones.
--
-- Catalogs seeded (additive WHERE NOT EXISTS, never overwritten):
--   - profesionales_urgencias            (23 codes; dev == prod byte-identical,
--                                         verified read-only SELECT)
--   - codigos_exceptuados                (15 codes, src 012 verbatim)
--   - centro_costo_pyp                   (6 codes, src 012 verbatim)
--   - centro_costo_quirofano             (4 codes, src 012 verbatim)
--   - centro_costo_hospitalizacion       (2 codes, src 012 verbatim)
--   - centros_costo_validos_urgencias    (8 centers; dev == prod byte-identical,
--                                         verified read-only SELECT)
--   - sala_codes                         (5 codes, src
--                                         seed/migracion-engine/16_sala_observacion_condiciones.sql;
--                                         DEV-ONLY gap: absent from prod, trivially
--                                         seedable; jsonb-equal to dev value)
-- Shared-key values were compared read-only (SELECT only, never written)
-- dev (asis_hos) vs prod (control_system_prod): profesionales_urgencias,
-- entidades_ess, centros_costo_validos_urgencias, facturadores_urgencias and
-- codigos_exceptuados_responsable_urgencias are EQUAL, so the literals below
-- reuse the 011/012 spellings verbatim. No conflicts found.
--
-- cat_in audit: seeded trees reference exactly these keys —
--   profesionales_urgencias (profesional_urgencias_valido),
--   codigos_exceptuados, centro_costo_pyp, centro_costo_quirofano,
--   centro_costo_hospitalizacion, centros_costo_validos_urgencias
--   (centro_costo_hospitalizacion_valido).
-- The two sala_*_evaluator trees use NO cat_in (single sala_obs_check cond,
-- faithful to dev). sala_codes is seeded as a trivial gap-fill for the F16
-- tree family (sala_observacion_valido); the evaluator itself carries hardcoded
-- sets (SALA_CODES / ENTITIES_05DSB01 in evaluators.py) and reads no catalog.
--
-- Source deltas vs the phase/final seed files (dev-active shape wins, same
-- policy as 012):
--   - duplicados_farmacia: final_rules.sql parents the gt-cantidad node under
--     the eq-tipo_factura ATOMIC node via MAX(id) (cond 388 padre 387 in dev),
--     so the AND root effectively has ONE live child and the cantidad check is
--     dead. Seeded with both atomics under the AND root (intended shape per the
--     file's own "simplified per-row check" comment). BEHAVIOR FIX vs dev: rows
--     tipo FARMACIA now also require cantidad > 1 (fewer flags, correct ones).
--   - profesional_urgencias_valido: phase2 inline `in` (23 codes) superseded by
--     the cat_in shape (dev-active, 2 conds; same values). Seeded as cat_in,
--     same call 012 made for odonto/equipos profesionales.
--   - revision_cantidad_urgencias: phase6 file is exact (1 cond + group_by sum
--     params, dev-verbatim incl. key order). No delta.
--   - sala_observacion_entidad / sala_observacion_estancia_prolongada: the
--     final_rules.sql (entidad) / phase5 (estancia) AND trees are stale; dev
--     runs both as a single sala_obs_check evaluator cond (reglas 48/30).
--     Seeded as the evaluator shape (dev-active). Known evaluator caveat, kept
--     verbatim from evaluators.py: estancia <= 2h never matches (F16 sub-rule 6
--     fixes this only for sala_observacion_valido, out of scope here).
--   - centro_costo_hospitalizacion_valido: dev holds ONLY v9 active (52 conds);
--     no retired siblings exist. F14 (14_centro_costo_comun.sql) covers this
--     name with the 50-cond base (orden 0-10); dev additionally carries the
--     orden-11 branch NOT(cat_in centros_costo_validos_urgencias) — the same
--     extra branch F14 gates to urgencias only. Seeded as the full 52-cond
--     dev-verbatim tree (orden values kept; standard F14 child layout).
--     Composite valor_esperado normalized SQL-NULL like 010/011/012 and prod
--     (dev v9 stores json 'null'; engine treats both as absent).
--
-- Version drift: identity is (nombre, version); this migration authors a single
-- active v1 per rule and never mass-retires sibling versions (lifecycle belongs
-- to the rule CRUD). On prod none of the 6 names exist yet (39-rule inventory,
-- read-only), so v1 lands clean. On dev-like DBs the seeded v1 coexists with
-- any pre-existing active sibling (e.g. hosp v9) until reconciled at apply
-- time — flagged, not resolved here (prod writes are out of scope).
--
-- Pre-existing engine-path gaps (NOT fixed here, noted for the record):
--   - urgencias detect_all evaluates "revision_cantidad_urgencias_valido"
--     (with _valido suffix) which exists NOWHERE (dev, prod, seeds) → that
--     branch always yields "Rule not found" → []. The seeded
--     revision_cantidad_urgencias (no suffix) is the seed-covered name.
--   - urgencias detect_all evaluates sala_observacion_valido + 6 sala_obs_*
--     sub-rules, none of which exist in prod (39-rule inventory) → likewise
--     dormant until seeded in a later change. The two sala rules seeded here
--     are the legacy-named rows (dormant in both engine and legacy paths).
--
-- Excluded (noted, not seeded):
--   - duplicados_farmacia_v2: no seed exists in seed/ or seeds/ (verified).
--     Dev holds a 1-cond active row.
--   - revision_cantidad_v2: no seed exists in seed/ or seeds/ (verified).
--     Dev holds a 1-cond active row.
--   - sala_obs_check_set: no seed exists in seed/ or seeds/ (verified).
--     Dev holds a 4-cond active row.
--   - ide_contrato_reverse_urgencias_valido: seeds/phase3/
--     insert_ide_contrato_reverse.sql DOES exist but uses BEGIN/COMMIT +
--     MAX(id)-style parenting (not DELETE+INSERT-safe per the 011
--     no-transaction-control rule) and dev holds a 21-cond active tree.
--     Excluded pending a full-coverage idempotent rewrite (same class as the
--     ide_contrato_odontologia_valido exclusion in 012).
--   - ide_contrato_odontologia_valido: partial seed only
--     (seeds/phase3/insert_ide_contrato_odon.sql covers the top 8 entities;
--     prod holds a 111-cond active tree). Needs rewrite — separate change
--     (carried over from 012).
--   - detect_duplicados_base: no seed exists anywhere in seed/ or seeds/
--     (verified; only the Python helper
--     app/services/transversales/detect_duplicados_base.py exists). Prod holds
--     no such rule; dev holds a 1-cond active transversal row. Excluded.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema guards (same as 010/011/012): widen condiciones.operador, normalize
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
-- Catalogs (additive only — WHERE NOT EXISTS, never overwritten)
-- ---------------------------------------------------------------------------
INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias',
       '["03568", "01235", "01960", "03493", "03822", "01293", "02249", "03799", "03222", "03384", "03154", "01289", "03628", "03893", "03710", "01868", "03742", "03857", "03365", "03730", "02217", "03374", "03255"]'::jsonb,
       'urgencias', 'Codigos de profesionales validos', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_exceptuados',
       '["194901", "23105", "23116", "232200", "232201", "25142AFINA", "90123501", "901325", "90385901", "90386401", "903883", "9038831", "904903", "906230", "906836"]'::jsonb,
       'transversal', 'Códigos exceptuados de reglas de centro de costo (CODIGOS_EXCEPTUADOS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_exceptuados');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'centro_costo_pyp',
       '["990211", "890205", "890405", "861801", "39360", "29116"]'::jsonb,
       'transversal', 'Códigos que requieren centro = PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN (CODIGOS_PYP_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centro_costo_pyp');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'centro_costo_quirofano',
       '["735301", "90DS02", "512002", "39220"]'::jsonb,
       'transversal', 'Códigos que requieren centro = QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO (CODIGOS_QUIROFANO_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centro_costo_quirofano');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'centro_costo_hospitalizacion',
       '["890601H", "39133"]'::jsonb,
       'transversal', 'Códigos que requieren centro = HOSPITALIZACIÓN - ESTANCIA GENERAL (CODIGOS_HOSPITALIZACION_ESTANCIA)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centro_costo_hospitalizacion');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'centros_costo_validos_urgencias',
       '["URGENCIAS", "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", "APOYO DIAGNOSTICO-LABORATOR CLINICO", "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN", "HOSPITALIZACIÓN - ESTANCIA GENERAL", "APOYO DIAGNOSTICO-IMAGENOLOGIA", "TRASLADOS", "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"]'::jsonb,
       'urgencias', 'Centros de costo válidos para Urgencias (CENTROS_COSTO_VALIDOS_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_validos_urgencias');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'sala_codes',
       '["5DSB01", "05DSB01", "129B02", "38114", "38915"]'::jsonb,
       'urgencias', 'Códigos de sala de observación activadores (SALA_CODES)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'sala_codes');

-- ===========================================================================
-- URGENCIAS (5)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. duplicados_farmacia (src seed/final_rules.sql, parenting corrected:
--    both atomics under the AND root; the source nests gt under the atomic
--    eq via MAX(id), leaving the cantidad check dead in dev)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'duplicados_farmacia', 'Detecta posibles duplicados en facturacion de farmacia (simplificado - per-row check)', 'urgencias', 'active', 1, 35, 'warning', true, NULL
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
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'duplicados_farmacia' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"FARMACIA"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gt', 'invoice.cantidad', '1', 1);
END $$;

-- ---------------------------------------------------------------------------
-- 2. profesional_urgencias_valido (src seed/phase2/insert_profesionales_urg.sql,
--    inline `in` superseded by the dev-active cat_in shape, same values)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'profesional_urgencias_valido', 'Profesional no válido en Urgencias', 'urgencias', 'active', 1, 40, 'error', true, NULL
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
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'profesional_urgencias_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias"', 0);
END $$;

-- ---------------------------------------------------------------------------
-- 3. revision_cantidad_urgencias (src seed/phase6/insert_revision_cantidad.sql,
--    exact: group_by sum params + single gt cond)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'revision_cantidad_urgencias', 'Revisión necesaria: cantidad anómala por factura (suma > 1)', 'urgencias', 'active', 1, 40, 'warning', true,
    '[{"group_by": "numero_factura", "aggregations": [{"field": "cantidad", "target": "sum_cantidad", "function": "sum"}]}]'::jsonb
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'revision_cantidad_urgencias' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'gt', 'invoice.sum_cantidad', '1', 0);
END $$;

-- ---------------------------------------------------------------------------
-- 4. sala_observacion_entidad (dev-active sala_obs_check evaluator shape;
--    the seed/final_rules.sql 3-cond AND tree is stale and NOT seeded)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'sala_observacion_entidad', 'Estancia en sala de observacion mayor a 6 horas para entidades especificas', 'urgencias', 'active', 1, 30, 'error', true, NULL
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'sala_observacion_entidad' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'sala_obs_check', 'invoice.codigo', '""', 0);
END $$;

-- ---------------------------------------------------------------------------
-- 5. sala_observacion_estancia_prolongada (dev-active sala_obs_check evaluator
--    shape; the seed/phase5 3-cond AND tree is stale and NOT seeded)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'sala_observacion_estancia_prolongada', 'Estancia en Urgencias superior a 6 horas — requiere código de sala de observación', 'urgencias', 'active', 1, 32, 'warning', true, NULL
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'sala_observacion_estancia_prolongada' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'sala_obs_check', 'invoice.codigo', '""', 0);
END $$;

-- ===========================================================================
-- HOSPITALIZACIÓN (1)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 6. centro_costo_hospitalizacion_valido
-- Faithful copy of the dev-active v9 52-cond OR tree as a single active v1
-- (F14 base orden 0-10 + the orden-11 NOT(cat_in centros validos) branch).
-- Orden values are dev-verbatim (standard F14 child layout throughout).
-- Composite valor_esperado normalized to SQL NULL (010/011/012 + prod
-- convention; dev v9 stores json 'null', engine-equivalent).
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
VALUES (
    'centro_costo_hospitalizacion_valido', 'Centro de costo no válido en Hospitalización', 'hospitalizacion', 'active', 1, 25, 'error', true, NULL
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
    cd_root INT;
    cd_r9 INT; cd_r9_n INT;
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'centro_costo_hospitalizacion_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO cd_root;

    -- REGLA9 (orden 0): tarifario farmacia -> centro FARMACIA
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

    -- REGLA1 (orden 1): cod_tipo=02 + lab=No + no exceptuado -> centro IMAGENOLOGIA
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

    -- REVERSE1 (orden 2): centro IMAGENOLOGIA -> cod_tipo=02 + lab=No
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

    -- REGLA2 (orden 3): cod_tipo=14 -> centro TRASLADOS
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

    -- REVERSE2 (orden 4): centro TRASLADOS -> cod_tipo=14
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

    -- REGLA3 (orden 5): codigo PyP -> centro PYP
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

    -- REVERSE3 (orden 6): centro PYP -> codigo PyP
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

    -- REGLA4 (orden 7): codigo quirofano -> centro QUIROFANO
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

    -- REVERSE4 (orden 8): centro QUIROFANO -> codigo quirofano
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

    -- REVERSE9 (orden 9): centro FARMACIA -> tarifario farmacia
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

    -- REGLA8 (orden 10): codigo hospitalizacion -> centro HOSPITALIZACION
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

    -- Extra branch (orden 11, dev-verbatim): centro fuera del catalogo valido
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_root, 'composite', 'NOT', NULL, NULL, 11)
    RETURNING id INTO cd_invalid_centro;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, cd_invalid_centro, 'atomic', 'cat_in', 'invoice.centro_costo', to_jsonb('centros_costo_validos_urgencias'::text), 0);
END $$;

-- ---------------------------------------------------------------------------
-- Lineage: seeded v1 rows are their own base (same as 009/011/012).
-- ---------------------------------------------------------------------------
UPDATE reglas SET rule_base_id = id
WHERE nombre IN ('duplicados_farmacia', 'profesional_urgencias_valido',
                 'revision_cantidad_urgencias', 'sala_observacion_entidad',
                 'sala_observacion_estancia_prolongada',
                 'centro_costo_hospitalizacion_valido')
  AND version = 1
  AND rule_base_id IS NULL;
