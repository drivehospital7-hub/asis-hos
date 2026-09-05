-- Migration 006: Backfill rule version lineage safely
--
-- Rows with a NULL/self base are grouped only when the existing identity/version
-- data proves one sequence: same name and domain, versions starting at 1, with
-- no gaps. The self-base condition is needed because migration 004 may already
-- have converted NULL to id before this migration runs. Existing shared bases
-- are treated as authoritative and are not rewritten.
-- Ambiguous or standalone rows are deliberately kept separate by using their
-- own id as the base. Rule contents, states, ids, conditions, and exceptions
-- are not modified.
--
-- Run through: python run_migrations.py

BEGIN;

WITH candidate_groups AS (
    SELECT
        nombre,
        dominio,
        MIN(id) AS base_id,
        COUNT(*) AS row_count,
        MIN(version) AS first_version,
        MAX(version) AS last_version,
        COUNT(DISTINCT version) AS distinct_versions
    FROM reglas
    WHERE rule_base_id IS NULL OR rule_base_id = id
    GROUP BY nombre, dominio
),
safe_groups AS (
    SELECT nombre, dominio, base_id
    FROM candidate_groups
    WHERE first_version = 1
      AND last_version = row_count
      AND distinct_versions = row_count
)
UPDATE reglas AS r
SET rule_base_id = g.base_id
FROM safe_groups AS g
WHERE (r.rule_base_id IS NULL OR r.rule_base_id = r.id)
  AND r.nombre = g.nombre
  AND r.dominio = g.dominio;

-- Every row left nullable is not proven to belong to another row's lineage.
-- Keep it isolated rather than guessing and potentially merging rules.
UPDATE reglas
SET rule_base_id = id
WHERE rule_base_id IS NULL;

COMMIT;
