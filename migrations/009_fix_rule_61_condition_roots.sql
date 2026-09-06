-- =============================================================================
-- 009_fix_rule_61_condition_roots.sql
--
-- cups_equivalentes_hospitalizacion must have one OR root. Seed the rule
-- by (nombre, version) when absent (SEMBRAR), then move only its two known
-- loose code conditions (906317 / 906249) under that root, preserving their
-- existing relative order.
--
-- Identity is resolved at runtime via (nombre, version) = 
-- ('cups_equivalentes_hospitalizacion', 1); no literal regla id is used, so
-- the migration works on fresh DBs (new id) and pre-seeded DBs alike.
--
-- Canonical source (read-only SELECT from dev/live asis_hos, Ref #1):
--   1 regla  nombre='cups_equivalentes_hospitalizacion' version=1
--            dominio='hospitalizacion' estado='active' prioridad=5
--            severidad='error' activo=true, descripcion 'Código CUPS ...'
--   15 condiciones under one composite OR root, including atomics
--            invoice.codigo = 906317 and invoice.codigo = 906249.
-- Minimal seed here is rule + OR root + those two atomics; the full tree
-- lives in the source DB and is NOT rebuilt here (repair only re-parents
-- the two loose atomics, never deletes).
--
-- Fail-fast ONLY for genuine shape violations: a root-level row that is
-- neither the composite OR root nor a repairable loose atomic.
-- Missing rule / missing root / missing atomics are seeded, not errors.
-- Idempotent: re-running is a no-op once the shape is correct.
-- =============================================================================
DO $$
DECLARE
    rid integer;
    or_root_id integer;
    violation_count integer;
    next_ord integer;
BEGIN
    -- (a) seed-if-missing: rule keyed by (nombre, version).
    SELECT id
    INTO rid
    FROM reglas
    WHERE nombre = 'cups_equivalentes_hospitalizacion'
      AND version = 1
    ORDER BY id
    LIMIT 1;

    IF rid IS NULL THEN
        INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
        VALUES (
            'cups_equivalentes_hospitalizacion',
            'Código CUPS con equivalente conocido detectado',
            'hospitalizacion', 'active', 1, 5, 'error', true, NULL
        )
        RETURNING id INTO rid;

        UPDATE reglas SET rule_base_id = rid WHERE id = rid AND rule_base_id IS NULL;
    END IF;

    -- (c) fail-fast ONLY for genuine shape violations: root-level rows that
    -- are neither the OR root nor the two known repairable loose atomics.
    SELECT COUNT(*)
    INTO violation_count
    FROM condiciones
    WHERE regla_id = rid
      AND padre_id IS NULL
      AND NOT (tipo = 'composite' AND operador = 'OR')
      AND NOT (tipo = 'atomic'
           AND fuente_datos = 'invoice.codigo'
           AND valor_esperado #>> '{}' IN ('906317', '906249'));

    IF violation_count > 0 THEN
        RAISE EXCEPTION 'cups_equivalentes_hospitalizacion has % unexpected root-level condition(s)', violation_count;
    END IF;

    -- Ensure the composite OR root exists (seed when absent).
    SELECT id
    INTO or_root_id
    FROM condiciones
    WHERE regla_id = rid
      AND padre_id IS NULL
      AND tipo = 'composite'
      AND operador = 'OR'
    ORDER BY id
    LIMIT 1;

    IF or_root_id IS NULL THEN
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, NULL, 'composite', 'OR', NULL, NULL, 0)
        RETURNING id INTO or_root_id;
    END IF;

    -- (b) repair: move loose atomics under the root, preserving relative order.
    WITH loose_conditions AS (
        SELECT
            c.id,
            row_number() OVER (ORDER BY c.orden, c.id) - 1 AS relative_order
        FROM condiciones c
        WHERE c.regla_id = rid
          AND c.padre_id IS NULL
          AND c.tipo = 'atomic'
          AND c.fuente_datos = 'invoice.codigo'
          AND c.valor_esperado #>> '{}' IN ('906317', '906249')
    ), next_order AS (
        SELECT COALESCE(MAX(orden), -1) + 1 AS value
        FROM condiciones
        WHERE padre_id = or_root_id
    )
    UPDATE condiciones c
    SET padre_id = or_root_id,
        orden = next_order.value + loose.relative_order
    FROM loose_conditions loose
    CROSS JOIN next_order
    WHERE c.id = loose.id;

    -- (a) seed-if-missing: the two atomics under the root (after repair, so
    -- moved loose rows count as present and are never duplicated).
    SELECT COALESCE(MAX(orden), -1) + 1
    INTO next_ord
    FROM condiciones
    WHERE padre_id = or_root_id;

    IF NOT EXISTS (
        SELECT 1
        FROM condiciones
        WHERE regla_id = rid
          AND padre_id = or_root_id
          AND tipo = 'atomic'
          AND fuente_datos = 'invoice.codigo'
          AND valor_esperado #>> '{}' = '906317'
    ) THEN
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, or_root_id, 'atomic', 'eq', 'invoice.codigo', '"906317"'::jsonb, next_ord);
        next_ord := next_ord + 1;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM condiciones
        WHERE regla_id = rid
          AND padre_id = or_root_id
          AND tipo = 'atomic'
          AND fuente_datos = 'invoice.codigo'
          AND valor_esperado #>> '{}' = '906249'
    ) THEN
        INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
        VALUES (rid, or_root_id, 'atomic', 'eq', 'invoice.codigo', '"906249"'::jsonb, next_ord);
    END IF;
END $$;
