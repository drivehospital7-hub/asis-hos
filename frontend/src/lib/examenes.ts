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
  /** Cantidad por ítem (EX-21). Opcional: ausente = 1 (registros legacy 5-campos). */
  cantidad?: number;
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

// ─── Listado search (EX-29) ─────────────────────────────────────────────

/**
 * Listado query normalization: trim + uppercase AFTER accent folding
 * (NFD + strip combining marks, `\p{M}`), so "Álvaro Ñúñez" ≈ "alvaro nunez".
 * Independent of `normalizeSearch` — Consulta EX-6 semantics stay frozen.
 */
export function normalizeListadoQuery(q: string): string {
  return (q ?? "")
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .trim()
    .toUpperCase();
}

/**
 * Filter prefacturas by substring on paciente | cedula | facturador or ANY
 * item cod/nom (folded). sin-fecha records match normally (hora not searched).
 * Blank query → the input listado unchanged (same reference).
 */
export function searchListado(listado: Prefactura[], query: string): Prefactura[] {
  const q = normalizeListadoQuery(query);
  if (!q) return listado;
  return listado.filter((pf) => {
    if (normalizeListadoQuery(pf.paciente).includes(q)) return true;
    if (normalizeListadoQuery(pf.cedula).includes(q)) return true;
    if (normalizeListadoQuery(pf.facturador).includes(q)) return true;
    return pf.items.some(
      (it) =>
        normalizeListadoQuery(it.cod).includes(q) ||
        normalizeListadoQuery(it.nom).includes(q),
    );
  });
}

// ─── Listado pagination (EX-31) ─────────────────────────────────────────

/** Records-per-page options for the Listado (no hardcoding in page.tsx). */
export const LISTADO_PAGE_SIZES = [25, 50, 100] as const;

/** Default page size; any filter/search change resets to this (EX-31). */
export const DEFAULT_LISTADO_PAGE_SIZE = 25;

// ─── Date-range filter (EX-30) ──────────────────────────────────────────

/**
 * Inclusive range membership on ISO `yyyy-mm-dd` bounds (A10): dayKey is
 * lexicographically comparable to ISO dates (zero-padded). sin-fecha records
 * are NEVER in range (A5 — no date → cannot be "in range"). Both bounds null
 * → true for dated records. One-sided bounds are open-ended; to < from
 * naturally yields false for every dayKey.
 */
export function inRange(
  pf: Prefactura,
  from: string | null,
  to: string | null,
): boolean {
  const dayKey = listadoFechaInfo(pf.hora).dayKey;
  if (dayKey === "sin-fecha") return false;
  if (from !== null && dayKey < from) return false;
  if (to !== null && dayKey > to) return false;
  return true;
}

/** Keep only prefacturas whose date falls within [from, to] (EX-30). */
export function filterByDateRange(
  listado: Prefactura[],
  from: string | null,
  to: string | null,
): Prefactura[] {
  return listado.filter((pf) => inRange(pf, from, to));
}

// ─── Current-month default range (EX-32) ────────────────────────────────

/** ISO `yyyy-mm-dd` inclusive range bounds for the Listado toolbar. */
export interface DateRange {
  from: string;
  to: string;
}

/**
 * Day-1..last-day of the month containing `now`, as ISO `yyyy-mm-dd`
 * (EX-32). `now` is injectable for deterministic tests. ISO strings are
 * required: `<input type="date">` values ARE ISO and `inRange` compares
 * dayKey lexicographically — dd/mm/yyyy would break both (A10).
 */
export function currentMonthRange(now: Date = new Date()): DateRange {
  const year = now.getFullYear();
  const month = now.getMonth() + 1; // 1-based for display/padding
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  return {
    from: `${year}-${String(month).padStart(2, "0")}-01`,
    to: `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`,
  };
}

// ─── Pagination (EX-31) ─────────────────────────────────────────────────

export interface Page<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

/**
 * Slice a filtered listado into pages (EX-31). Page is clamped into
 * 1..totalPages; empty input → `{ items: [], page: 1, totalPages: 0 }`.
 * Page size is floored to ≥ 1. Never mutates the input.
 */
export function paginate<T>(records: T[], page: number, pageSize: number): Page<T> {
  const size = Math.max(1, Math.trunc(pageSize) || 1);
  const total = records.length;
  const totalPages = total === 0 ? 0 : Math.max(1, Math.ceil(total / size));
  const clamped =
    total === 0 ? 1 : Math.min(Math.max(1, Math.trunc(page) || 1), totalPages);
  const start = (clamped - 1) * size;
  return {
    items: records.slice(start, start + size),
    page: clamped,
    pageSize: size,
    total,
    totalPages,
  };
}

// ─── Descending sort + view composition (EX-31/33, D1/D2/D4) ────────────

