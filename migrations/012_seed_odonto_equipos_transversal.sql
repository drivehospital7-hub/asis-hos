-- =============================================================================
-- 012_seed_odonto_equipos_transversal.sql
--
-- Seeds the odontología + equipos_basicos + transversal engine rules + catalogs
-- by (nombre, version), never by hardcoded live IDs. Idempotent DELETE+INSERT
-- pattern like 010/011: each rule is upserted ON CONFLICT (nombre, version = 1)
-- and its condition tree is deleted + rebuilt, so re-running is a no-op.
--
-- Rules seeded (22 total, all estado='active', activo=true, v1):
--   Odontología (4, dominio='odontologia'):
--     1. centro_costo_odontologia_valido   (50 conds, F14 full OR tree)
--     2. profesional_odontologia_valido    (2 conds, NOT cat_in profesionales_odontologia)
--     3. ruta_duplicada                    (1 cond, group_by identificacion)
--     4. valores_decimales                 (3 conds, OR regex)
--   Equipos básicos (2, dominio='equipos_basicos'):
--     5. centro_costo_equipos_basicos_valido (50 conds, F14 full OR tree)
--     6. profesional_equipos_validos         (2 conds, NOT cat_in profesionales_equipos_basicos)
--   Transversal (16, dominio='transversal'):
--     7. cantidad_consultas_anomalas       (3 conds, src seeds/005)
--     8. cantidad_general_anomalas         (2 conds, src seeds/005)
--     9. cantidad_pyp_anomalas             (3 conds, src seeds/005)
--    10. codigo_entidad                    (2 conds, NOT ent_code_match)
--    11. cups_sin_contrato                 (2 conds, NOT exists_in_db procedimiento.cups)
--    12. doble_tipo_procedimiento          (1 cond, group_by numero_factura)
--    13. entidad_86000_requiere_as_ms      (4 conds, src seeds/004)
--    14. tipo_documento_edad_7_17          (7 conds, AND + OR[CC,AS,RC])
--    15. tipo_documento_edad_as_menor      (3 conds, src seed/tipo_doc_edad_completo.sql)
--    16. tipo_documento_edad_ce_invalido   (3 conds, AND eq CE + lt edad 18)
--    17. tipo_documento_edad_cn_invalido   (3 conds, src tipo_doc_edad_completo.sql)
--    18. tipo_documento_edad_mayor_18      (7 conds, AND + OR[TI,RC,MS,TE])
--    19. tipo_documento_edad_menor_7       (7 conds, AND + OR[TI,CC,AS,TE])
--    20. tipo_documento_edad_ms_mayor      (3 conds, src tipo_doc_edad_completo.sql)
--    21. tipo_id_requiere_entidad_86000    (4 conds, src seeds/004)
--    22. tipo_usuario_valido               (2 conds, NOT cat_in tipo_usuario_validos)
-- Total: 164 condiciones.
--
-- Catalogs seeded (additive WHERE NOT EXISTS, never overwritten):
--   F14 cat_in keys: codigos_exceptuados, centro_costo_pyp,
--     centro_costo_quirofano, centro_costo_hospitalizacion
--   Laboratorio/intramural: centros_costo_laboratorio_validos,
--     centros_costo_pyp_intramural, centros_costo_validos_intramural
--   Profesionales: profesionales_odontologia, profesionales_equipos_basicos
--   Transversal: tipo_usuario_validos, entidades_ess,
--     codigos_exceptuados_ambulatorio, codigos_exceptuados_responsable_urgencias
--     (also seeded by 011; WHERE NOT EXISTS keeps it a no-op),
--     codigos_excluidos_vacunacion, codigos_tipo_procedimiento_ambulatorio,
--     codigos_tipo_procedimiento_laboratorio
-- Values are byte-identical to the read-only prod inventory (SELECT only,
-- never written): in particular tipo_usuario_validos keeps the accented
-- "OTROS (REGÍMENES ESPECIALES, EOC)" (seeds/002 + seeds/006 carry the
-- unaccented stale spelling and are NOT used as value source).
--
-- cat_in audit: seeded trees reference exactly these keys —
--   profesionales_odontologia, profesionales_equipos_basicos,
--   tipo_usuario_validos, codigos_exceptuados, centro_costo_pyp,
--   centro_costo_quirofano, centro_costo_hospitalizacion.
-- Sibling keys seeded for related rules: entidades_ess (sala_observacion),
-- laboratorio/intramural families (intramural centro_costo), exceptuados
-- family (intramural REGLA7 / responsable urgencias / vacunación).
--
-- Source deltas vs the phase seed files (prod-active shape wins; legacy
-- detector app/services/transversales/tipo_documento_edad.py confirms):
--   - profesionales_*/tipo_usuario: prod uses cat_in; phase2/002 inline sets
--     are stale snapshots of the same values. Seeded as cat_in.
--   - centro_costo odonto/equipos: phase4 2-cond inline version is superseded
--     by the migracion-engine/14 full OR tree (50 conds, prod-active). Seeded
--     as F14, faithful copy of seed/migracion-engine/14_centro_costo_comun.sql
--     restricted to these 2 rule names.
--   - ruta_duplicada: seeds/motor_reglas_seed.sql row-shape (factura_count)
--     is superseded by the group_by identificacion shape (prod-active).
--   - codigo_entidad: phase7 contains-"{" placeholder superseded by the
--     ent_code_match evaluator (prod-active).
--   - cups_sin_contrato: phase7 cups_contratado evaluator superseded by the
--     exists_in_db procedimiento.cups check (prod-active).
--   - tipo_documento_edad_mayor_18/_menor_7: phase5 NOT(single-type) shape
--     superseded by the OR shapes incl. TE (prod-active, 7 conds each).
--     tipo_documento_edad_7_17 likewise uses the OR shape but with 3 children
--     (CC, AS, RC — NO TE, prod-verbatim and correct: TE behaves like TI and
--     is valid for 7-17 per detect_tipo_documento_edad).
--   - tipo_documento_edad_ce_invalido: tipo_doc_edad_completo.sql lte edad 7
--     is stale (CE behaves like CC, valid only >= 18); seeded as lt edad 18
--     (prod-active). Its descripcion ("...mayores de 7 anos") is kept verbatim
--     from prod and is itself stale — not fixed here.
--   - valores_decimales: seeds/motor value 'error' superseded by prod
--     'warning' (prio 10 kept). Prod holds ONLY v3 active (no v1 row); this
--     migration seeds the (nombre, v1) lineage like 010/011. On a future prod
--     apply this yields a second active version (v1 + v3) unless v3 is retired
--     or reconciled at apply time — flagged, not resolved here (prod writes
--     are out of scope).
--   - cantidad_pyp_anomalas keeps prod-verbatim "Promocion y Prevencion"
--     (no accent), differing from base CONVENIO_PYP ("Promoción y Prevención").
--
-- Excluded (noted, not seeded):
--   - ide_contrato_odontologia_valido: a seed DOES exist
--     (seeds/phase3/insert_ide_contrato_odon.sql) but covers only the top 8
--     entities, uses BEGIN/COMMIT + WITH MAX(id)-style parenting (not
--     DELETE+INSERT-safe per the 011 no-transaction-control rule), and prod
--     holds a 111-cond active tree. Seeding the partial file would regress
--     prod. Excluded pending a full-coverage idempotent rewrite.
--   - detect_duplicados_base: no seed exists anywhere in seed/ or seeds/
--     (verified). Prod holds a 1-cond active row. Excluded.
--   - ide_contrato_equipos_basicos_valido: referenced by
--     app/services/equipos_basicos/detect_all.py but absent from prod and from
--     every seed file; equipos legacy falls back to
--     detect_ide_contrato_odontologia. Out of scope, noted as a pre-existing
--     engine-path gap ("Rule not found" → []).
--   - equipos detect_all "cantidades_anomalas" (singular): no such rule exists
--     (only the 3 cantidad_*_anomalas variants); pre-existing caller bug,
--     out of scope.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema guards (same as 010/011): widen condiciones.operador, normalize
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
SELECT 'centros_costo_laboratorio_validos',
       '["APOYO DIAGNOSTICO-LABORATOR CLINICO", "APOYO DIAGNOSTICO-LABORATOR CLINICO."]'::jsonb,
       'intramural', 'Centros de costo válidos para laboratorio clínico (CENTROS_COSTO_LABORATORIO_VALIDOS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_laboratorio_validos');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'centros_costo_pyp_intramural',
       '["SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION", "SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION.", "SERVICIOS AMBULATORIOS- PROMOCION/PREVENCION"]'::jsonb,
       'intramural', 'Centros de costo PyP válidos en Intramural (CENTROS_COSTO_PYP_INTRAMURAL)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_pyp_intramural');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'centros_costo_validos_intramural',
       '["APOYO DIAGNOSTICO-LABORATOR CLINICO", "APOYO DIAGNOSTICO-IMAGENOLOGIA", "APOYO DIAGNOSTICO-LABORATOR CLINICO.", "SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS", "SALUD PUBLICA-VACUNACION  REGULAR", "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", "HOSPITALIZACIÓN - ESTANCIA GENERAL", "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO", "TRASLADOS", "SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION", "SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION.", "SERVICIOS AMBULATORIOS- PROMOCION/PREVENCION", "URGENCIAS"]'::jsonb,
       'intramural', 'Centros de costo válidos en Intramural (INTRAMURAL_CENTROS_COSTO_VALIDOS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_validos_intramural');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_odontologia',
       '["03424", "03007", "01329", "01251", "01330", "03698"]'::jsonb,
       'odontologia', 'Códigos de profesionales válidos en Odontología (PROFESIONALES_ODONTOLOGIA_VALIDACION)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_odontologia');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_equipos_basicos',
       '["03764", "03762", "03808", "02981", "03761", "03766", "03739", "03763", "02084", "03825", "03831", "03851", "03848"]'::jsonb,
       'equipos_basicos', 'Códigos de profesionales válidos en Equipos Básicos (PROFESIONALES_EQUIPOS_BASICOS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_equipos_basicos');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'tipo_usuario_validos',
       '["SUBSIDIADO", "CONTRIBUTIVO", "OTROS (REGÍMENES ESPECIALES, EOC)", "VINCULADO", "PARTICULAR"]'::jsonb,
       'transversal', 'Tipos de usuario válidos (TIPO_USUARIO_VALORES)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'tipo_usuario_validos');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'entidades_ess',
       '["ESS118", "ESSC18"]'::jsonb,
       'urgencias', 'Entidades ESS que usan 05DSB01 para >6h (ENTITIES_05DSB01)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'entidades_ess');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_exceptuados_ambulatorio',
       '["735301", "861101"]'::jsonb,
       'intramural', 'Códigos exceptuados de REGLA7 ambulatorio (CODIGOS_EXCEPTUADOS_AMBULATORIO)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_exceptuados_ambulatorio');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_exceptuados_responsable_urgencias',
       '["735301"]'::jsonb,
       'intramural', 'Códigos exceptuados de REGLA_RESPONSABLE_URGENCIAS (CODIGOS_EXCEPTUADOS_RESPONSABLE_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_exceptuados_responsable_urgencias');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_excluidos_vacunacion',
       '["906249PR", "906249"]'::jsonb,
       'intramural', 'Códigos excluidos de la regla de vacunación (CODIGOS_EXCLUIDOS_VACUNACION)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_excluidos_vacunacion');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_tipo_procedimiento_ambulatorio',
       '["03", "04"]'::jsonb,
       'intramural', 'Códigos tipo procedimiento que exigen SERVICIOS AMBULATORIOS (CODIGOS_TIPO_PROCEDIMIENTO_AMBULATORIO)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_tipo_procedimiento_ambulatorio');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_tipo_procedimiento_laboratorio',
       '["02", "05"]'::jsonb,
       'intramural', 'Códigos tipo procedimiento para laboratorio clínico (CODIGOS_TIPO_PROCEDIMIENTO_LABORATORIO)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_tipo_procedimiento_laboratorio');

