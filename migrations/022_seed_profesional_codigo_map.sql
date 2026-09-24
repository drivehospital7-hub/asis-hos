-- ===========================================================================
-- 022: profesional -> codigos permitidos al motor (Approach A: datos puros)
-- ===========================================================================
-- Lleva al motor el mapeo "tipo de profesional -> codigos de procedimiento
-- permitidos" que vivia solo en codigo legacy:
--   app/services/urgencias/profesionales_urgencias.py (+ constants/urgencias.py)
--   app/services/odontologia/profesionales.py       (+ constants/odontologia.py)
--   app/services/equipos_basicos/profesionales.py   (+ constants/equipos_basicos.py)
--
-- Diseno: catalogos de lista plana por tipo (cat_in solo acepta listas) +
-- una regla row AND por (dominio, tipo). Sin codigo nuevo.
--
-- Decisiones de producto (2026-09-22):
--   - Alcance EXTENDIDO a Hospitalizacion: reusa el mapeo de Urgencias
--     (el legacy solo validaba existencia ahi). Reglas profesional_hosp_*.
--   - Laboratorio con eq "Si" (precedente 012/013/015/016, case-sensitive).
--   - Sin guards de vacio (precedente reglas profesional_*_valido ya en
--     motor: el legacy salteaba vacios, el motor los marca).
--   - Los catalogos por tipo salen de los dicts PROFESIONALES_* (unica
--     fuente del tipo). NOTA: el dict de urgencias (36 codigos) != catalogo
--     profesionales_urgencias (23 codigos); esa discrepancia de existencia
--     no se toca aqui.
--
-- Reusa: catalogo codigos_tipo_procedimiento_laboratorio (["02","05"]).
--
-- 22 reglas (prioridad 40, severidad error, grupo 'Profesionales'):
--   urgencias       9 (6 por tipo + medico_excluido + bacteriologa_lab + medico_lab)
--   hospitalizacion 9 (espejo, filtro 'Hospitalización')
--   odontologia     2 (higienista, odontologo_pyp; sin filtro de tipo factura,
--                      igual que el legacy y que profesional_odontologia_valido)
--   equipos_basicos 2 (espejo odonto)
-- 21 catalogos nuevos. Total condiciones: 114.
-- Idempotente: ON CONFLICT (nombre, version) + DELETE+rebuild, sin BEGIN/COMMIT.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- Catalogos: profesionales por tipo (12)
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

-- ---------------------------------------------------------------------------
-- Catalogos: codigos permitidos por tipo (9, dominio transversal)
-- ---------------------------------------------------------------------------
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

-- ===========================================================================
-- URGENCIAS (9): AND(eq(tipo=Urgencias), cat_in(prof), <chequeo codigo>)
-- ===========================================================================

-- 1. TRABAJADORA SOCIAL solo 890409/37701
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_trabajadora_social',
    'TRABAJADORA SOCIAL con codigo no permitido en Urgencias (solo 890409, 37701)',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_trabajadora_social' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_trabajadora_social"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_trabajadora_social"', 0);
END $$;

-- 2. PSICOLOGA solo 890408/35102
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_psicologa',
    'PSICOLOGA con codigo no permitido en Urgencias (solo 890408, 35102)',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_psicologa' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_psicologa"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_psicologa"', 0);
END $$;

-- 3. NUTRICIONISTA solo 890406/37602
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_nutricionista',
    'NUTRICIONISTA con codigo no permitido en Urgencias (solo 890406, 37602)',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_nutricionista' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_nutricionista"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_nutricionista"', 0);
END $$;

-- 4. FISIOTERAPEUTA solo 890412/890411/29117
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_fisioterapeuta',
    'FISIOTERAPEUTA con codigo no permitido en Urgencias (solo 890412, 890411, 29117)',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_fisioterapeuta' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_fisioterapeuta"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_fisioterapeuta"', 0);
END $$;

