-- =============================================================================
-- Seed: catalogos — catálogos para reglas cat_in
-- =============================================================================
-- La tabla catalogos almacena listas de valores referenciadas por reglas
-- que usan el operador cat_in. Cada fila es un key + JSONB array de valores.
-- =============================================================================

BEGIN;

INSERT INTO catalogos (key, value)
VALUES (
    'tipo_usuario_validos',
    '["SUBSIDIADO", "CONTRIBUTIVO", "OTROS (REGIMENES ESPECIALES, EOC)", "VINCULADO", "PARTICULAR"]'::jsonb
) ON CONFLICT (key) DO NOTHING;

COMMIT;

SELECT key, jsonb_array_length(value) as cantidad FROM catalogos WHERE key = 'tipo_usuario_validos';
