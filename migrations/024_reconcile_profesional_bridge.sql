-- ===========================================================================
-- 024: converge 022 urg_ rules to the prod bridge shape (final names)
-- ===========================================================================
-- Divergence: 022 seeded per-domain rules named profesional_urg_* with an
-- eq guard on invoice.tipo_factura_descripcion (= 'Urgencias'). Prod uses
-- one bridge rule per family named profesional_* (no urg_ prefix, no eq
-- guard) scoped to both hospitalizacion and urgencias via regla_dominios.
--
-- Convergent in both directions:
--   fresh DB: 022 creates the urg_ form, this file renames each urg_ row to
--     its final name (guarded: only when the final name is absent), strips
--     the eq guard by rebuilding the bridge condition tree, and ensures
--     both bridge rows.
--   prod DB: the urg_ form never existed, so the renames are no-ops; the
--     rule upserts only refresh activo/grupo_error and the guarded
--     condition inserts are no-ops when the bridge tree already exists.
--
-- Never creates or renames any other rule: neither the existence-check rules
-- nor the other-domain mirrors seeded by 022 are referenced here.
--
-- Idempotent, no BEGIN/COMMIT. Portable PG/SQLite: EXISTS + INSERT..SELECT,
-- correlated guard deletes, ON CONFLICT with literal SET. Catalog re-runs
-- below are copied from 022 (additive-guarded).
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- Catalogs re-run (copied from 022; additive-guarded, never redefined:
-- codigos_tipo_procedimiento_laboratorio is reused, not inserted)
-- ---------------------------------------------------------------------------
INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias_trabajadora_social',
       '["01235", "03568"]'::jsonb,
       'urgencias', 'Profesionales de Urgencias tipo TRABAJADORA SOCIAL (PROFESIONALES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias_trabajadora_social');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias_psicologa',
       '["01952", "01960", "02161", "03493"]'::jsonb,
       'urgencias', 'Profesionales de Urgencias tipo PSICOLOGA (PROFESIONALES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias_psicologa');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias_nutricionista',
       '["02786", "03822"]'::jsonb,
       'urgencias', 'Profesionales de Urgencias tipo NUTRICIONISTA (PROFESIONALES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias_nutricionista');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias_fisioterapeuta',
       '["03365", "03929"]'::jsonb,
       'urgencias', 'Profesionales de Urgencias tipo FISIOTERAPEUTA (PROFESIONALES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias_fisioterapeuta');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias_jefe_enfermeria',
       '["01346", "01868", "02749", "03379", "03710", "03742", "03857"]'::jsonb,
       'urgencias', 'Profesionales de Urgencias tipo JEFE ENFERMERIA (PROFESIONALES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias_jefe_enfermeria');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias_odontologo',
       '["01251", "03007", "03424"]'::jsonb,
       'urgencias', 'Profesionales de Urgencias tipo ODONTOLOGO (PROFESIONALES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias_odontologo');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias_medico',
       '["01293", "02249", "03154", "03384", "03577", "03628", "03799", "03893", "03911", "03928"]'::jsonb,
       'urgencias', 'Profesionales de Urgencias tipo MEDICO (PROFESIONALES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias_medico');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_urgencias_bacteriologa',
       '["02217", "03255", "03374", "03662", "03730", "03959"]'::jsonb,
       'urgencias', 'Profesionales de Urgencias tipo BACTERIOLOGA (PROFESIONALES_URGENCIAS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_urgencias_bacteriologa');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_odontologia_higienista',
       '["01329", "01330", "03698"]'::jsonb,
       'odontologia', 'Profesionales de Odontologia tipo HIGIENISTA (PROFESIONALES_ODONTOLOGIA_VALIDACION)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_odontologia_higienista');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_odontologia_odontologo',
       '["01251", "03007", "03424"]'::jsonb,
       'odontologia', 'Profesionales de Odontologia tipo ODONTOLOGO (PROFESIONALES_ODONTOLOGIA_VALIDACION)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_odontologia_odontologo');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_equipos_basicos_higienista',
       '["02084", "02981", "03761", "03762", "03808", "03825", "03848"]'::jsonb,
       'equipos_basicos', 'Profesionales de Equipos Basicos tipo HIGIENISTA (PROFESIONALES_EQUIPOS_BASICOS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_equipos_basicos_higienista');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'profesionales_equipos_basicos_odontologo',
       '["03739", "03763", "03764", "03766", "03831", "03851"]'::jsonb,
       'equipos_basicos', 'Profesionales de Equipos Basicos tipo ODONTOLOGO (PROFESIONALES_EQUIPOS_BASICOS)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'profesionales_equipos_basicos_odontologo');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_trabajadora_social',
       '["37701", "890409"]'::jsonb,
       'transversal', 'Codigos permitidos para TRABAJADORA SOCIAL (CODIGOS_TRABAJADORA_SOCIAL)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_trabajadora_social');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_psicologa',
       '["35102", "890408"]'::jsonb,
       'transversal', 'Codigos permitidos para PSICOLOGA (CODIGOS_PSICOLOGA)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_psicologa');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_nutricionista',
       '["37602", "890406"]'::jsonb,
       'transversal', 'Codigos permitidos para NUTRICIONISTA (CODIGOS_NUTRICIONISTA)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_nutricionista');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_fisioterapeuta',
       '["29117", "890411", "890412"]'::jsonb,
       'transversal', 'Codigos permitidos para FISIOTERAPEUTA (CODIGOS_FISIOTERAPEUTA)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_fisioterapeuta');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_jefe_enfermeria',
       '["29116", "39360", "861801", "890205", "890405", "990211"]'::jsonb,
       'transversal', 'Codigos permitidos para JEFE ENFERMERIA (CODIGOS_JEFE_ENFERMERIA)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_jefe_enfermeria');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_odontologo_urg',
       '["230101", "230102", "230201", "230202", "231101", "231201", "232102", "232103", "232201", "232401", "232402", "237102", "237103", "237301", "237302", "237304", "249101", "36101", "890403", "890703", "997105"]'::jsonb,
       'transversal', 'Codigos permitidos para ODONTOLOGO en Urgencias (CODIGOS_ODONTOLOGO)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_odontologo_urg');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_excluidos_medico',
       '["230101", "230102", "230201", "230202", "231101", "231201", "232102", "232103", "232201", "232401", "232402", "237102", "237103", "237301", "237302", "237304", "249101", "29116", "29117", "35102", "36101", "37602", "37701", "39360", "861801", "890205", "890403", "890405", "890406", "890408", "890409", "890411", "890412", "890703", "990211", "997105"]'::jsonb,
       'transversal', 'Codigos prohibidos para MEDICO (CODIGOS_EXCLUIDOS_MEDICO)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_excluidos_medico');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'excepciones_bacteriologa',
       '["903883", "904903"]'::jsonb,
       'transversal', 'Codigos exceptuados de la regla de laboratorio de BACTERIOLOGA (EXCEPCIONES_BACTERIOLOGA)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'excepciones_bacteriologa');

