-- =============================================================================
-- Migration Engine F13: Catálogos de centro de costo
-- Seeds constant sets into catalogos table for cat_in evaluator lookups.
-- All values extracted from Python constants (app/constants/urgencias.py,
-- app/constants/intramural.py) — must match EXACTLY.
-- =============================================================================

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'codigos_exceptuados',
       '["194901","23105","23116","232200","232201","25142AFINA","90123501","901325","90385901","90386401","903883","9038831","904903","906230","906836"]'::jsonb,
       'transversal',
       'Códigos exceptuados de reglas de centro de costo (CODIGOS_EXCEPTUADOS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_exceptuados');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centro_costo_pyp',
       '["990211","890205","890405","861801","39360","29116"]'::jsonb,
       'transversal',
       'Códigos que requieren centro = PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN (CODIGOS_PYP_URGENCIAS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centro_costo_pyp');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centro_costo_quirofano',
       '["735301","90DS02","512002","39220"]'::jsonb,
       'transversal',
       'Códigos que requieren centro = QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO (CODIGOS_QUIROFANO_URGENCIAS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centro_costo_quirofano');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centro_costo_hospitalizacion',
       '["890601H","39133"]'::jsonb,
       'transversal',
       'Códigos que requieren centro = HOSPITALIZACIÓN - ESTANCIA GENERAL (CODIGOS_HOSPITALIZACION_ESTANCIA)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centro_costo_hospitalizacion');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centros_costo_validos_urgencias',
       '["URGENCIAS","APOYO TERAPEUTICO-FARMACIA E INSUMOS.","APOYO DIAGNOSTICO-LABORATOR CLINICO","PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN","HOSPITALIZACIÓN - ESTANCIA GENERAL","APOYO DIAGNOSTICO-IMAGENOLOGIA","TRASLADOS","QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"]'::jsonb,
       'urgencias',
       'Centros de costo válidos para Urgencias (CENTROS_COSTO_VALIDOS_URGENCIAS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_validos_urgencias');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centros_costo_pyp_intramural',
       '["SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION","SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION.","SERVICIOS AMBULATORIOS- PROMOCION/PREVENCION"]'::jsonb,
       'intramural',
       'Centros de costo PyP válidos en Intramural (CENTROS_COSTO_PYP_INTRAMURAL)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_pyp_intramural');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'codigos_excluidos_vacunacion',
       '["906249PR","906249"]'::jsonb,
       'intramural',
       'Códigos excluidos de la regla de vacunación (CODIGOS_EXCLUIDOS_VACUNACION)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_excluidos_vacunacion');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'codigos_exceptuados_ambulatorio',
       '["735301","861101"]'::jsonb,
       'intramural',
       'Códigos exceptuados de REGLA7 ambulatorio (CODIGOS_EXCEPTUADOS_AMBULATORIO)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_exceptuados_ambulatorio');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'codigos_exceptuados_responsable_urgencias',
       '["735301"]'::jsonb,
       'intramural',
       'Códigos exceptuados de REGLA_RESPONSABLE_URGENCIAS (CODIGOS_EXCEPTUADOS_RESPONSABLE_URGENCIAS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_exceptuados_responsable_urgencias');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centros_costo_laboratorio_validos',
       '["APOYO DIAGNOSTICO-LABORATOR CLINICO","APOYO DIAGNOSTICO-LABORATOR CLINICO."]'::jsonb,
       'intramural',
       'Centros de costo válidos para laboratorio clínico (CENTROS_COSTO_LABORATORIO_VALIDOS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_laboratorio_validos');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'codigos_tipo_procedimiento_ambulatorio',
       '["03","04"]'::jsonb,
       'intramural',
       'Códigos tipo procedimiento que exigen SERVICIOS AMBULATORIOS (CODIGOS_TIPO_PROCEDIMIENTO_AMBULATORIO)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_tipo_procedimiento_ambulatorio');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'codigos_tipo_procedimiento_laboratorio',
       '["02","05"]'::jsonb,
       'intramural',
       'Códigos tipo procedimiento para laboratorio clínico (CODIGOS_TIPO_PROCEDIMIENTO_LABORATORIO)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'codigos_tipo_procedimiento_laboratorio');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'centros_costo_validos_intramural',
       '["APOYO DIAGNOSTICO-LABORATOR CLINICO","APOYO DIAGNOSTICO-IMAGENOLOGIA","APOYO DIAGNOSTICO-LABORATOR CLINICO.","SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS","SALUD PUBLICA-VACUNACION  REGULAR","APOYO TERAPEUTICO-FARMACIA E INSUMOS.","HOSPITALIZACIÓN - ESTANCIA GENERAL","QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO","TRASLADOS","SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION","SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION.","SERVICIOS AMBULATORIOS- PROMOCION/PREVENCION","URGENCIAS"]'::jsonb,
       'intramural',
       'Centros de costo válidos en Intramural (INTRAMURAL_CENTROS_COSTO_VALIDOS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'centros_costo_validos_intramural');

INSERT INTO catalogos (key, value, dominio, descripcion)
SELECT 'facturadores_urgencias',
       '["ARIAS CULCHA ANGIE CAROLINA","ESPAÑA DIAZ LORENY ALEJANDRA","MEZA FERNANDEZ CARLOS OMAR","PAEZ YULIETH DANIELA"]'::jsonb,
       'urgencias',
       'Facturadores de Urgencias (FACTURADORES_URGENCIAS)'
WHERE NOT EXISTS (SELECT 1 FROM catalogos WHERE key = 'facturadores_urgencias');
