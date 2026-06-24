-- =============================================================================
-- Motor de Reglas de Auditoría — Seed Data (PoC, 3 rules)
-- =============================================================================
-- Migrates legacy detectors: decimales, ruta_duplicada, tipo_documento_edad.
-- Domain: odontologia. Run: psql -d asis_hos -f seeds/motor_reglas_seed.sql
-- =============================================================================

BEGIN;

-- 1. valores_decimales — detect decimal values in Vlr. Subsidiado or Vlr. Procedimiento
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'valores_decimales',
    'Detecta facturas con valores decimales en Vlr. Subsidiado o Vlr. Procedimiento.',
    'odontologia',
    'active',
    1,
    10,
    'error',
    TRUE
);

-- Root: OR composite
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'valores_decimales'),
    NULL, 'composite', 'OR', NULL, NULL, 0
);

-- Leaf 1: regex on vlr_subsidiado
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'valores_decimales'),
    (SELECT id FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'valores_decimales') AND padre_id IS NULL),
    'atomic', 'regex', 'invoice.vlr_subsidiado',
    '"\\.\\d*[1-9]\\d*$"'::jsonb, 0
);

-- Leaf 2: regex on vlr_procedimiento
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'valores_decimales'),
    (SELECT id FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'valores_decimales') AND padre_id IS NULL),
    'atomic', 'regex', 'invoice.vlr_procedimiento',
    '"\\.\\d*[1-9]\\d*$"'::jsonb, 1
);


-- 2. ruta_duplicada — detect patients with >= threshold invoices in PyP
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, parametros, severidad, activo)
VALUES (
    'ruta_duplicada',
    'Detecta pacientes con múltiples facturas en Promoción y Prevención (PyP).',
    'odontologia',
    'active',
    1,
    20,
    '[{"umbral": 3}]'::jsonb,
    'warning',
    TRUE
);

-- Root: AND composite
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'ruta_duplicada'),
    NULL, 'composite', 'AND', NULL, NULL, 0
);

-- Leaf 1: eq on convenio_facturado
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'ruta_duplicada'),
    (SELECT id FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'ruta_duplicada') AND padre_id IS NULL),
    'atomic', 'eq', 'invoice.convenio_facturado',
    '"Promoción y Prevención"'::jsonb, 0
);

-- Leaf 2: gte on factura_count (threshold = 3)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'ruta_duplicada'),
    (SELECT id FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'ruta_duplicada') AND padre_id IS NULL),
    'atomic', 'gte', 'invoice.factura_count',
    '3'::jsonb, 1
);


-- 3. tipo_documento_edad — detect document type / age mismatches (deferred)
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'tipo_documento_edad',
    'Detecta discrepancias entre tipo de documento y edad del paciente. (PoC deferred)',
    'odontologia',
    'draft',
    1,
    30,
    'warning',
    TRUE
);

-- Placeholder root condition
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'tipo_documento_edad'),
    NULL, 'composite', 'AND', NULL, NULL, 0
);


COMMIT;

-- Verification
SELECT nombre, dominio, estado, prioridad
FROM reglas
WHERE dominio = 'odontologia'
ORDER BY prioridad;