INSERT INTO catalogos (key, value, dominio, descripcion, updated_at)
SELECT 'codigos_pyp_higienista',
       '["990212", "997002", "997106", "997107", "997301", "P0000011"]'::jsonb,
       'transversal', 'Codigos PYP que puede usar HIGIENISTA (PYP_CODES_HIGIENISTA)', now()
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_pyp_higienista');

-- ---------------------------------------------------------------------------
-- Defensive bridge DDL (table created by 023; repeated here so this file is
-- safe to review/apply even if 023 was skipped in a partial chain)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regla_dominios (
    regla_id INTEGER NOT NULL REFERENCES reglas(id) ON DELETE CASCADE,
    dominio VARCHAR(50) NOT NULL,
    PRIMARY KEY (regla_id, dominio)
);

CREATE INDEX IF NOT EXISTS ix_regla_dominios_dominio
    ON regla_dominios (dominio, regla_id);

-- ===========================================================================
-- 1. profesional_urg_trabajadora_social -> profesional_trabajadora_social
-- Bridge: AND(cat_in(prof), NOT(cat_in(codigo))) — 4 conditions, no eq guard
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_trabajadora_social', dominio = 'hospitalizacion',
    descripcion = 'TRABAJADORA SOCIAL con codigo no permitido en Hospitalización (solo 890409, 37701)',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_trabajadora_social' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_trabajadora_social' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_trabajadora_social',
    'TRABAJADORA SOCIAL con codigo no permitido en Hospitalización (solo 890409, 37701)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_trabajadora_social' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_trabajadora_social' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_trabajadora_social' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_trabajadora_social' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_trabajadora_social"', 1