-- ===========================================================================
-- ODONTOLOGÍA (4)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- centro_costo_odontologia_valido + centro_costo_equipos_basicos_valido
-- F14 full OR trees (faithful copy of
-- seed/migracion-engine/14_centro_costo_comun.sql restricted to these 2
-- names; reglas rows upserted here first so the tree builder never skips).
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'centro_costo_odontologia_valido', 'Centro de costo no válido en Odontología', 'odontologia', 'active', 1, 25, 'error', true, NULL
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

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'centro_costo_equipos_basicos_valido', 'Centro de costo no válido en Equipos Básicos', 'equipos_basicos', 'active', 1, 25, 'error', true, NULL
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
    _rule_names TEXT[] := ARRAY[
        'centro_costo_equipos_basicos_valido',
        'centro_costo_odontologia_valido'
    ];
    _rule_name TEXT;
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
BEGIN
    FOREACH _rule_name IN ARRAY _rule_names LOOP
        SELECT id INTO _regla_id FROM reglas WHERE nombre = _rule_name AND version = 1;
        IF _regla_id IS NULL THEN
            CONTINUE;
        END IF;

        DELETE FROM condiciones WHERE regla_id = _regla_id;

        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
        RETURNING id INTO cd_root;

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

    END LOOP;
END $$;

