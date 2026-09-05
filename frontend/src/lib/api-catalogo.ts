/** API client for the Catalog Management page.
 *
 * Typed fetch wrapper for CRUD operations across SQLite (EpsContratado,
 * Procedimiento CUPS) and PostgreSQL (Procedimientos tariffs).
 *
 * Each function returns the parsed response data on success,
 * or throws an error with the server message on failure.
 */

// ─── Types ──────────────────────────────────────────────────────────

export interface EpsContratado {
  id: number;
  cod_contrato: string;
  eps: string;
  regimen: string;
}

export interface ProcedimientoSqlite {
  id: number;
  cups: string;
  procedimiento: string;
}

export interface NotaHoja {
  id: number;
  nota: string;
}

export interface EpsProcedimientosChain {
  eps: EpsContratado;
  procedimientos: Array<{
    eps_nota_id: number;
    id_nota_hoja: number;
    nota_hoja: string;
    cups: string;
    procedimiento: string;
    tarifa: number;
  }>;
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

// ─── GET / READ ──────────────────────────────────────────────────────

/** Fetch all EpsContratado from SQLite. */
export async function fetchEps(): Promise<EpsContratado[]> {
  return apiGet<EpsContratado[]>("/api/eps");
}

/** Fetch all Procedimiento (CUPS) from SQLite. */
export async function fetchProcSqlite(): Promise<ProcedimientoSqlite[]> {
  return apiGet<ProcedimientoSqlite[]>("/api/procedimientos");
}

/** Fetch the chain EpsContratado → Procedimientos for a given EPS id. */
export async function fetchProcedimientosPorEps(epsId: number): Promise<EpsProcedimientosChain> {
  return apiGet<EpsProcedimientosChain>(`/api/eps/${epsId}/procedimientos`);
}

/** Fetch all NotaHoja from SQLite. */
export async function fetchNotasHoja(): Promise<NotaHoja[]> {
  return apiGet<NotaHoja[]>("/api/notas-hoja");
}

// ─── POST / CREATE ──────────────────────────────────────────────────

/** Create a new EpsContratado. */
export async function createEps(data: {
  cod_contrato: string;
  eps: string;
  regimen?: string;
}): Promise<EpsContratado> {
  return apiPost<EpsContratado>("/api/eps", data);
}

/** Create a new Procedimiento (CUPS) in SQLite. */
export async function createProcSqlite(data: {
  cups: string;
  procedimiento: string;
}): Promise<ProcedimientoSqlite> {
  return apiPost<ProcedimientoSqlite>("/api/procedimientos", data);
}

/** Create a new NotaHoja in SQLite. */
export async function createNotaHoja(data: { nota: string }): Promise<NotaHoja> {
  return apiPost<NotaHoja>("/api/notas-hoja", data);
}

// ─── PUT / UPDATE ───────────────────────────────────────────────────

/** Update an existing NotaHoja in SQLite. */
export async function updateNotaHoja(
  id: number,
  data: Partial<{ nota: string }>,
): Promise<NotaHoja> {
  return apiPut<NotaHoja>(`/api/notas-hoja/${id}`, data);
}

/** Update an existing EpsContratado. */
export async function updateEps(
  id: number,
  data: Partial<{ cod_contrato: string; eps: string; regimen: string }>,
): Promise<EpsContratado> {
  return apiPut<EpsContratado>(`/api/eps/${id}`, data);
}

/** Update an existing Procedimiento (CUPS) in SQLite. */
export async function updateProcSqlite(
  id: number,
  data: Partial<{ cups: string; procedimiento: string }>,
): Promise<ProcedimientoSqlite> {
  return apiPut<ProcedimientoSqlite>(`/api/procedimientos/${id}`, data);
}

// ─── DELETE ──────────────────────────────────────────────────────────

export interface DependenciasNotaHoja {
  eps_nota_count: number;
  notas_tecnicas_count: number;
  eps_vinculadas: Array<{ id: number; cod_contrato: string; eps: string }>;
  procedimientos_vinculados: Array<{ id: number; cups: string; procedimiento: string }>;
}

export interface VinculacionesNota {
  nota: NotaHoja;
  procedimientos: Array<{
    nt_id: number;
    id: number;
    cups: string;
    procedimiento: string;
    tarifa: number | null;
  }>;
  eps_vinculadas: Array<{ eps_nota_id: number; id: number; cod_contrato: string; eps: string }>;
}

/** Fetch dependencias for a NotaHoja before deleting. */
export async function fetchNotaHojaDependencias(id: number): Promise<DependenciasNotaHoja> {
  return apiGet<DependenciasNotaHoja>(`/api/notas-hoja/${id}/dependencias`);
}

/** Fetch vinculaciones (procedimientos + EPS) for a NotaHoja. */
export async function fetchVinculacionesNota(id: number): Promise<VinculacionesNota> {
  return apiGet<VinculacionesNota>(`/api/notas-hoja/${id}/vinculaciones`);
}

/** Vincular un procedimiento a una NotaHoja (solo NotasTecnicas, sin EPS). */
export async function vincularProcedimientoANota(
  notaId: number,
  data: { id_procedimiento: number; tarifa?: number },
): Promise<{ nt_id: number }> {
  return apiPost<{ nt_id: number }>(
    `/api/notas-hoja/${notaId}/vincular-procedimiento`, data,
  );
}

/** Vincular una EPS a una NotaHoja (crea EpsNota). */
export async function vincularEpsANota(
  notaId: number,
  data: { id_eps_contratado: number },
): Promise<{ eps_nota_id: number }> {
  return apiPost<{ eps_nota_id: number }>(
    `/api/notas-hoja/${notaId}/vincular-eps`, data,
  );
}

/** Eliminar vínculo EPS-Nota. */
export async function deleteEpsNota(id: number): Promise<void> {
  return apiDelete(`/api/eps-nota/${id}`);
}

/** Actualizar tarifa de una nota técnica. */
export async function updateNotasTecnicas(
  id: number,
  data: { tariff?: number },
): Promise<{ tariff: number }> {
  return apiPut<{ tariff: number }>(`/api/notas-tecnicas/${id}`, data);
}

/** Eliminar una nota técnica (desvincula procedimiento de nota). */
export async function deleteNotasTecnicas(id: number): Promise<void> {
  return apiDelete(`/api/notas-tecnicas/${id}`);
}

/** Delete a NotaHoja in SQLite by id. */
export async function deleteNotaHoja(id: number): Promise<void> {
  return apiDelete(`/api/notas-hoja/${id}`);
}

/** Delete an EpsContratado by id. */
export async function deleteEps(id: number): Promise<void> {
  return apiDelete(`/api/eps/${id}`);
}

/** Delete a Procedimiento (CUPS) in SQLite by id. */
export async function deleteProcSqlite(id: number): Promise<void> {
  return apiDelete(`/api/procedimientos/${id}`);
}

// ─── COMPOUND ───────────────────────────────────────────────────────

/** Vincular procedimiento to EPS (creates EpsNota + NotasTecnicas atomically). */
export async function vincularProcedimiento(
  epsId: number,
  data: { id_nota_hoja: number; id_procedimiento: number; tarifa: number },
): Promise<{
  eps_nota: { id: number; id_nota_hoja: number; id_eps_contratado: number };
  notas_tecnicas: { id: number; id_procedimiento: number; id_nota_hoja: number; tarifa: number };
}> {
  return apiPost(`/api/eps/${epsId}/vincular-procedimiento`, data);
}
