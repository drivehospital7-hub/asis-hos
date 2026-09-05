// ─── Types ──────────────────────────────────────────────────────────

export interface OperatorDef {
  value: string;
  label: string;
  category: OperatorCategory;
}

export type OperatorCategory =
  | "comparison"
  | "string"
  | "set"
  | "db"
  | "complex";

export type ValueType = "number" | "string" | "json" | "array" | "hidden";

export interface CategoryDef {
  id: OperatorCategory;
  label: string;
}

// ─── Operator Categories ────────────────────────────────────────────

export const CATEGORIAS: CategoryDef[] = [
  { id: "comparison", label: "Comparación" },
  { id: "string", label: "String" },
  { id: "set", label: "Set / Lista" },
  { id: "db", label: "Base de Datos" },
  { id: "complex", label: "Complejo" },
];

// ─── All 18 Atomic Operators (sync with evaluators.py) ─────────────

export const OPERADORES_ATOMICOS: OperatorDef[] = [
  // Comparison
  { value: "eq", label: "Igual (=)", category: "comparison" },
  { value: "gt", label: "Mayor (>)", category: "comparison" },
  { value: "gte", label: "Mayor o igual (>=)", category: "comparison" },
  { value: "lt", label: "Menor (<)", category: "comparison" },
  { value: "lte", label: "Menor o igual (<=)", category: "comparison" },
  // String
  { value: "contains", label: "Contiene", category: "string" },
  { value: "regex", label: "Regex", category: "string" },
  { value: "regex_extract", label: "Regex (extraer)", category: "string" },
  // Set
  { value: "in", label: "En lista (in)", category: "set" },
  { value: "cat_in", label: "En catálogo (cat_in)", category: "set" },
  { value: "set_contains_all", label: "Set contiene todo", category: "set" },
  { value: "set_intersects", label: "Set intersecta", category: "set" },
  // DB
  { value: "exists_in_db", label: "Existe en DB", category: "db" },
  { value: "ent_code_match", label: "Código entidad coincide", category: "db" },
  { value: "sala_obs_check", label: "Sala observación", category: "db" },
  { value: "centro_costo_check", label: "Centro costo", category: "db" },
  // Complex
  { value: "all_values_match", label: "Todos los valores coinciden", category: "complex" },
  { value: "cups_contratado", label: "CUPS contratado", category: "complex" },
];

// ─── Operator → Value Type Mapping ─────────────────────────────────

export const OPERADOR_VALUE_TYPE: Record<string, ValueType> = {
  // Comparison → number
  eq: "string", // eq works for both numbers and strings
  gt: "number",
  gte: "number",
  lt: "number",
  lte: "number",
  // String → text
  contains: "string",
  regex: "string",
  regex_extract: "json", // pattern string → JSON textarea
  // Set
  in: "array",
  cat_in: "string", // catalog key name
  set_contains_all: "array",
  set_intersects: "array",
  // DB
  exists_in_db: "json", // { table, field }
  ent_code_match: "hidden", // context-derived
  sala_obs_check: "hidden", // context-derived
  centro_costo_check: "hidden", // context-derived
  // Complex
  all_values_match: "number", // threshold
  cups_contratado: "hidden", // context-derived
};

// ─── Composite Operators ───────────────────────────────────────────

export const OPERADORES_COMPOSITE = ["AND", "OR", "NOT"] as const;

// ─── FUENTES_DATOS ─────────────────────────────────────────────────

export const FUENTES_DATOS: string[] = [
  // invoice.* (existing 31 fields)
  "invoice.vlr_subsidiado",
  "invoice.vlr_procedimiento",
  "invoice.convenio_facturado",
  "invoice.codigo",
  "invoice.cantidad",
  "invoice.numero_factura",
  "invoice.tipo_procedimiento",
  "invoice.centro_costo",
  "invoice.identificacion",
  "invoice.edad",
  "invoice.tipo_identificacion",
  "invoice.entidad_cobrar",
  "invoice.factura_count",
  "invoice.tipo_usuario",
  "invoice.codigo_entidad_cobrar",
  "invoice.vlr_copago",
  "invoice.ide_contrato",
  "invoice.tarifario",
  "invoice.fec_nacimiento",
  "invoice.fec_factura",
  "invoice.laboratorio",
  "invoice.tipo_factura_descripcion",
  "invoice.codigo_equiv",
  "invoice.codigo_tipo_procedimiento",
  "invoice.entidad_afiliacion",
  "invoice.responsable_cierra",
  "invoice.profesional_atiende",
  "date.edad",
  "date.horas",
  "invoice.distinct_count_tipo_procedimiento",
  "invoice.sum_cantidad",
  // catalog.*
  "catalog.key",
  "catalog.value",
  // group.*
  "group.id",
  "group.nombre",
  "group.tipo",
  // contract.*
  "contract.id",
  "contract.cod_contrato",
  "contract.eps",
  "contract.nombre_eps",
];

// ─── Helpers ────────────────────────────────────────────────────────

/** Get operators for a given category. */
export function getOperatorsByCategory(category: OperatorCategory): OperatorDef[] {
  return OPERADORES_ATOMICOS.filter((op) => op.category === category);
}

/** Get the value type for an operator. Defaults to "string". */
export function getValueTypeForOperator(operator: string): ValueType {
  return OPERADOR_VALUE_TYPE[operator] ?? "string";
}
