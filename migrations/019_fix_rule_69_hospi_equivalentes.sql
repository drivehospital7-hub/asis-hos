-- =============================================================================
-- 019_fix_rule_69_hospi_equivalentes.sql
--
-- Fixes rule #69 hospi_equivalentes_group_fac (dominio='hospitalizacion').
-- The rule was INVERTED: MATCH (error) when the invoice CONTAINED 38114 or
-- 129B02. Correct semantics (user-confirmed): ERROR when the invoice brings
-- NEITHER code — at least one of the two is mandatory at invoice level.
--
-- Changes (idempotent by-name mechanism, same as 010/011/012/013/014):
--   1. parametros: add filter_field=tipo_factura_descripcion /
--      filter_value=Hospitalización + explicit collect_set aggregation
--      (hermanas pattern from 010: hosp_codigos_oblig_mayor24h/menor24h).
--      Without the filter, Urgencias invoices leaked in (prod evidence:
--      123 MATCH split 74 Urgencias vs 49 Hospitalización).
--   2. Condition tree rewritten to error-when-missing with OR semantics:
--      NOT[set_intersects(invoice.collect_set_codigo, ["38114","129B02"])].
--      set_intersects (not set_contains_all) because ONE of the two suffices;
--      same presence operator the hermanas use (hosp_codigos_prohibidos in
--      010, sala_obs_check_set in 014), negated for absence.
--
-- Identity is (nombre, version=1); live row IDs are never hardcoded. If the
-- rule is absent (dev/test DBs where it was never seeded), it is created
-- with the corrected shape so all environments converge.
-- grupo_error is deliberately left untouched (bucket routing already works;
-- DO UPDATE below excludes it). prioridad/severidad are also preserved.
-- Run through: python run_migrations.py (version tracked in schema_migrations
-- by the runner).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema guards (same as 010/011/012/013/014): widen condiciones.operador,
-- normalize condiciones.valor_esperado to jsonb. Guarded; rerun-safe.
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
-- hospi_equivalentes_group_fac (rule #69, hospitalizacion, group rule)
-- Group rule: Hospitalización invoice missing BOTH 38114 and 129B02.
-- ===========================================================================
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros, grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template)
VALUES (
    'hospi_equivalentes_group_fac',
    'Hospitalización sin código 38114 ni 129B02 a nivel factura (al menos uno es obligatorio)',
    'hospitalizacion', 'active', 1, 5, 'error', true,
    '[{"group_by": "numero_factura", "filter_field": "tipo_factura_descripcion", "filter_value": "Hospitalización", "aggregations": [{"function": "collect_set", "field": "codigo", "target": "collect_set_codigo"}]}]'::jsonb
, 'Cups-Equivalentes', 'codigo,procedimiento', NULL, NULL)
ON CONFLICT (nombre, version) DO UPDATE SET descripcion = EXCLUDED.descripcion,
    dominio = EXCLUDED.dominio,
    estado = 'active',
    activo = true,
    parametros = EXCLUDED.parametros,
    detalle_a_campo = EXCLUDED.detalle_a_campo,
    detalle_b_campo = EXCLUDED.detalle_b_campo,
    descripcion_template = EXCLUDED.descripcion_template;

DO $$
DECLARE
    rid integer;
    not_id integer;
BEGIN
    SELECT id INTO rid FROM reglas WHERE nombre = 'hospi_equivalentes_group_fac' AND version = 1;
    IF rid IS NULL THEN
        RAISE NOTICE 'hospi_equivalentes_group_fac missing after upsert; skipping tree rebuild';
        RETURN;
    END IF;
    DELETE FROM condiciones WHERE regla_id = rid;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, NULL, 'composite', 'NOT', NULL, NULL, 0) RETURNING id INTO not_id;

    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (rid, not_id, 'atomic', 'set_intersects', 'invoice.collect_set_codigo', '["38114", "129B02"]', 0);
END $$;

-- ---------------------------------------------------------------------------
-- Lineage: seeded v1 row is its own base (same as 009/011/012/013/014).
-- ---------------------------------------------------------------------------
UPDATE reglas SET rule_base_id = id
WHERE nombre = 'hospi_equivalentes_group_fac'
  AND version = 1
  AND rule_base_id IS NULL;
