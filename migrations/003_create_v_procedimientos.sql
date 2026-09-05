-- Migration 003: Create unified view v_procedimientos
-- Flattens the 5-table chain (eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento)
-- into the flat structure expected by procedimientos_db.py.
-- Uses DISTINCT ON (eps, cups) ORDER BY tariff DESC so the highest tariff prevails on duplicates.
-- Idempotent: CREATE OR REPLACE VIEW allows safe re-execution.
-- Reversible: DROP VIEW IF EXISTS v_procedimientos;

CREATE OR REPLACE VIEW v_procedimientos AS
SELECT
    ROW_NUMBER() OVER (ORDER BY eps, codigo_cups) AS id,
    eps,
    codigo_cups,
    descripcion,
    tarifa,
    created_at,
    updated_at
FROM (
    SELECT DISTINCT ON (ec.eps, p.cups)
        ec.eps,
        p.cups AS codigo_cups,
        p.procedimiento AS descripcion,
        nt.tariff AS tarifa,
        CAST(NULL AS TIMESTAMPTZ) AS created_at,
        CAST(NULL AS TIMESTAMPTZ) AS updated_at
    FROM eps_contratado ec
    JOIN eps_nota en ON en.id_eps_contratado = ec.id
    JOIN nota_hoja nh ON nh.id = en.id_nota_hoja
    JOIN notas_tecnicas nt ON nt.id_nota_hoja = nh.id
    JOIN procedimiento p ON p.id = nt.id_procedimiento
    ORDER BY ec.eps, p.cups, nt.tariff DESC
) sub;
