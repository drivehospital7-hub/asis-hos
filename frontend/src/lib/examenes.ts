/**
 * Pure logic for the Exámenes (Lab Prefactura) module.
 *
 * Port of `Laboratorio_HospitalOrito_v5.html` helpers (search, month grouping,
 * flat→grouped migration at source HTML:561, facturador completion, prefactura
 * building) into testable, side-effect-free functions. UI state lives in
 * `pages/examenes/page.tsx`; this module only transforms data.
 */

// ─── Types ────────────────────────────────────────────────────────────

export interface Examen {
  cod: string;
  nom: string;
  neps: string;
  mall: string;
  emss: string;
}

export interface PrefacturaItem {
  cod: string;
  nom: string;
  neps: string;
  mall: string;
  emss: string;
}

export interface Prefactura {
  id: string;
  paciente: string;
  cedula: string;
  facturador: string;
  hora: string;
  items: PrefacturaItem[];
}

/** Flat legacy record (source listado before grouping). */
export interface FlatExamen {
  cod: string;
  nom: string;
  neps?: string;
  mall?: string;
  emss?: string;
  paciente: string;
  cedula?: string;
  facturador: string;
  hora?: string;
}

export interface FechaInfo {
  monthKey: string;
  dayKey: string;
  sortKey: number;
  monthLabel: string;
  dayLabel: string;
}

export interface UiActions {
  admin: boolean;
  save: boolean;
  edit: boolean;
  delete: boolean;
  clear: boolean;
}

// ─── Search (EX-6) ─────────────────────────────────────────────────────

/** Trim + uppercase, mirroring the source `buscar()` normalization. */
export function normalizeSearch(q: string): string {
  return (q ?? "").trim().toUpperCase();
}

/**
 * CUPS search: exact `cod` match wins; otherwise substring on `cod` or
 * `nom` (uppercased). Blank query → empty array (caller shows the error).
 */
export function searchExamenes(examenes: Examen[], query: string): Examen[] {
  const q = normalizeSearch(query);
  if (!q) return [];
  const exact = examenes.find((e) => e.cod === q);
  if (exact) return [exact];
  return examenes.filter(
    (e) => e.cod.includes(q) || e.nom.toUpperCase().includes(q),
  );
}

// ─── IDs ───────────────────────────────────────────────────────────────

/** `pf-<timestamp>-<4 random chars>` (source `genPrefacturaId`). */
export function genPrefacturaId(): string {
  return "pf-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6);
}

// ─── Migration (D5, EX-18 — source HTML:561 `migrateListado`) ────────────

/**
 * Groups flat legacy records into prefacturas keyed by
 * `(paciente|facturador).toUpperCase()`. Item flags fall back to "".
 */
export function migrateFlatToGrouped(flat: FlatExamen[]): Prefactura[] {
  const groups = new Map<string, Prefactura>();
  for (const r of flat) {
    const key = (r.paciente + "|" + r.facturador).toUpperCase();
    if (!groups.has(key)) {
      groups.set(key, {
        id: genPrefacturaId(),
        paciente: r.paciente,
        cedula: r.cedula ?? "",
        facturador: r.facturador,
        hora: r.hora ?? "",
        items: [],
      });
    }
    groups.get(key)!.items.push({
      cod: r.cod,
      nom: r.nom,
      neps: r.neps || "",
      mall: r.mall || "",
      emss: r.emss || "",
    });
  }
  return [...groups.values()];
}

// ─── Month grouping (EX-11) ────────────────────────────────────────────

