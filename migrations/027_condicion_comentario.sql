-- =============================================================================
-- 027_condicion_comentario.sql
--
-- Memo libre por nodo del arbol de condiciones (UI: boton "+" por rama).
-- Solo documentacion: el motor lo ignora en la evaluacion.
-- Idempotente, sin BEGIN/COMMIT, portable PG/SQLite (guardas por catalogo).
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'condiciones' AND column_name = 'comentario'
    ) THEN
        ALTER TABLE condiciones ADD COLUMN comentario TEXT;
    END IF;
END $$;
