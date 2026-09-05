-- =============================================================================
-- Migration Engine F5: duplicado_id_codigo_02_lab
-- Rule: GroupEvaluator — flag facturas where group (ident, codigo, dx)
--       appears >= 4 times for tipo=02 + Laboratorio=Si.
-- Domain: intramural
-- Evaluator: gte (via condition tree)
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, parametros, severidad, activo)
SELECT 'duplicado_id_codigo_02_lab',
       'Duplicados ID+Código para tipo=02+Lab=Si — grupos de (identificacion, codigo, dx_principal) con count >= 4',
       'intramural', 'active', 1, 51,
       '[{"group_by": ["identificacion", "codigo", "codigo_dx_principal"], "filter_field": "codigo_tipo_procedimiento", "filter_value": "02", "aggregations": [{"function": "group_size", "target": "count"}, {"function": "collect_group_keys", "field": "numero_factura", "target": "facturas"}]}]',
       'warning', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'duplicado_id_codigo_02_lab' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'duplicado_id_codigo_02_lab' AND version = 1
);

-- Single atomic condition: gte(count, 4)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'duplicado_id_codigo_02_lab' AND version = 1),
    NULL,
    'atomic',
    'gte',
    'invoice.count',
    '4',
    0
);