/**
 * Minutes-since-midnight from an es-CO hora `dd/mm/yyyy hh:mm`; untimed
 * (date-only) horas → 0 so they sort last within their day (EX-33).
 */
function horaMinutes(hora: string): number {
  const match = String(hora || "").match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{1,2})/);
  if (!match) return 0;
  return Number(match[4]) * 60 + Number(match[5]);
}

/**
 * Sort the listado date-descending (most recent first), time-descending
 * within the same day, sin-fecha records last — stable for equal keys
 * (EX-33, D4). Applied to the FULL displayed set BEFORE pagination so pages
 * stay contiguous most-recent-first. Non-mutating (ES2019 stable sort).
 */
export function sortByDateDesc(listado: Prefactura[]): Prefactura[] {
  return [...listado].sort((a, b) => {
    const ka = listadoFechaInfo(a.hora).dayKey;
    const kb = listadoFechaInfo(b.hora).dayKey;
    if (ka === "sin-fecha" || kb === "sin-fecha") {
      if (ka === kb) return 0; // both sin-fecha → input order (stable)
      return ka === "sin-fecha" ? 1 : -1;
    }
    if (ka !== kb) return ka < kb ? 1 : -1; // ISO dayKey desc
    return horaMinutes(b.hora) - horaMinutes(a.hora); // time desc within day
  });
}

/**
 * EX-11 pipeline composition: date range (D2 — both bounds empty → the raw
 * listado incl. sin-fecha, `filterByDateRange` skipped entirely) → global
 * search on the FULL listado while the query is non-blank (D1 — the active
 * range is ignored) → descending sort (D4). Pure; the page memo calls this
 * once and derives rowNumbers / paginate / CSV from its output.
 */
export function composeListadoView(
  listado: Prefactura[],
  opts: { from: string | null; to: string | null; query: string },
): Prefactura[] {
  const ranged =
    opts.from !== null || opts.to !== null
      ? filterByDateRange(listado, opts.from, opts.to)
      : listado;
  const displayed = normalizeListadoQuery(opts.query)
    ? searchListado(listado, opts.query)
    : ranged;
  return sortByDateDesc(displayed);
}

// ─── Listado numbering / totals / tooltip (EX-11) ───────────────────────

/**
 * Screen row N° per prefactura: continuous 1-based over the FULL filtered
 * set (pre-pagination, stable across pages). CSV (EX-14) numbers one row per
 * ITEM, so a prefactura's screen N° = its FIRST item's CSV N° =
 * 1 + Σ items.length of all preceding prefacturas (#1682 parity rule).
 */
export function listadoRowNumbers(filtered: Prefactura[]): Map<string, number> {
  const map = new Map<string, number>();
  let n = 0;
  for (const pf of filtered) {
    map.set(pf.id, n + 1);
    n += pf.items.length;
  }
  return map;
}

export interface DayTotals {
  records: number;
  items: number;
  cantidad: number;
}

/**
 * Day-section totals header: `N registros · M ítems · K cantidades`,
 * computed over the page slice passed in (EX-11). K sums normalized
 * item cantidad (absent/NaN/<1 → 1 via normalizeItem).
 */
export function daySectionTotals(entries: Prefactura[]): DayTotals {
  let items = 0;
  let cantidad = 0;
  for (const pf of entries) {
    items += pf.items.length;
    for (const it of pf.items) cantidad += normalizeItem(it).cantidad;
  }
  return { records: entries.length, items, cantidad };
}

/**
 * Badge hover tooltip: up to 8 lines `cod — nom (x cantidad)`, capped with
 * `+N más` when the prefactura has more items (EX-11 tooltip cap).
 */
export function badgeTooltip(items: PrefacturaItem[]): string {
  const lines = items
    .slice(0, 8)
    .map((it) => `${it.cod} — ${it.nom} (x ${normalizeItem(it).cantidad})`);
  const extra = items.length - 8;
  if (extra > 0) lines.push(`+${extra} más`);
  return lines.join("\n");
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
      cantidad: 1,
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
  items: Array<{
    cod: string;
    nom: string;
    neps?: string;
    mall?: string;
    emss?: string;
    cantidad?: number;
  }>;
  /** Injectable clock for deterministic tests. */
  now?: Date;
}

/** ítem con cantidad garantizada (post-normalización). */
export type NormalizedPrefacturaItem = PrefacturaItem & { cantidad: number };

/**
 * Normaliza la cantidad de un ítem (EX-27): ausente/NaN/<1 → 1;
 * entero ≥1 pasa tal cual; fracciones se truncan (2.9 → 2). Único clamp
 * read-time del frontend — el store queda verbatim (R4-001).
 */
