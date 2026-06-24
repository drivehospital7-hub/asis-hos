/** API client for the Rule Engine Admin page.
 *
 * Typed fetch wrapper for CRUD operations on rules, versions,
 * exceptions, evidence, audit, and simulation.
 *
 * Each function returns the parsed response data on success,
 * or throws an error with the server message on failure.
 */

// ─── Types ──────────────────────────────────────────────────────────

export interface Regla {
  id: number;
  rule_base_id: number | null;
  nombre: string;
  descripcion: string | null;
  dominio: string;
  estado: string;
  version: number;
  prioridad: number;
  severidad: string;
  activo: boolean;
  parametros: Record<string, unknown> | null;
  parametros_default: Record<string, unknown> | null;
  creado_en: string | null;
  actualizado_en: string | null;
  condiciones?: CondicionTree[] | null;
  excepciones?: Excepcion[] | null;
}

export interface CondicionTree {
  id: number;
  regla_id: number;
  padre_id: number | null;
  tipo: string;
  operador: string | null;
  fuente_datos: string | null;
  valor_esperado: unknown;
  orden: number;
  condiciones?: CondicionTree[];
  [key: string]: unknown;  // Allow dynamic field access (updateNodeInTree helper)
}

export interface Excepcion {
  id: number;
  regla_id: number;
  tipo_efecto: string;
  condicion_json: Record<string, unknown>;
  parametros_override: Record<string, unknown> | null;
  activo: boolean;
  creado_en: string | null;
  expira_en: string | null;
}

export interface EvidenciaItem {
  id: number;
  regla_id: number;
  regla_version: number;
  dominio: string;
  factura: string;
  outcome: string;
  arbol_evaluado: Record<string, unknown>;
  creado_en: string | null;
}

export interface EvidenciaResult {
  items: EvidenciaItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditItem {
  id: number;
  evidencia_id: number;
  regla_id: number;
  regla_version: number;
  factura: string;
  resultado: string;
  severidad: string;
  mensaje: string | null;
  creado_en: string | null;
}

export interface AuditResult {
  items: AuditItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface SimulateResult {
  engine_results: Array<Record<string, unknown>>;
  legacy_results: Array<Record<string, unknown>>;
  diff: {
    matched: Array<{ factura: string; problema: string }>;
    engine_only: Array<{ factura: string; problema: string }>;
    legacy_only: Array<{ factura: string; problema: string }>;
    matched_count: number;
    engine_only_count: number;
    legacy_only_count: number;
    engine_total: number;
    legacy_total: number;
  };
  total_rows: number;
  rows_processed: number;
  truncated: boolean;
}

export interface UpdateResult {
  old_rule_id: number;
  new_rule_id: number;
  old_version: number;
  new_version: number;
}

interface ApiResponse<T> {
  status: "success" | "error";
  data: T;
  errors: string[];
}

// ─── Helpers ─────────────────────────────────────────────────────────

async function apiGet<T>(url: string): Promise<T> {
  const res = await fetch(url);
  const json: ApiResponse<T> = await res.json();
  if (json.status === "error") {
    throw new Error(json.errors?.[0] ?? "Error de servidor");
  }
  return json.data;
}

async function apiPost<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json: ApiResponse<T> = await res.json();
  if (json.status === "error") {
    throw new Error(json.errors?.[0] ?? "Error de servidor");
  }
  return json.data;
}

async function apiPut<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json: ApiResponse<T> = await res.json();
  if (json.status === "error") {
    throw new Error(json.errors?.[0] ?? "Error de servidor");
  }
  return json.data;
}

async function apiDelete(url: string): Promise<void> {
  const res = await fetch(url, { method: "DELETE" });
  const json: ApiResponse<unknown> = await res.json();
  if (json.status === "error") {
    throw new Error(json.errors?.[0] ?? "Error de servidor");
  }
}

// ─── Rules CRUD ──────────────────────────────────────────────────────

/** List all rules with optional filters. */
export async function fetchReglas(params?: {
  dominio?: string;
  estado?: string;
  activo?: string;
}): Promise<Regla[]> {
  const searchParams = new URLSearchParams();
  if (params?.dominio) searchParams.set("dominio", params.dominio);
  if (params?.estado) searchParams.set("estado", params.estado);
  if (params?.activo) searchParams.set("activo", params.activo);
  const qs = searchParams.toString();
  return apiGet<Regla[]>(`/api/reglas${qs ? `?${qs}` : ""}`);
}

