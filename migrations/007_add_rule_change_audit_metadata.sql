-- Migration 007: Add audit metadata to rule versions.
-- Existing versions remain valid and receive NULL metadata.

ALTER TABLE reglas
    ADD COLUMN IF NOT EXISTS cambio_que TEXT NULL,
    ADD COLUMN IF NOT EXISTS cambio_por_que TEXT NULL,
    ADD COLUMN IF NOT EXISTS cambio_responsable VARCHAR(100) NULL;
