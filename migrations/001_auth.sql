-- Tablas para auth. Los usuarios reales se provisionan desde
-- instance/users.json mediante scripts/migrate_users_json_to_db.py.
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'usuario',
    primer_nombre VARCHAR(100) NOT NULL DEFAULT '',
    segundo_nombre VARCHAR(100) NOT NULL DEFAULT '',
    apellido_1 VARCHAR(100) NOT NULL DEFAULT '',
    apellido_2 VARCHAR(100) NOT NULL DEFAULT '',
    permisos JSON NOT NULL DEFAULT '[]'::json
);

CREATE TABLE IF NOT EXISTS user_areas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    area VARCHAR(50) NOT NULL
);
