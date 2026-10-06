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
  | "complex"
  | "empty";

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
  { id: "empty", label: "Vacío" },
];

// ─── All 21 Atomic Operators (sync with evaluators.py) ─────────────

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
  // Empty (no value needed)
  { value: "is_empty", label: "Vacío (is_empty)", category: "empty" },
  { value: "not_empty", label: "No vacío (not_empty)", category: "empty" },
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
  { value: "hospi_sala_obs_cantidad_check", label: "Hospi sala obs cantidad", category: "db" },
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
  // Empty → no value
  is_empty: "hidden",
  not_empty: "hidden",
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
  hospi_sala_obs_cantidad_check: "hidden", // context-derived
  // Complex
  all_values_match: "number", // threshold
  cups_contratado: "hidden", // context-derived
};

// ─── Composite Operators ───────────────────────────────────────────

export const OPERADORES_COMPOSITE = ["AND", "OR", "NOT"] as const;

// ─── FUENTES_DATOS ─────────────────────────────────────────────────

export const FUENTES_DATOS: string[] = [
  // invoice.* (row fields + collect_set/aggregates used by seeded rules)
  "invoice.vlr_subsidiado",
  "invoice.vlr_procedimiento",
  "invoice.convenio_facturado",
  "invoice.codigo",
  "invoice.codigo_profesional",
  "invoice.collect_set_codigo",
  "invoice.collect_set_tarifario",
  "invoice.count",
  "invoice.estancia_horas",
  "invoice.cantidad",
  "invoice.numero_factura",
  "invoice.numero_autorizacion",
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
  "invoice.vacuna",
  "invoice.tipo_factura_descripcion",
  "invoice.codigo_equiv",
  "invoice.codigo_tipo_procedimiento",
  "invoice.entidad_afiliacion",
  "invoice.responsable_cierra",
  "invoice.profesional_atiende",
  "date.edad",
  "date.edad_meses",
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
  "group.collect_set_codigo",
  "group.collect_set_tipos",
  "group.collect_value_counts",
  "group.sum_cantidad",
  "group.distinct_count_numero_factura",
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

// ─── Rule evaluation mode (row vs grouped) ─────────────────────────
//
// The engine routes on `parametros[0].group_by`: present → per-factura
// group evaluation; absent → row-by-row. This section lets the editor
// expose that switch and filter selects accordingly. Filtering is
// guidance only (datalists accept free text; the backend validates
// shape, not operator vocabulary).

export type RuleMode = "row" | "group";

/** Operators that only make sense on aggregated sets (group mode). */
export const GROUP_ONLY_OPERATORS: string[] = [
  "set_contains_all",
  "set_intersects",
];

/** invoice.* fields homogeneous per factura (safe group prefilter / group_by). */
export const FACTURA_LEVEL_FIELDS: string[] = [
  "invoice.numero_factura",
  "invoice.tarifario",
  "invoice.convenio_facturado",
  "invoice.tipo_factura_descripcion",
  "invoice.entidad_cobrar",
  "invoice.codigo_entidad_cobrar",
];

/** invoice.* row fields offered for aggregation / group_by. */
export const INVOICE_ROW_FIELDS: string[] = FUENTES_DATOS.filter(
  (f) => f.startsWith("invoice.") && !f.includes("collect_set") && !f.includes("distinct_count") && !f.includes("sum_"),
);

export interface GroupAggregation {
  function: string;
  field?: string;
  field1?: string;
  field2?: string;
  target: string;
}

export interface GroupParamConfig {
  group_by: string | string[];
  aggregations?: GroupAggregation[];
  filter_field?: string;
  filter_value?: string;
}

export const AGG_FUNCTIONS: { value: string; label: string }[] = [
  { value: "collect_set", label: "Conjunto (collect_set)" },
  { value: "distinct_count", label: "Distintos (distinct_count)" },
  { value: "sum", label: "Suma (sum)" },
  { value: "compute_horas", label: "Horas entre fechas (compute_horas)" },
];

/** Derive the editor mode from stored parametros. */
export function parseRuleMode(parametros: unknown): RuleMode {
  if (Array.isArray(parametros) && parametros.length > 0) {
    const first = parametros[0] as Record<string, unknown> | null;
    if (first && typeof first === "object" && first["group_by"]) return "group";
  }
  return "row";
}

/** Extract the editable group config (index 0) or null. */
export function getGroupConfig(parametros: unknown): GroupParamConfig | null {
  if (parseRuleMode(parametros) !== "group") return null;
  const first = (parametros as unknown[])[0] as GroupParamConfig;
  return {
    group_by: first.group_by ?? "numero_factura",
    aggregations: Array.isArray(first.aggregations) ? [...first.aggregations] : [],
    ...(first.filter_field ? { filter_field: first.filter_field } : {}),
    ...(first.filter_value ? { filter_value: first.filter_value } : {}),
  };
}

/** True when the params text is empty or a pure group config array. */
export function isBuilderCompatibleParams(text: string): boolean {
  if (!text.trim()) return true;
  try {
    const parsed: unknown = JSON.parse(text);
    if (!Array.isArray(parsed) || parsed.length === 0) return false;
    const first = parsed[0] as Record<string, unknown>;
    if (!first || typeof first !== "object") return false;
    const allowed = new Set(["group_by", "aggregations", "filter_field", "filter_value"]);
    return Object.keys(first).every((k) => allowed.has(k));
  } catch {
    return false;
  }
}

/** Get the value type for an operator. Defaults to "string". */
export function getValueTypeForOperator(operator: string): ValueType {
  return OPERADOR_VALUE_TYPE[operator] ?? "string";
}
