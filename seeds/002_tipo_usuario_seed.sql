-- =============================================================================
-- Seed: tipo_usuario_valido — detecta tipo de usuario no válido
-- =============================================================================
-- Domain: transversal (aplica a todos los dominios)
-- Lógica: NOT(IN(invoice.tipo_usuario, [valores_válidos]))
-- =============================================================================

BEGIN;

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'tipo_usuario_valido',
    'Detecta facturas con tipo de usuario no válido.',
    'transversal',
    'active',
    1,
    15,
    'warning',
    TRUE
);

-- Root: NOT composite
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'tipo_usuario_valido'),
    NULL, 'composite', 'NOT', NULL, NULL, 0
);

-- Child: IN against valid values
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'tipo_usuario_valido'),
    (SELECT id FROM condiciones WHERE regla_id = (SELECT id FROM reglas WHERE nombre = 'tipo_usuario_valido') AND padre_id IS NULL),
    'atomic', 'in', 'invoice.tipo_usuario',
    '["SUBSIDIADO", "CONTRIBUTIVO", "OTROS (REGIMENES ESPECIALES, EOC)", "VINCULADO", "PARTICULAR"]'::jsonb,
    0
);

COMMIT;

SELECT nombre, dominio, estado, prioridad FROM reglas WHERE nombre = 'tipo_usuario_valido';