export function normalizeItem(item: PrefacturaItem): NormalizedPrefacturaItem {
  const q = Math.trunc(Number(item.cantidad));
  return { ...item, cantidad: Number.isFinite(q) && q >= 1 ? q : 1 };
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
    items: input.items.map((item) =>
      normalizeItem({
        cod: item.cod,
        nom: item.nom,
        neps: item.neps || "",
        mall: item.mall || "",
        emss: item.emss || "",
        cantidad: item.cantidad,
      }),
    ),
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
 * Write-action visibility from `can_write` (EX-17, D6). Read-only users keep
 * save/edit/save-modal/per-item-removal (all read-level `examenes`) and the
 * cart "Vaciar" (`clear` — client-side-only draft state, ungated like ×
 * removeFromCart); only the Admin tab and whole-record delete need
 * `examenes:write`. UI hiding is NOT security — the API enforces `examenes`
 * vs `examenes:write` per endpoint.
 */
export function resolveUiActions(can_write: boolean): UiActions {
  return {
    admin: can_write,
    save: true,
    edit: true,
    delete: can_write,
    clear: true,
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

/** Pure-JS SHA-256 hex (fallback for non-secure contexts where crypto.subtle is unavailable). */
function sha256HexPureJs(bytes: Uint8Array): string {
  const K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);
  let H = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
  const ml = bytes.length * 8;
  const padLen = bytes.length % 64 < 56 ? 56 - (bytes.length % 64) : 120 - (bytes.length % 64);
  const padded = new Uint8Array(bytes.length + padLen + 8);
  padded.set(bytes);
  padded[bytes.length] = 0x80;
  const view = new DataView(padded.buffer);
  view.setUint32(padded.length - 4, ml >>> 0, false);
  view.setUint32(padded.length - 8, Math.floor(ml / 0x100000000), false);
  const w = new Uint32Array(64);
  for (let i = 0; i < padded.length; i += 64) {
    for (let j = 0; j < 16; j++) w[j] = view.getUint32(i + j * 4, false);
    for (let j = 16; j < 64; j++) {
      const s0 = ((w[j - 15] >>> 7) | (w[j - 15] << 25)) ^ ((w[j - 15] >>> 18) | (w[j - 15] << 14)) ^ (w[j - 15] >>> 3);
      const s1 = ((w[j - 2] >>> 17) | (w[j - 2] << 15)) ^ ((w[j - 2] >>> 19) | (w[j - 2] << 13)) ^ (w[j - 2] >>> 10);
      w[j] = (w[j - 16] + s0 + w[j - 7] + s1) >>> 0;
    }
    let [a, b, c, d, e, f, g, h] = H;
    for (let j = 0; j < 64; j++) {
      const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + K[j] + w[j]) >>> 0;
      const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;
      h = g; g = f; f = e; e = (d + temp1) >>> 0; d = c; c = b; b = a; a = (temp1 + temp2) >>> 0;
    }
    H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0; H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
    H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0; H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
  }
  return Array.from(H).map((v) => v.toString(16).padStart(8, "0")).join("");
}

/** SHA-256 hex canónico (base_hash del POST). Resilient to non-secure contexts (plain HTTP). */
export async function baseHash(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  const canUseSubtle =
    typeof crypto !== "undefined" &&
    !!(crypto as unknown as { subtle?: SubtleCrypto }).subtle?.digest &&
    (typeof window === "undefined" || (window as unknown as { isSecureContext?: boolean }).isSecureContext !== false);
  if (canUseSubtle) {
    try {
      const digest = await crypto.subtle.digest("SHA-256", bytes);
      return Array.from(new Uint8Array(digest))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
    } catch {
      // fall through to pure-JS
    }
  }
  return sha256HexPureJs(bytes);
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

export type DeleteResult = "ok" | "conflict" | "error";

/**
 * DELETE whole-record con concurrencia optimista (EX-2): envía `base_hash`
 * del arreglo en el que el cliente basó su copia. 409 (estado cambió) y 404
 * (registro ya no existe = copia stale) → "conflict"; el caller avisa y
 * recarga. Sin `baseArr` → DELETE legacy sin body. 200 → "ok"; cualquier
 * otro fallo o error de red → "error".
 */
export async function deletePrefactura(
  id: string,
  baseListado?: unknown[],
): Promise<DeleteResult> {
  try {
    const payload =
      baseListado === undefined ? undefined : JSON.stringify({ base_hash: await baseHash(baseListado) });
    const res = await fetch(`/api/listado/${encodeURIComponent(id)}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: payload,
    });
    if (res.status === 409 || res.status === 404) return "conflict";
    if (!res.ok) return "error";
    const body = await res.json();
    return body?.status === "success" ? "ok" : "error";
  } catch {
    return "error";
  }
}