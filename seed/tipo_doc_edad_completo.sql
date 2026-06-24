-- =============================================================================
-- Seed: Tipo Documento vs Edad — reglas faltantes (7-17, MS, AS, CN, CE)
-- =============================================================================

BEGIN;

-- ========== REGLA: 7-17 años debe tener TI ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'tipo_documento_edad_7_17',
    'Tipo de identificacion incorrecto para edad 7-17 anos (debe ser TI)',
    'transversal',
    'active', 1, 30, 'error', TRUE
);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_7_17';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'gte', 'date.edad', '7'::jsonb, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_7_17';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id AND c.padre_id IS NOT NULL), 'atomic', 'lt', 'date.edad', '18'::jsonb, 1 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_7_17';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, c.id, 'composite', 'NOT', NULL, NULL, 2 FROM reglas r JOIN condiciones c ON c.regla_id = r.id AND c.padre_id IS NULL WHERE r.nombre = 'tipo_documento_edad_7_17';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'eq', 'invoice.tipo_identificacion', '"TI"'::jsonb, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_7_17';

-- ========== REGLA: AS no valido en menores de 18 ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'tipo_documento_edad_as_menor',
    'Tipo AS (Adulto Sin identificacion) no valido para menores de 18 anos',
    'transversal',
    'active', 1, 30, 'error', TRUE
);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_as_menor';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'eq', 'invoice.tipo_identificacion', '"AS"'::jsonb, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_as_menor';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'lt', 'date.edad', '18'::jsonb, 1 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_as_menor';

-- ========== REGLA: MS no valido en mayores de 18 ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'tipo_documento_edad_ms_mayor',
    'Tipo MS (Menor Sin identificacion) no valido para mayores de 18 anos',
    'transversal',
    'active', 1, 30, 'error', TRUE
);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_ms_mayor';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'eq', 'invoice.tipo_identificacion', '"MS"'::jsonb, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_ms_mayor';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'gte', 'date.edad', '18'::jsonb, 1 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_ms_mayor';

-- ========== REGLA: CN solo valido < 2 meses ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'tipo_documento_edad_cn_invalido',
    'Tipo CN (Certificado de Nacimiento) solo valido para menores de 2 meses',
    'transversal',
    'active', 1, 30, 'error', TRUE
);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_cn_invalido';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'eq', 'invoice.tipo_identificacion', '"CN"'::jsonb, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_cn_invalido';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'gte', 'date.edad_meses', '2'::jsonb, 1 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_cn_invalido';

-- ========== REGLA: CE solo valido > 7 años ==========
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'tipo_documento_edad_ce_invalido',
    'Tipo CE (Cedula de Extranjeria) solo valido para mayores de 7 anos',
    'transversal',
    'active', 1, 30, 'error', TRUE
);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_ce_invalido';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'eq', 'invoice.tipo_identificacion', '"CE"'::jsonb, 0 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_ce_invalido';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'lte', 'date.edad', '7'::jsonb, 1 FROM reglas r WHERE r.nombre = 'tipo_documento_edad_ce_invalido';

COMMIT;