FROM reglas r WHERE r.nombre = 'profesional_trabajadora_social' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'composite', 'NOT', NULL, NULL, 2
FROM reglas r WHERE r.nombre = 'profesional_trabajadora_social' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'NOT' AND c2.orden = 2
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'NOT' AND c.orden = 2),
       'atomic', 'cat_in', 'invoice.codigo', '"codigos_trabajadora_social"', 0
FROM reglas r WHERE r.nombre = 'profesional_trabajadora_social' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'NOT' AND c0.orden = 2)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_trabajadora_social' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_trabajadora_social' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');

-- ===========================================================================
-- 2. profesional_urg_psicologa -> profesional_psicologa
-- Bridge: AND(cat_in(prof), NOT(cat_in(codigo))) — 4 conditions, no eq guard
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_psicologa', dominio = 'hospitalizacion',
    descripcion = 'PSICOLOGA con codigo no permitido en Hospitalización (solo 890408, 35102)',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_psicologa' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_psicologa' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_psicologa',
    'PSICOLOGA con codigo no permitido en Hospitalización (solo 890408, 35102)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_psicologa' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_psicologa' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_psicologa' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_psicologa' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_psicologa"', 1
FROM reglas r WHERE r.nombre = 'profesional_psicologa' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'composite', 'NOT', NULL, NULL, 2
FROM reglas r WHERE r.nombre = 'profesional_psicologa' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'NOT' AND c2.orden = 2
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'NOT' AND c.orden = 2),
       'atomic', 'cat_in', 'invoice.codigo', '"codigos_psicologa"', 0
FROM reglas r WHERE r.nombre = 'profesional_psicologa' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'NOT' AND c0.orden = 2)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_psicologa' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_psicologa' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');

-- ===========================================================================
-- 3. profesional_urg_nutricionista -> profesional_nutricionista
-- Bridge: AND(cat_in(prof), NOT(cat_in(codigo))) — 4 conditions, no eq guard
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_nutricionista', dominio = 'hospitalizacion',
    descripcion = 'NUTRICIONISTA con codigo no permitido en Hospitalización (solo 890406, 37602)',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_nutricionista' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_nutricionista' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_nutricionista',
    'NUTRICIONISTA con codigo no permitido en Hospitalización (solo 890406, 37602)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_nutricionista' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_nutricionista' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_nutricionista' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_nutricionista' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_nutricionista"', 1
FROM reglas r WHERE r.nombre = 'profesional_nutricionista' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'composite', 'NOT', NULL, NULL, 2
FROM reglas r WHERE r.nombre = 'profesional_nutricionista' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'NOT' AND c2.orden = 2
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'NOT' AND c.orden = 2),
       'atomic', 'cat_in', 'invoice.codigo', '"codigos_nutricionista"', 0
FROM reglas r WHERE r.nombre = 'profesional_nutricionista' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'NOT' AND c0.orden = 2)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_nutricionista' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_nutricionista' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');

-- ===========================================================================
-- 4. profesional_urg_fisioterapeuta -> profesional_fisioterapeuta
-- Bridge: AND(cat_in(prof), NOT(cat_in(codigo))) — 4 conditions, no eq guard
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_fisioterapeuta', dominio = 'hospitalizacion',
    descripcion = 'FISIOTERAPEUTA con codigo no permitido en Hospitalización (solo 890412, 890411, 29117)',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_fisioterapeuta' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_fisioterapeuta' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_fisioterapeuta',
    'FISIOTERAPEUTA con codigo no permitido en Hospitalización (solo 890412, 890411, 29117)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_fisioterapeuta' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_fisioterapeuta' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_fisioterapeuta' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_fisioterapeuta' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_fisioterapeuta"', 1
FROM reglas r WHERE r.nombre = 'profesional_fisioterapeuta' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'composite', 'NOT', NULL, NULL, 2
FROM reglas r WHERE r.nombre = 'profesional_fisioterapeuta' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'NOT' AND c2.orden = 2
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'NOT' AND c.orden = 2),
       'atomic', 'cat_in', 'invoice.codigo', '"codigos_fisioterapeuta"', 0
FROM reglas r WHERE r.nombre = 'profesional_fisioterapeuta' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'NOT' AND c0.orden = 2)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_fisioterapeuta' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_fisioterapeuta' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');

