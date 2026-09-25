-- =============================================================================
-- 025: seed duplicado_id_codigo_02_lab (src seed/migracion-engine/08 verbatim)
-- =============================================================================
-- Content below is seed/migracion-engine/08_duplicado_id_codigo_02_lab.sql
-- verbatim, plus grupo_error 'Duplicado ID-Codigo' on the rule insert and
-- the intramural bridge row. Keeps activo=true from the seed.
--
-- Defensive bridge DDL (table created by 023; repeated here so this file is
-- safe to review/apply even if 023 was skipped in a partial chain).
--
-- PENDING DECISION (reported, not changed): duplicado_id_codigo_05 is
-- reported inactive in prod while this 02_lab sibling ships activo=true
-- (matching its seed). If prod parity requires 02_lab inactive too, that
-- choice belongs to the user in a follow-up change, not to this seed.
--
-- Idempotent, no BEGIN/COMMIT. Portable PG/SQLite: EXISTS + INSERT..SELECT.
-- =============================================================================

CREATE TABLE IF NOT EXISTS regla_dominios (
    regla_id INTEGER NOT NULL REFERENCES reglas(id) ON DELETE CASCADE,
    dominio VARCHAR(50) NOT NULL,
    PRIMARY KEY (regla_id, dominio)
);

CREATE INDEX IF NOT EXISTS ix_regla_dominios_dominio
    ON regla_dominios (dominio, regla_id);

-- =============================================================================
-- Migration Engine F5: duplicado_id_codigo_02_lab
-- Rule: GroupEvaluator — flag facturas where group (ident, codigo, dx)
--       appears >= 4 times for tipo=02 + Laboratorio=Si.
-- Domain: intramural
-- Evaluator: gte (via condition tree)
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, parametros, severidad, activo, grupo_error)
SELECT 'duplicado_id_codigo_02_lab',
       'Duplicados ID+Código para tipo=02+Lab=Si — grupos de (identificacion, codigo, dx_principal) con count >= 4',
       'intramural', 'active', 1, 51,
       '[{"group_by": ["identificacion", "codigo", "codigo_dx_principal"], "filter_field": "codigo_tipo_procedimiento", "filter_value": "02", "aggregations": [{"function": "group_size", "target": "count"}, {"function": "collect_group_keys", "field": "numero_factura", "target": "facturas"}]}]',
       'warning', true, 'Duplicado ID-Codigo'
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'duplicado_id_codigo_02_lab' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'duplicado_id_codigo_02_lab' AND version = 1
);

-- Single atomic condition: gte(count, 4)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'duplicado_id_codigo_02_lab' AND version = 1),
    NULL,
    'atomic',
    'gte',
    'invoice.count',
    '4',
    0
);

INSERT INTO regla_dominios (regla_id, dominio)
SELECT r.id, 'intramural' FROM reglas r
WHERE r.nombre = 'duplicado_id_codigo_02_lab' AND r.version = 1
  AND NOT EXISTS (SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = r.id AND rd.dominio = 'intramural');
