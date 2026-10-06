-- =============================================================================
-- 026: catalogo grupos_error (la lista de sugerencias vive en DB).
--
-- Los grupos son etiquetas en reglas.grupo_error; esta tabla es el
-- catalogo gestionable desde el modal (crear/renombrar/desasignar).
-- Backfill con las 23 etiquetas canonicas (src app/constants/grupo_error.py
-- ALL_GRUPO_ERROR_LABELS): 5 sistema (formato propio, bloqueadas en UI)
-- + 18 simples. Idempotente, sin BEGIN/COMMIT, portable PG/SQLite.
-- =============================================================================

CREATE TABLE IF NOT EXISTS grupos_error (
    nombre TEXT PRIMARY KEY,
    tipo TEXT NOT NULL DEFAULT 'simple',
    descripcion TEXT NULL
);

INSERT INTO grupos_error (nombre, tipo) SELECT 'Tipo Identificacion / Edad', 'sistema' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Tipo Identificacion / Edad');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Codigo-Entidad-vs-Afiliacion', 'sistema' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Codigo-Entidad-vs-Afiliacion');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Duplicados-Farmacia', 'sistema' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Duplicados-Farmacia');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Cups-Equivalentes', 'sistema' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Cups-Equivalentes');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Revision-Necesaria', 'sistema' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Revision-Necesaria');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Centros de Costo', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Centros de Costo');
INSERT INTO grupos_error (nombre, tipo) SELECT 'IDE Contrato', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'IDE Contrato');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Profesionales', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Profesionales');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Cantidades', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Cantidades');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Cantidades SOAT', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Cantidades SOAT');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Cantidades Hospitalización', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Cantidades Hospitalización');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Cantidades SOAT Hospitalización', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Cantidades SOAT Hospitalización');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Decimales', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Decimales');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Tipo Usuario', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Tipo Usuario');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Copago vs Entidad', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Copago vs Entidad');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Cups Sin Contrato', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Cups Sin Contrato');
INSERT INTO grupos_error (nombre, tipo) SELECT 'MAL CAPITADO', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'MAL CAPITADO');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Ruta Duplicada', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Ruta Duplicada');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Doble Tipo Procedimiento', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Doble Tipo Procedimiento');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Codigos Hospitalizacion', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Codigos Hospitalizacion');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Cronograma Bacteriologas', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Cronograma Bacteriologas');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Duplicado ID-Codigo', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Duplicado ID-Codigo');
INSERT INTO grupos_error (nombre, tipo) SELECT 'Estancias', 'simple' WHERE NOT EXISTS (SELECT 1 FROM grupos_error WHERE nombre = 'Estancias');
