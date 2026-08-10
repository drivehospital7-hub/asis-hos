-- Completa users para instalaciones creadas con la versión inicial de 001_auth.
-- No inserta, actualiza ni elimina datos: la carga controlada está en el
-- script de provisioning de usuarios.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS primer_nombre VARCHAR(100) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS segundo_nombre VARCHAR(100) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS apellido_1 VARCHAR(100) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS apellido_2 VARCHAR(100) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS permisos JSON NOT NULL DEFAULT '[]'::json;