-- ===========================================================================
-- profesional_odontologia_valido (NOT cat_in profesionales_odontologia)
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_odontologia_valido', 'Profesional no válido en Odontología', 'odontologia', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'profesional_odontologia_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_odontologia"', 0);
END $$;

-- ===========================================================================
-- ruta_duplicada (group_by identificacion, distinct_count numero_factura)
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'ruta_duplicada', 'Detecta pacientes con múltiples facturas en Promoción y Prevención (PyP).', 'odontologia', 'active', 1, 20, 'warning', true,
    '[{"group_by": "identificacion", "aggregations": [{"field": "numero_factura", "target": "distinct_count_numero_factura", "function": "distinct_count"}], "filter_field": "convenio_facturado", "filter_value": "Promocion y Prevencion"}]'::jsonb
, 'Ruta Duplicada', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'ruta_duplicada' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'gte', 'group.distinct_count_numero_factura', '3', 0);
END $$;

-- ===========================================================================
-- valores_decimales (OR regex vlr_subsidiado / vlr_procedimiento)
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'valores_decimales', 'Detecta facturas con valores decimales en Vlr. Subsidiado o Vlr. Procedimiento.', 'odontologia', 'active', 1, 10, 'warning', true, NULL
, 'Decimales', '=Vlr. Procedimiento', '=Vlr. Subsidiado', 'Valores con decimales')
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'valores_decimales' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'OR', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'regex', 'invoice.vlr_subsidiado', '"\\.\\d*[1-9]\\d*$"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'regex', 'invoice.vlr_procedimiento', '"\\.\\d*[1-9]\\d*$"', 1);
END $$;