-- 5. JEFE ENFERMERIA solo sus 6 codigos
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_jefe_enfermeria',
    'JEFE ENFERMERIA con codigo no permitido en Urgencias (solo 861801, 890205, 890405, 990211, 29116, 39360)',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_jefe_enfermeria' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_jefe_enfermeria"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_jefe_enfermeria"', 0);
END $$;

-- 6. ODONTOLOGO solo sus 21 codigos
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_odontologo',
    'ODONTOLOGO con codigo no permitido en Urgencias (solo codigos de CODIGOS_ODONTOLOGO)',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_odontologo' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_odontologo"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_odontologo_urg"', 0);
END $$;

-- 7. MEDICO con codigo reservado a otro tipo (match positivo)
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_medico_excluido',
    'MEDICO con codigo reservado a otro tipo de profesional en Urgencias',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_medico_excluido' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_medico"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_excluidos_medico"', 2);
END $$;

-- 8. BACTERIOLOGA sin Tipo 02/05 + Laboratorio Si (salvo excepciones)
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_bacteriologa_lab',
    'BACTERIOLOGA sin Codigo Tipo 02/05 + Laboratorio Si en Urgencias (salvo 904903, 903883)',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_lab_id integer;
    and_lab_id integer;
    not_exc_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_bacteriologa_lab' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_bacteriologa"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_lab_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_lab_id, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO and_lab_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, and_lab_id, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', '"codigos_tipo_procedimiento_laboratorio"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, and_lab_id, 'atomic', 'eq', 'invoice.laboratorio', '"Si"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 3) RETURNING id INTO not_exc_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_exc_id, 'atomic', 'cat_in', 'invoice.codigo', '"excepciones_bacteriologa"', 0);
END $$;

-- 9. MEDICO con codigo de laboratorio (Tipo 02/05 + Lab Si, reservado BACTERIOLOGA)
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_urg_medico_lab',
    'MEDICO con codigo de Laboratorio en Urgencias (Tipo 02/05 + Lab Si, reservado a BACTERIOLOGA)',
    'urgencias', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_urg_medico_lab' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_medico"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', '"codigos_tipo_procedimiento_laboratorio"', 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.laboratorio', '"Si"', 3);
END $$;

-- ===========================================================================
-- HOSPITALIZACION (9): espejo de Urgencias con filtro 'Hospitalización'.
-- Extension 022: el legacy solo validaba existencia en este dominio.
-- Reusa los mismos catalogos (mapeo de Urgencias).
-- ===========================================================================

-- 10. TRABAJADORA SOCIAL
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_trabajadora_social',
    'TRABAJADORA SOCIAL con codigo no permitido en Hospitalización (solo 890409, 37701)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_trabajadora_social' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_trabajadora_social"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_trabajadora_social"', 0);
END $$;

-- 11. PSICOLOGA
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_psicologa',
    'PSICOLOGA con codigo no permitido en Hospitalización (solo 890408, 35102)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_psicologa' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_psicologa"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_psicologa"', 0);
END $$;

-- 12. NUTRICIONISTA
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_nutricionista',
    'NUTRICIONISTA con codigo no permitido en Hospitalización (solo 890406, 37602)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_nutricionista' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_nutricionista"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_nutricionista"', 0);
END $$;

-- 13. FISIOTERAPEUTA
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_fisioterapeuta',
    'FISIOTERAPEUTA con codigo no permitido en Hospitalización (solo 890412, 890411, 29117)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_fisioterapeuta' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_fisioterapeuta"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_fisioterapeuta"', 0);
END $$;

-- 14. JEFE ENFERMERIA
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_jefe_enfermeria',
    'JEFE ENFERMERIA con codigo no permitido en Hospitalización (solo 861801, 890205, 890405, 990211, 29116, 39360)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_jefe_enfermeria' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_jefe_enfermeria"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_jefe_enfermeria"', 0);
END $$;

