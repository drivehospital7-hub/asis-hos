-- =============================================================================
-- Migration Engine F2: duplicados_farmacia_farmacia
-- Rule: GroupEvaluator — flag facturas where ALL (codigo, cantidad) pairs
--       appear at least 2 times, filtered by tipo_factura_descripcion = Farmacia.
-- Domain: farmacia
-- Evaluator: all_values_match
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, parametros, severidad, activo)
SELECT 'duplicados_farmacia_farmacia',
       'Duplicados en Farmacia — facturas donde todos los pares (codigo, cantidad) están duplicados',
       'farmacia', 'active', 1, 35,
       '[{"group_by": "numero_factura", "filter_field": "tipo_factura_descripcion", "filter_value": "Farmacia", "aggregations": [{"function": "collect_value_counts", "fields": ["codigo", "cantidad"], "target": "pares"}]}]',
       'warning', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'duplicados_farmacia_farmacia' AND version = 1
);

DELETE FROM condiciones WHERE regla_id = (
    SELECT id FROM reglas WHERE nombre = 'duplicados_farmacia_farmacia' AND version = 1
);

-- Single atomic condition: all_values_match(pares, threshold=2)
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (
    (SELECT id FROM reglas WHERE nombre = 'duplicados_farmacia_farmacia' AND version = 1),
    NULL,
    'atomic',
    'all_values_match',
    'invoice.pares',
    '2',
    0
);
