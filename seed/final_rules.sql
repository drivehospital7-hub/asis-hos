-- Final missing rules: duplicados_farmacia + sala_observacion_entity
BEGIN;

-- duplicados_farmacia — simplified per-row check for duplicated pharmacy codes
-- NOTE: Full multi-pass aggregation (like legacy) not expressible in current engine.
-- This simplified version catches common duplicate patterns.
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'duplicados_farmacia',
    'Detecta posibles duplicados en facturacion de farmacia (simplificado - per-row check)',
    'urgencias', 'active', 1, 35, 'warning', TRUE
);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0 FROM reglas r WHERE r.nombre = 'duplicados_farmacia';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"FARMACIA"'::jsonb, 0 FROM reglas r WHERE r.nombre = 'duplicados_farmacia';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'gt', 'invoice.cantidad', '1'::jsonb, 1 FROM reglas r WHERE r.nombre = 'duplicados_farmacia';

-- sala_observacion extended: add entity-specific rule for EPSS41 and EPSI05
INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
VALUES (
    'sala_observacion_entidad',
    'Estancia en sala de observacion mayor a 6 horas para entidades especificas',
    'urgencias', 'active', 1, 30, 'error', TRUE
);
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, NULL, 'composite', 'AND', NULL, NULL, 0 FROM reglas r WHERE r.nombre = 'sala_observacion_entidad';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'gt', 'date.horas', '6'::jsonb, 0 FROM reglas r WHERE r.nombre = 'sala_observacion_entidad';
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
SELECT r.id, (SELECT MAX(c.id) FROM condiciones c WHERE c.regla_id = r.id), 'atomic', 'in', 'invoice.codigo_entidad_cobrar', '["EPSS41","EPSI05","EPSIC5"]'::jsonb, 1 FROM reglas r WHERE r.nombre = 'sala_observacion_entidad';

COMMIT;