-- ===========================================================================
-- 5. profesional_urg_jefe_enfermeria -> profesional_jefe_enfermeria
-- Bridge: AND(cat_in(prof), NOT(cat_in(codigo))) — 4 conditions, no eq guard
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_jefe_enfermeria', dominio = 'hospitalizacion',
    descripcion = 'JEFE ENFERMERIA con codigo no permitido en Hospitalización (solo 861801, 890205, 890405, 990211, 29116, 39360)',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_jefe_enfermeria' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_jefe_enfermeria' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_jefe_enfermeria',
    'JEFE ENFERMERIA con codigo no permitido en Hospitalización (solo 861801, 890205, 890405, 990211, 29116, 39360)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_jefe_enfermeria' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_jefe_enfermeria' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_jefe_enfermeria' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_jefe_enfermeria' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_jefe_enfermeria"', 1
FROM reglas r WHERE r.nombre = 'profesional_jefe_enfermeria' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'composite', 'NOT', NULL, NULL, 2
FROM reglas r WHERE r.nombre = 'profesional_jefe_enfermeria' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'NOT' AND c2.orden = 2
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'NOT' AND c.orden = 2),
       'atomic', 'cat_in', 'invoice.codigo', '"codigos_jefe_enfermeria"', 0
FROM reglas r WHERE r.nombre = 'profesional_jefe_enfermeria' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'NOT' AND c0.orden = 2)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_jefe_enfermeria' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_jefe_enfermeria' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');

-- ===========================================================================
-- 6. profesional_urg_odontologo -> profesional_odontologo
-- Bridge: AND(cat_in(prof), NOT(cat_in(codigo))) — 4 conditions, no eq guard
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_odontologo', dominio = 'hospitalizacion',
    descripcion = 'ODONTOLOGO con codigo no permitido en Hospitalización (solo codigos de CODIGOS_ODONTOLOGO)',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_odontologo' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_odontologo' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_odontologo',
    'ODONTOLOGO con codigo no permitido en Hospitalización (solo codigos de CODIGOS_ODONTOLOGO)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_odontologo' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_odontologo' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_odontologo' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_odontologo' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_odontologo"', 1
FROM reglas r WHERE r.nombre = 'profesional_odontologo' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'composite', 'NOT', NULL, NULL, 2
FROM reglas r WHERE r.nombre = 'profesional_odontologo' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'NOT' AND c2.orden = 2
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'NOT' AND c.orden = 2),
       'atomic', 'cat_in', 'invoice.codigo', '"codigos_odontologo_urg"', 0
FROM reglas r WHERE r.nombre = 'profesional_odontologo' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'NOT' AND c0.orden = 2)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_odontologo' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_odontologo' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');

-- ===========================================================================
-- 7. profesional_urg_medico_excluido -> profesional_medico_excluido
-- Bridge: AND(cat_in(prof), cat_in(codigos_excluidos)) — 3 conditions,
-- positive match, no eq guard
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_medico_excluido', dominio = 'hospitalizacion',
    descripcion = 'MEDICO con codigo reservado a otro tipo de profesional en Hospitalización',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_medico_excluido' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_medico_excluido' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_medico_excluido',
    'MEDICO con codigo reservado a otro tipo de profesional en Hospitalización',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_medico_excluido' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_medico_excluido' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_medico_excluido' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_medico_excluido' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_medico"', 1
FROM reglas r WHERE r.nombre = 'profesional_medico_excluido' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo', '"codigos_excluidos_medico"', 2
FROM reglas r WHERE r.nombre = 'profesional_medico_excluido' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_medico_excluido' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_medico_excluido' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');

-- ===========================================================================
-- 8. profesional_urg_bacteriologa_lab -> profesional_bacteriologa_lab
-- Bridge: AND(cat_in(prof), NOT(AND(tipo_lab, lab=Si)), NOT(excepciones))
-- — 8 conditions, no eq guard
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_bacteriologa_lab', dominio = 'hospitalizacion',
    descripcion = 'BACTERIOLOGA sin Codigo Tipo 02/05 + Laboratorio Si en Hospitalización (salvo 904903, 903883)',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_bacteriologa_lab' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_bacteriologa_lab' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_bacteriologa_lab',
    'BACTERIOLOGA sin Codigo Tipo 02/05 + Laboratorio Si en Hospitalización (salvo 904903, 903883)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_bacteriologa_lab' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_bacteriologa_lab' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_bacteriologa_lab' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_bacteriologa_lab' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_bacteriologa"', 1