/** Capitalize the first letter (source `capitalizarInicial`). */
export function capitalizeInitial(value: string): string {
  const text = String(value || "");
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

/**
 * Parse es-CO `dd/mm/yyyy` (with optional time) from a prefactura hora.
 * Round-trip validation rejects impossible dates; unparseable → "sin-fecha"
 * (sortKey -Infinity so it sorts last, never dropped).
 */
export function listadoFechaInfo(hora: string | null | undefined): FechaInfo {
  const value = String(hora || "");
  const match = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s|$)/);
  if (match) {
    const day = Number(match[1]);
    const month = Number(match[2]);
    const year = Number(match[3]);
    const date = new Date(year, month - 1, day);
    if (
      date.getFullYear() === year &&
      date.getMonth() === month - 1 &&
      date.getDate() === day
    ) {
      return {
        monthKey: `${year}-${String(month).padStart(2, "0")}`,
        dayKey: `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
        sortKey: date.getTime(),
        monthLabel: capitalizeInitial(
          date.toLocaleDateString("es-CO", { month: "long", year: "numeric" }),
        ),
        dayLabel: capitalizeInitial(
          date.toLocaleDateString("es-CO", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric",
          }),
        ),
      };
    }
  }
  return {
    monthKey: "sin-fecha",
    dayKey: "sin-fecha",
    sortKey: -Infinity,
    monthLabel: "Fecha no disponible",
    dayLabel: "Fecha no disponible",
  };
}

/** Unique months present in the listado, newest-first (sin-fecha last). */
export function groupMonths(
  listado: Prefactura[],
): Array<{ monthKey: string; monthLabel: string }> {
  const monthMap = new Map<string, FechaInfo>();
  for (const pf of listado) {
    const info = listadoFechaInfo(pf.hora);
    if (!monthMap.has(info.monthKey)) monthMap.set(info.monthKey, info);
  }
  return [...monthMap.values()]
    .sort((a, b) => b.sortKey - a.sortKey)
    .map((m) => ({ monthKey: m.monthKey, monthLabel: m.monthLabel }));
}

/** Filter listado by month key; "todos" returns everything. */
export function filterByMonth(listado: Prefactura[], monthKey: string): Prefactura[] {
  if (monthKey === "todos" || !monthKey) return listado;
  return listado.filter((pf) => listadoFechaInfo(pf.hora).monthKey === monthKey);
}

// ─── Date/time formatters ───────────────────────────────────────────────

/** dd/mm/yyyy with zero padding (es-CO display). */
export function formatFechaEsCo(date: Date): string {
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${date.getFullYear()}`;
}

/**
 * dd/mm/yyyy hh:mm (24h, zero padded). Deterministic across environments
 * (the source's `toLocaleTimeString` is locale/ICU-dependent; the dd/mm/yyyy
 * date prefix — what grouping and CSV depend on — is preserved).
 */
export function formatHoraEsCo(date: Date): string {
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${date.getFullYear()} ${hh}:${mi}`;
}

// ─── Prefactura building (EX-10) ───────────────────────────────────────

export interface BuildPrefacturaInput {
  paciente: string;
  cedula: string;
  facturador: string;
  items: Array<{ cod: string; nom: string; neps?: string; mall?: string; emss?: string }>;
  /** Injectable clock for deterministic tests. */
  now?: Date;
}

/**
 * Build the prefactura pushed to the listado (source `verPrefacturaYAgregar`):
 * blank patient → "Sin nombre", cedula/facturador → "—"; item flags → "".
 */
export function buildPrefactura(input: BuildPrefacturaInput): Prefactura {
  const now = input.now ?? new Date();
  return {
    id: genPrefacturaId(),
    paciente: input.paciente.trim() || "Sin nombre",
    cedula: input.cedula.trim() || "—",
    facturador: input.facturador.trim() || "—",
    hora: formatHoraEsCo(now),
    items: input.items.map((item) => ({
      cod: item.cod,
      nom: item.nom,
      neps: item.neps || "",
      mall: item.mall || "",
      emss: item.emss || "",
    })),
  };
}

// ─── Display mapping (EX-11 sub-table) ──────────────────────────────────

/** X→SI, AUTH→AUTH, else "—" (listado item sub-table). */
export function tcDisplay(v: string | null | undefined): string {
  if (v === "X") return "SI";
  if (v === "AUTH") return "AUTH";
  return "—";
}

// ─── UI gating (EX-17) ──────────────────────────────────────────────────

/**
 * Write-action visibility from `can_write`. Read-only users keep CSV/print
 * (component renders those independently); Admin tab + all mutations are
 * gated here. UI hiding is NOT security — the API enforces `examenes:write`.
 */
export function resolveUiActions(can_write: boolean): UiActions {
  return {
    admin: can_write,
    save: can_write,
    edit: can_write,
    delete: can_write,
    clear: can_write,
  };
}

// ─── Optimistic concurrency (R4-001) ────────────────────────────────────

/**
 * Serialización canónica compartida con el backend (`examenes_store.file_hash`:
 * `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`), para
 * que `base_hash` del cliente coincida con el estado del servidor.
 */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return "[" + value.map((v) => canonicalJson(v)).join(",") + "]";
  }
  if (value !== null && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    return (
      "{" +
      keys.map((k) => JSON.stringify(k) + ":" + canonicalJson(obj[k])).join(",") +
      "}"
    );
  }
  return JSON.stringify(value);
}

/** SHA-256 hex canónico (base_hash del POST). */
export async function baseHash(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export type PostResult = "ok" | "conflict" | "error";

/**
 * POST full-array con concurrencia optimista: envía `base_hash` del arreglo en
 * el que el cliente basó su copia. 409 → "conflict" (no se escribió); el caller
 * avisa y recarga. Sin `baseArr` → POST legacy (arreglo plano).
 */
export async function postArray(
  url: string,
  arr: unknown[],
  baseArr?: unknown[],
): Promise<PostResult> {
  try {
    const payload =
      baseArr === undefined
        ? JSON.stringify(arr)
        : JSON.stringify({ data: arr, base_hash: await baseHash(baseArr) });
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
    });
    if (res.status === 409) return "conflict";
    if (!res.ok) return "error";
    const body = await res.json();
    return body?.status === "success" ? "ok" : "error";
  } catch {
    return "error";
  }
}