-- ===========================================================================
-- EQUIPOS BÁSICOS (2)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- profesional_equipos_validos (NOT cat_in profesionales_equipos_basicos)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_equipos_validos', 'Profesional no válido en Equipos Básicos', 'equipos_basicos', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'profesional_equipos_validos' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_equipos_basicos"', 0);
END $$;

-- ===========================================================================
-- TRANSVERSAL (16)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- cantidad_consultas_anomalas (src seeds/005_cantidades_anomalas_seed.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'cantidad_consultas_anomalas', 'Consultas con cantidad >= 2 se consideran anomalas.', 'transversal', 'active', 1, 30, 'warning', true, NULL
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cantidad_consultas_anomalas' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tipo_procedimiento', '"Consultas"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gte', 'invoice.cantidad', '2', 1);
END $$;

-- ---------------------------------------------------------------------------
-- cantidad_general_anomalas (src seeds/005_cantidades_anomalas_seed.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'cantidad_general_anomalas', 'Cualquier tipo de procedimiento con cantidad > 10 se considera anomalo.', 'transversal', 'active', 1, 30, 'warning', true, NULL
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cantidad_general_anomalas' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gt', 'invoice.cantidad', '10', 0);
END $$;

-- ---------------------------------------------------------------------------
-- cantidad_pyp_anomalas (src seeds/005_cantidades_anomalas_seed.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'cantidad_pyp_anomalas', 'Convenio PyP con cantidad >= 3 se considera anomalo.', 'transversal', 'active', 1, 30, 'warning', true, NULL
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cantidad_pyp_anomalas' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.convenio_facturado', '"Promocion y Prevencion"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gte', 'invoice.cantidad', '3', 1);
END $$;