FROM reglas r WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'composite', 'NOT', NULL, NULL, 2
FROM reglas r WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'NOT' AND c2.orden = 2
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'NOT' AND c.orden = 2),
       'composite', 'AND', NULL, NULL, 0
FROM reglas r WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'NOT' AND c0.orden = 2)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'AND' AND c2.padre_id IS NOT NULL
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'AND' AND c.padre_id IS NOT NULL),
       'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', '"codigos_tipo_procedimiento_laboratorio"', 0
FROM reglas r WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'AND' AND c0.padre_id IS NOT NULL)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_tipo_procedimiento'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'AND' AND c.padre_id IS NOT NULL),
       'atomic', 'eq', 'invoice.laboratorio', '"Si"', 1
FROM reglas r WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'AND' AND c0.padre_id IS NOT NULL)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'eq' AND c2.fuente_datos = 'invoice.laboratorio'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'composite', 'NOT', NULL, NULL, 3
FROM reglas r WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'NOT' AND c2.orden = 3
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.operador = 'NOT' AND c.orden = 3),
       'atomic', 'cat_in', 'invoice.codigo', '"excepciones_bacteriologa"', 0
FROM reglas r WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.operador = 'NOT' AND c0.orden = 3)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_bacteriologa_lab' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');

-- ===========================================================================
-- 9. profesional_urg_medico_lab -> profesional_medico_lab
-- Bridge: AND(cat_in(prof), cat_in(tipo_lab), eq(lab=Si)) — 4 conditions,
-- no eq guard on tipo factura
-- ===========================================================================
UPDATE reglas SET nombre = 'profesional_medico_lab', dominio = 'hospitalizacion',
    descripcion = 'MEDICO con codigo de Laboratorio en Hospitalización (Tipo 02/05 + Lab Si, reservado a BACTERIOLOGA)',
    estado = 'active', activo = true, grupo_error = 'Profesionales'
WHERE nombre = 'profesional_urg_medico_lab' AND version = 1
  AND NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_medico_lab' AND version = 1);

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_medico_lab',
    'MEDICO con codigo de Laboratorio en Hospitalización (Tipo 02/05 + Lab Si, reservado a BACTERIOLOGA)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
, 'Profesionales', 'codigo_profesional,procedimiento', 'Cód: {codigo_profesional}', NULL)
ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales';

DELETE FROM condiciones
WHERE regla_id IN (SELECT id FROM reglas WHERE nombre = 'profesional_medico_lab' AND version = 1)
  AND EXISTS (
    SELECT 1 FROM condiciones g
    WHERE g.regla_id = condiciones.regla_id
      AND g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT (SELECT id FROM reglas WHERE nombre = 'profesional_medico_lab' AND version = 1), NULL, 'composite', 'AND', NULL, NULL, 0
WHERE EXISTS (SELECT 1 FROM reglas WHERE nombre = 'profesional_medico_lab' AND version = 1)
  AND NOT EXISTS (
    SELECT 1 FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'profesional_medico_lab' AND version = 1)
      AND padre_id IS NULL AND operador = 'AND'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_medico"', 1
FROM reglas r WHERE r.nombre = 'profesional_medico_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_profesional'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', '"codigos_tipo_procedimiento_laboratorio"', 2
FROM reglas r WHERE r.nombre = 'profesional_medico_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'cat_in' AND c2.fuente_datos = 'invoice.codigo_tipo_procedimiento'
  );

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id,
       (SELECT c.id FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NULL AND c.operador = 'AND'),
       'atomic', 'eq', 'invoice.laboratorio', '"Si"', 3
FROM reglas r WHERE r.nombre = 'profesional_medico_lab' AND r.version = 1
  AND EXISTS (SELECT 1 FROM condiciones c0 WHERE c0.regla_id = r.id AND c0.padre_id IS NULL AND c0.operador = 'AND')
  AND NOT EXISTS (
    SELECT 1 FROM condiciones c2 WHERE c2.regla_id = r.id AND c2.operador = 'eq' AND c2.fuente_datos = 'invoice.laboratorio'
  );

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'hospitalizacion' FROM reglas r
WHERE r.nombre = 'profesional_medico_lab' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'hospitalizacion');

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'urgencias' FROM reglas r
WHERE r.nombre = 'profesional_medico_lab' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'urgencias');