-- 15. ODONTOLOGO
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_odontologo',
    'ODONTOLOGO con codigo no permitido en Hospitalización (solo codigos de CODIGOS_ODONTOLOGO)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_odontologo' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_odontologo"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_odontologo_urg"', 0);
END $$;

-- 16. MEDICO con codigo reservado
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_medico_excluido',
    'MEDICO con codigo reservado a otro tipo de profesional en Hospitalización',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_medico_excluido' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_medico"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_excluidos_medico"', 2);
END $$;

-- 17. BACTERIOLOGA sin laboratorio
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_bacteriologa_lab',
    'BACTERIOLOGA sin Codigo Tipo 02/05 + Laboratorio Si en Hospitalización (salvo 904903, 903883)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_lab_id integer;
    and_lab_id integer;
    not_exc_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_bacteriologa_lab' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_bacteriologa"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_lab_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_lab_id, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO and_lab_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, and_lab_id, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', '"codigos_tipo_procedimiento_laboratorio"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, and_lab_id, 'atomic', 'eq', 'invoice.laboratorio', '"Si"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 3) RETURNING id INTO not_exc_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_exc_id, 'atomic', 'cat_in', 'invoice.codigo', '"excepciones_bacteriologa"', 0);
END $$;

-- 18. MEDICO con codigo de laboratorio
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_hosp_medico_lab',
    'MEDICO con codigo de Laboratorio en Hospitalización (Tipo 02/05 + Lab Si, reservado a BACTERIOLOGA)',
    'hospitalizacion', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_hosp_medico_lab' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Hospitalización"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_urgencias_medico"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_tipo_procedimiento', '"codigos_tipo_procedimiento_laboratorio"', 2);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'eq', 'invoice.laboratorio', '"Si"', 3);
END $$;

-- ===========================================================================
-- ODONTOLOGIA (2): sin filtro de tipo factura (igual que el legacy y que
-- profesional_odontologia_valido).
-- ===========================================================================

-- 19. HIGIENISTA solo codigos PYP
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_odon_higienista',
    'HIGIENISTA con codigo no PYP en Odontología (solo codigos de PYP_CODES_HIGIENISTA)',
    'odontologia', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_odon_higienista' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_odontologia_higienista"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_pyp_higienista"', 0);
END $$;

-- 20. ODONTOLOGO con codigo PYP (salvo P0000011)
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_odon_odontologo_pyp',
    'ODONTOLOGO con codigo PYP en Odontología (no puede usar PYP, salvo P0000011)',
    'odontologia', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_odon_odontologo_pyp' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_odontologia_odontologo"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_pyp_higienista"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'eq', 'invoice.codigo', '"P0000011"', 0);
END $$;

-- ===========================================================================
-- EQUIPOS BASICOS (2): espejo de Odontologia.
-- ===========================================================================

-- 21. HIGIENISTA solo codigos PYP
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_eqb_higienista',
    'HIGIENISTA con codigo no PYP en Equipos Básicos (solo codigos de PYP_CODES_HIGIENISTA)',
    'equipos_basicos', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_eqb_higienista' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_equipos_basicos_higienista"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 1) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_pyp_higienista"', 0);
END $$;

-- 22. ODONTOLOGO con codigo PYP (salvo P0000011)
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'profesional_eqb_odontologo_pyp',
    'ODONTOLOGO con codigo PYP en Equipos Básicos (no puede usar PYP, salvo P0000011)',
    'equipos_basicos', 'active', 1, 40, 'error', true, NULL
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
    rid integer;
    root_id integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'profesional_eqb_odontologo_pyp' AND version = 1;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'AND', NULL, NULL, 0) RETURNING id INTO root_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo_profesional', '"profesionales_equipos_basicos_odontologo"', 0);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'atomic', 'cat_in', 'invoice.codigo', '"codigos_pyp_higienista"', 1);

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, root_id, 'composite', 'NOT', NULL, NULL, 2) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'eq', 'invoice.codigo', '"P0000011"', 0);
END $$;
