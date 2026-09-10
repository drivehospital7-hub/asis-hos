-- =============================================================================
-- 017_grupo_error_mapping.sql
--
-- Adds rule-declared /procesar grouping columns to reglas (nullable-first
-- rollout) and backfills grupo_error for all 55 seeded rules (010-016).
--
-- Rollout: nullable TEXT, no NOT NULL yet (deferred until the
-- cups_sin_contrato #27/#39 dedup lands). Re-runnable: DDL uses
-- IF NOT EXISTS and every backfill UPDATE is keyed by (nombre, version).
-- Does NOT touch evidencias / resultados_auditoria.
-- =============================================================================

ALTER TABLE reglas
    ADD COLUMN IF NOT EXISTS grupo_error TEXT NULL,
    ADD COLUMN IF NOT EXISTS detalle_a_campo TEXT NULL,
    ADD COLUMN IF NOT EXISTS detalle_b_campo TEXT NULL,
    ADD COLUMN IF NOT EXISTS descripcion_template TEXT NULL;

-- ---------------------------------------------------------------------------
-- Backfill grupo_error (one UPDATE per rule, keyed by nombre + version = 1)
-- ---------------------------------------------------------------------------

-- Tipo Identificacion / Edad (7 tipo_documento_edad_* rules)
UPDATE reglas SET grupo_error = 'Tipo Identificacion / Edad' WHERE nombre = 'tipo_documento_edad_menor_7' AND version = 1;
UPDATE reglas SET grupo_error = 'Tipo Identificacion / Edad' WHERE nombre = 'tipo_documento_edad_mayor_18' AND version = 1;
UPDATE reglas SET grupo_error = 'Tipo Identificacion / Edad' WHERE nombre = 'tipo_documento_edad_7_17' AND version = 1;
UPDATE reglas SET grupo_error = 'Tipo Identificacion / Edad' WHERE nombre = 'tipo_documento_edad_as_menor' AND version = 1;
UPDATE reglas SET grupo_error = 'Tipo Identificacion / Edad' WHERE nombre = 'tipo_documento_edad_ms_mayor' AND version = 1;
UPDATE reglas SET grupo_error = 'Tipo Identificacion / Edad' WHERE nombre = 'tipo_documento_edad_cn_invalido' AND version = 1;
UPDATE reglas SET grupo_error = 'Tipo Identificacion / Edad' WHERE nombre = 'tipo_documento_edad_ce_invalido' AND version = 1;

-- Codigo-Entidad-vs-Afiliacion (3 rules)
UPDATE reglas SET grupo_error = 'Codigo-Entidad-vs-Afiliacion' WHERE nombre = 'tipo_id_requiere_entidad_86000' AND version = 1;
UPDATE reglas SET grupo_error = 'Codigo-Entidad-vs-Afiliacion' WHERE nombre = 'entidad_86000_requiere_as_ms' AND version = 1;
UPDATE reglas SET grupo_error = 'Codigo-Entidad-vs-Afiliacion' WHERE nombre = 'codigo_entidad' AND version = 1;

-- Duplicados-Farmacia (3 rules)
UPDATE reglas SET grupo_error = 'Duplicados-Farmacia' WHERE nombre = 'duplicados_farmacia' AND version = 1;
UPDATE reglas SET grupo_error = 'Duplicados-Farmacia' WHERE nombre = 'duplicados_farmacia_v2' AND version = 1;
UPDATE reglas SET grupo_error = 'Duplicados-Farmacia' WHERE nombre = 'detect_duplicados_base' AND version = 1;

-- Cups-Equivalentes (4 rules)
UPDATE reglas SET grupo_error = 'Cups-Equivalentes' WHERE nombre = 'cups_equivalentes' AND version = 1;
UPDATE reglas SET grupo_error = 'Cups-Equivalentes' WHERE nombre = 'sala_observacion_entidad' AND version = 1;
UPDATE reglas SET grupo_error = 'Cups-Equivalentes' WHERE nombre = 'sala_observacion_estancia_prolongada' AND version = 1;
UPDATE reglas SET grupo_error = 'Cups-Equivalentes' WHERE nombre = 'sala_obs_check_set' AND version = 1;

-- Revision-Necesaria (4 rules)
UPDATE reglas SET grupo_error = 'Revision-Necesaria' WHERE nombre = 'revision_entidad_86' AND version = 1;
UPDATE reglas SET grupo_error = 'Revision-Necesaria' WHERE nombre = 'revision_cantidad_urgencias' AND version = 1;
UPDATE reglas SET grupo_error = 'Revision-Necesaria' WHERE nombre = 'revision_cantidad_v2' AND version = 1;
UPDATE reglas SET grupo_error = 'Revision-Necesaria' WHERE nombre = 'revision_cantidad_intramural' AND version = 1;

-- Centros de Costo (7 rules)
UPDATE reglas SET grupo_error = 'Centros de Costo' WHERE nombre = 'centro_costo_odontologia_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'Centros de Costo' WHERE nombre = 'centro_costo_equipos_basicos_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'Centros de Costo' WHERE nombre = 'centro_costo_urgencias_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'Centros de Costo' WHERE nombre = 'centro_costo_urgencias' AND version = 1;
UPDATE reglas SET grupo_error = 'Centros de Costo' WHERE nombre = 'centro_costo_urgencias_cross' AND version = 1;
UPDATE reglas SET grupo_error = 'Centros de Costo' WHERE nombre = 'centro_costo_hospitalizacion_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'Centros de Costo' WHERE nombre = 'centro_costo_intramural_valido' AND version = 1;

-- IDE Contrato (4 rules)
UPDATE reglas SET grupo_error = 'IDE Contrato' WHERE nombre = 'ide_contrato_urgencias_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'IDE Contrato' WHERE nombre = 'ide_contrato_odontologia_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'IDE Contrato' WHERE nombre = 'ide_contrato_hospitalizacion_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'IDE Contrato' WHERE nombre = 'ide_contrato_reverse_urgencias_valido' AND version = 1;

-- Profesionales (4 rules)
UPDATE reglas SET grupo_error = 'Profesionales' WHERE nombre = 'profesional_odontologia_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'Profesionales' WHERE nombre = 'profesional_equipos_validos' AND version = 1;
UPDATE reglas SET grupo_error = 'Profesionales' WHERE nombre = 'profesional_urgencias_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'Profesionales' WHERE nombre = 'profesional_hospitalizacion_valido' AND version = 1;

-- Cantidades (4 rules)
UPDATE reglas SET grupo_error = 'Cantidades' WHERE nombre = 'cantidad_consultas_anomalas' AND version = 1;
UPDATE reglas SET grupo_error = 'Cantidades' WHERE nombre = 'cantidad_general_anomalas' AND version = 1;
UPDATE reglas SET grupo_error = 'Cantidades' WHERE nombre = 'cantidad_pyp_anomalas' AND version = 1;
UPDATE reglas SET grupo_error = 'Cantidades' WHERE nombre = 'cantidades_urgencias' AND version = 1;

-- Cantidades SOAT / Hospitalizacion (3 rules)
UPDATE reglas SET grupo_error = 'Cantidades SOAT' WHERE nombre = 'cantidades_soat_urgencias' AND version = 1;
UPDATE reglas SET grupo_error = 'Cantidades Hospitalización' WHERE nombre = 'cantidades_hospitalizacion' AND version = 1;
UPDATE reglas SET grupo_error = 'Cantidades SOAT Hospitalización' WHERE nombre = 'cantidades_soat_hospitalizacion' AND version = 1;

-- Single-rule plain groups (9 rules)
UPDATE reglas SET grupo_error = 'Decimales' WHERE nombre = 'valores_decimales' AND version = 1;
UPDATE reglas SET grupo_error = 'Tipo Usuario' WHERE nombre = 'tipo_usuario_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'Copago vs Entidad' WHERE nombre = 'copago_entidad_valido' AND version = 1;
UPDATE reglas SET grupo_error = 'Cups Sin Contrato' WHERE nombre = 'cups_sin_contrato' AND version = 1;
UPDATE reglas SET grupo_error = 'MAL CAPITADO' WHERE nombre = 'mal_capitado' AND version = 1;
UPDATE reglas SET grupo_error = 'Ruta Duplicada' WHERE nombre = 'ruta_duplicada' AND version = 1;
UPDATE reglas SET grupo_error = 'Doble Tipo Procedimiento' WHERE nombre = 'doble_tipo_procedimiento' AND version = 1;
UPDATE reglas SET grupo_error = 'Cronograma Bacteriologas' WHERE nombre = 'bacteriologas_cronograma' AND version = 1;
UPDATE reglas SET grupo_error = 'Duplicado ID-Codigo' WHERE nombre = 'duplicado_id_codigo_05' AND version = 1;

-- Codigos Hospitalizacion (3 rules)
UPDATE reglas SET grupo_error = 'Codigos Hospitalizacion' WHERE nombre = 'hosp_codigos_oblig_mayor24h' AND version = 1;
UPDATE reglas SET grupo_error = 'Codigos Hospitalizacion' WHERE nombre = 'hosp_codigos_oblig_menor24h' AND version = 1;
UPDATE reglas SET grupo_error = 'Codigos Hospitalizacion' WHERE nombre = 'hosp_codigos_prohibidos' AND version = 1;
