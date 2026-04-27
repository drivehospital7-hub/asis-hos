-- Tablas para auth
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'usuario'
);

CREATE TABLE IF NOT EXISTS user_areas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    area VARCHAR(50) NOT NULL
);

-- Usuarios de ejemplo
INSERT INTO users (username, password_hash, rol) VALUES 
    ('admin', 'scrypt:32768:8:1$ere19G35Q5YnxUyX$19eb99000a172ef73b9319dcfe2a5a3160e12e95bb639634af68f3282ae0d4cb1632a0fc2a8bed410957d45a34327ff96637f3b7ccf15fbc9f183fdfa15d531b', 'admin')
ON CONFLICT (username) DO NOTHING;

INSERT INTO users (username, password_hash, rol) VALUES 
    ('odonto_user', 'scrypt:32768:8:1$LUquhJhApdnMSSPp$ab6be2953c9deaf61fcb0e4e8e6826db7b61e1adf2b86163697401a7561470fa09bc24a333363ed34deac424b30913de78fa7a959e0a8121fe8ce616f670dbe6', 'usuario')
ON CONFLICT (username) DO NOTHING;

INSERT INTO users (username, password_hash, rol) VALUES 
    ('urgencias_user', 'scrypt:32768:8:1$qS6upK13DOJ43oDd$8f76809ef5cd303f135ec457c9ea369733687bf8a574d40ed8e3f5fe8891655e67b6e9e36af78f8f535e8cfb9e3026ee70d01a73479b1813b3e197732d80a814', 'usuario')
ON CONFLICT (username) DO NOTHING;

-- Asignar áreas
INSERT INTO user_areas (user_id, area)
SELECT id, 'odontologia' FROM users WHERE username = 'odonto_user' AND id NOT IN (SELECT user_id FROM user_areas WHERE area = 'odontologia')
ON CONFLICT DO NOTHING;

INSERT INTO user_areas (user_id, area)
SELECT id, 'urgencias' FROM users WHERE username = 'urgencias_user' AND id NOT IN (SELECT user_id FROM user_areas WHERE area = 'urgencias')
ON CONFLICT DO NOTHING;