-- ---------------------------------------------------------------------------
-- codigo_entidad (NOT ent_code_match)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'codigo_entidad', 'Entidad Afiliación carece de código de entidad en formato esperado', 'transversal', 'active', 1, 40, 'warning', true, NULL
, 'Codigo-Entidad-vs-Afiliacion', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'codigo_entidad' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'ent_code_match', 'invoice.codigo_entidad_cobrar', '"[A-Z0-9]+"', 0);
END $$;

-- ---------------------------------------------------------------------------
-- cups_sin_contrato (NOT exists_in_db procedimiento.cups)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'cups_sin_contrato', 'CUPS no encontrado en el catálogo de procedimientos', 'transversal', 'active', 1, 35, 'error', true, NULL
, 'Cups Sin Contrato', 'codigo,procedimiento', 'Entidad: {codigo_entidad_cobrar}, {entidad}', NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cups_sin_contrato' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'exists_in_db', 'invoice.codigo', '{"table": "procedimiento", "field": "cups"}', 0);
END $$;

-- ---------------------------------------------------------------------------
-- doble_tipo_procedimiento (src seed/phase6/insert_doble_tipo_procedimiento.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'doble_tipo_procedimiento', 'Factura con más de un tipo de procedimiento', 'transversal', 'active', 1, 35, 'error', true,
    '[{"group_by": "numero_factura", "aggregations": [{"field": "tipo_procedimiento", "target": "distinct_count_tipo_procedimiento", "function": "distinct_count"}]}]'::jsonb
, 'Doble Tipo Procedimiento', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'doble_tipo_procedimiento' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'gt', 'invoice.distinct_count_tipo_procedimiento', '1', 0);
END $$;

-- ---------------------------------------------------------------------------
-- entidad_86000_requiere_as_ms (src seeds/004_tipo_id_entidad_seed.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'entidad_86000_requiere_as_ms', 'Cod Entidad Cobrar = 86000 solo es valido para tipo identificacion AS o MS.', 'transversal', 'active', 1, 20, 'error', true, NULL
, 'Codigo-Entidad-vs-Afiliacion', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'entidad_86000_requiere_as_ms' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '86000', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _not_id, 'atomic', 'in', 'invoice.tipo_identificacion', '["AS", "MS"]', 0);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_documento_edad_7_17 (AND gte 7 + lt 18 + OR[CC,AS,RC])
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_documento_edad_7_17', 'Tipo de identificacion incorrecto para edad 7-17 anos (debe ser TI)', 'transversal', 'active', 1, 30, 'error', true, NULL
, 'Tipo Identificacion / Edad', NULL, NULL, NULL)
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
    _or_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_documento_edad_7_17' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gte', 'date.edad', '7', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'lt', 'date.edad', '18', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'OR', NULL, NULL, 2)
    RETURNING id INTO _or_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"CC"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"AS"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"RC"', 2);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_documento_edad_as_menor (src seed/tipo_doc_edad_completo.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_documento_edad_as_menor', 'Tipo AS (Adulto Sin identificacion) no valido para menores de 18 anos', 'transversal', 'active', 1, 30, 'error', true, NULL