/** Get a single rule with conditions and exceptions. */
export async function fetchRegla(id: number): Promise<Regla> {
  return apiGet<Regla>(`/api/reglas/${id}`);
}

/** Create a new rule. */
export async function createRegla(data: Partial<Regla> & { condiciones?: unknown }): Promise<Regla> {
  return apiPost<Regla>("/api/reglas", data);
}

/** Update a rule (auto-versioning). */
export async function updateRegla(id: number, data: Partial<Regla>): Promise<UpdateResult> {
  return apiPut<UpdateResult>(`/api/reglas/${id}`, data);
}

/** Soft-delete a rule. */
export async function deleteRegla(id: number): Promise<void> {
  return apiDelete(`/api/reglas/${id}`);
}

// ─── Versions ────────────────────────────────────────────────────────

/** List all versions of a rule. */
export async function fetchVersiones(reglaId: number): Promise<Regla[]> {
  return apiGet<Regla[]>(`/api/reglas/${reglaId}/versiones`);
}

/** Clone the active version as a new draft. */
export async function versionarRegla(reglaId: number): Promise<Regla> {
  return apiPost<Regla>(`/api/reglas/${reglaId}/versionar`, {});
}

// ─── Exceptions ──────────────────────────────────────────────────────

/** List all exceptions for a rule. */
export async function fetchExcepciones(reglaId: number): Promise<Excepcion[]> {
  return apiGet<Excepcion[]>(`/api/reglas/${reglaId}/excepciones`);
}

/** Create a new exception for a rule. */
export async function createExcepcion(
  reglaId: number,
  data: { tipo_efecto: string; condicion_json: Record<string, unknown>; activo?: boolean },
): Promise<Excepcion> {
  return apiPost<Excepcion>(`/api/reglas/${reglaId}/excepciones`, data);
}

// ─── Evidence & Audit ────────────────────────────────────────────────

/** Query evidence records with filters and pagination. */
export async function queryEvidencias(params?: {
  regla_id?: number;
  factura?: string;
  dominio?: string;
  outcome?: string;
  desde?: string;
  hasta?: string;
  limit?: number;
  offset?: number;
}): Promise<EvidenciaResult> {
  const searchParams = new URLSearchParams();
  if (params?.regla_id) searchParams.set("regla_id", String(params.regla_id));
  if (params?.factura) searchParams.set("factura", params.factura);
  if (params?.dominio) searchParams.set("dominio", params.dominio);
  if (params?.outcome) searchParams.set("outcome", params.outcome);
  if (params?.desde) searchParams.set("desde", params.desde);
  if (params?.hasta) searchParams.set("hasta", params.hasta);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiGet<EvidenciaResult>(`/api/evidencias${qs ? `?${qs}` : ""}`);
}

/** Query audit results with filters and pagination. */
export async function queryAuditoria(params?: {
  regla_id?: number;
  factura?: string;
  resultado?: string;
  desde?: string;
  hasta?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditResult> {
  const searchParams = new URLSearchParams();
  if (params?.regla_id) searchParams.set("regla_id", String(params.regla_id));
  if (params?.factura) searchParams.set("factura", params.factura);
  if (params?.resultado) searchParams.set("resultado", params.resultado);
  if (params?.desde) searchParams.set("desde", params.desde);
  if (params?.hasta) searchParams.set("hasta", params.hasta);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiGet<AuditResult>(`/api/auditoria${qs ? `?${qs}` : ""}`);
}

/** Delete all evidence and audit records (testing only). */
export async function clearEvidencias(): Promise<{ message: string }> {
  const res = await fetch("/api/evidencias", { method: "DELETE" });
  const json: ApiResponse<{ message: string }> = await res.json();
  if (json.status === "error") {
    throw new Error(json.errors?.[0] ?? "Error al limpiar datos");
  }
  return json.data;
}

// ─── Simulator ───────────────────────────────────────────────────────

/** Run a dry-run simulation comparing engine vs legacy detectors. */
export async function simulateReglas(
  file: File,
  ruleName?: string,
): Promise<SimulateResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (ruleName) formData.append("rule_name", ruleName);

  const res = await fetch("/api/reglas/simular", {
    method: "POST",
    body: formData,
  });
  const json: ApiResponse<SimulateResult> = await res.json();
  if (json.status === "error") {
    throw new Error(json.errors?.[0] ?? "Error de servidor");
  }
  return json.data;
}