, 'Tipo Identificacion / Edad', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_documento_edad_as_menor' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"AS"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'lt', 'date.edad', '18', 1);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_documento_edad_ce_invalido (AND eq CE + lt edad 18)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_documento_edad_ce_invalido', 'Tipo CE (Cedula de Extranjeria) solo valido para mayores de 7 anos', 'transversal', 'active', 1, 30, 'error', true, NULL
, 'Tipo Identificacion / Edad', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_documento_edad_ce_invalido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"CE"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'lt', 'date.edad', '18', 1);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_documento_edad_cn_invalido (src seed/tipo_doc_edad_completo.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_documento_edad_cn_invalido', 'Tipo CN (Certificado de Nacimiento) solo valido para menores de 2 meses', 'transversal', 'active', 1, 30, 'error', true, NULL
, 'Tipo Identificacion / Edad', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_documento_edad_cn_invalido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"CN"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gte', 'date.edad_meses', '2', 1);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_documento_edad_mayor_18 (AND gte 18 + OR[TI,RC,MS,TE])
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_documento_edad_mayor_18', 'Tipo de identificación incorrecto para mayor de edad (debe ser CC)', 'transversal', 'active', 1, 31, 'error', true, NULL
, 'Tipo Identificacion / Edad', NULL, NULL, NULL)
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
    _or_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_documento_edad_mayor_18' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gte', 'date.edad', '18', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'OR', NULL, NULL, 1)
    RETURNING id INTO _or_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"TI"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"RC"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"MS"', 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"TE"', 3);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_documento_edad_menor_7 (AND lt 7 + OR[TI,CC,AS,TE])
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_documento_edad_menor_7', 'Tipo de identificación incorrecto para menor de 7 años (debe ser RC)', 'transversal', 'active', 1, 30, 'error', true, NULL
, 'Tipo Identificacion / Edad', NULL, NULL, NULL)
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
    _or_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_documento_edad_menor_7' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'lt', 'date.edad', '7', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'OR', NULL, NULL, 1)
    RETURNING id INTO _or_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"TI"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"CC"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"AS"', 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _or_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"TE"', 3);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_documento_edad_ms_mayor (src seed/tipo_doc_edad_completo.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_documento_edad_ms_mayor', 'Tipo MS (Menor Sin identificacion) no valido para mayores de 18 anos', 'transversal', 'active', 1, 30, 'error', true, NULL
, 'Tipo Identificacion / Edad', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_documento_edad_ms_mayor' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tipo_identificacion', '"MS"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gte', 'date.edad', '18', 1);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_id_requiere_entidad_86000 (src seeds/004_tipo_id_entidad_seed.sql)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_id_requiere_entidad_86000', 'AS o MS como tipo identificacion requieren Cod Entidad Cobrar = 86000.', 'transversal', 'active', 1, 20, 'error', true, NULL
, 'Codigo-Entidad-vs-Afiliacion', NULL, NULL, NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_id_requiere_entidad_86000' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.tipo_identificacion', '["AS", "MS"]', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'composite', 'NOT', NULL, NULL, 1)
    RETURNING id INTO _not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _not_id, 'atomic', 'eq', 'invoice.codigo_entidad_cobrar', '86000', 0);
END $$;

-- ---------------------------------------------------------------------------
-- tipo_usuario_valido (NOT cat_in tipo_usuario_validos)
-- ---------------------------------------------------------------------------
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'tipo_usuario_valido', 'Detecta facturas con tipo de usuario no válido.', 'transversal', 'active', 1, 15, 'warning', true, NULL
, 'Tipo Usuario', 'codigo,procedimiento', 'tipo_actual', NULL)
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
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'tipo_usuario_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'cat_in', 'invoice.tipo_usuario', '"tipo_usuario_validos"', 0);
END $$;

-- ---------------------------------------------------------------------------
-- Lineage: seeded v1 rows are their own base (same as 009/011).
-- ---------------------------------------------------------------------------
UPDATE reglas SET rule_base_id = id
WHERE nombre IN ('centro_costo_odontologia_valido', 'profesional_odontologia_valido',
                 'ruta_duplicada', 'valores_decimales',
                 'centro_costo_equipos_basicos_valido', 'profesional_equipos_validos',
                 'cantidad_consultas_anomalas', 'cantidad_general_anomalas',
                 'cantidad_pyp_anomalas', 'codigo_entidad', 'cups_sin_contrato',
                 'doble_tipo_procedimiento', 'entidad_86000_requiere_as_ms',
                 'tipo_documento_edad_7_17', 'tipo_documento_edad_as_menor',
                 'tipo_documento_edad_ce_invalido', 'tipo_documento_edad_cn_invalido',
                 'tipo_documento_edad_mayor_18', 'tipo_documento_edad_menor_7',
                 'tipo_documento_edad_ms_mayor', 'tipo_id_requiere_entidad_86000',
                 'tipo_usuario_valido')
  AND version = 1
  AND rule_base_id IS NULL;
