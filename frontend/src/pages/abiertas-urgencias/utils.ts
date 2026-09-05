import { NOMBRE_MAP, PATTERNS, HEADER_DETECTION } from "./constants";

// ─── Types ────────────────────────────────────────────────────────────

export interface ScheduleDay {
  dia: number;
  manana: string;
  tarde: string;
  noche: string;
}

export interface FacturaResult {
  fechaCrea: string;
  fechaEgreso: string;
  factura: string;
  estado: string;
  responsable: string;
  area: string;
  paciente: string;
  hcPendiente: string;
  _enviada?: boolean;
}

export interface ColumnIndexes {
  fechaCreaIdx: number;
  fechaEgresoIdx: number;
  facturaIdx: number;
  areaIdx: number;
  pacienteIdx: number;
  estadoIdx: number;
  hcPendienteIdx: number;
  fechaCierreIdx: number;
}

// ─── Pure Functions ───────────────────────────────────────────────────

/**
 * Parse pasted schedule TSV text into structured day array.
 * Normalizes line endings, joins multi-line quoted fields,
 * finds header row by "DIA"/"DÍA" keyword, and parses
 * tab-separated rows into ScheduleDay[].
 * Returns null if parsing fails.
 */
export function parseScheduleText(text: string): ScheduleDay[] | null {
  // Pre-normalize: join hyphenated line breaks inside time cells (e.g. "01:00 PM-\n07:00")
  // and normalize Windows line endings before the main split.
  const normalized = text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/-\s*\n\s*/g, "-")
    .replace(/\n\s*\n/g, "\n");
  const rawLines = normalized.split("\n");

  // Join multi-line quoted fields
  const mergedLines: string[] = [];
  let buffer = "";

  for (const line of rawLines) {
    const trimmed = line.trim();
    if (trimmed === "") continue;

    if (trimmed.startsWith('"') && buffer) {
      const quoteCount = (trimmed.match(/"/g) || []).length;
      buffer += "\t" + trimmed;
      if (quoteCount % 2 === 1 && trimmed.endsWith('"')) {
        mergedLines.push(buffer);
        buffer = "";
      }
    } else if (trimmed.startsWith('"') && !buffer) {
      buffer = trimmed;
    } else if (buffer) {
      buffer += " " + trimmed;
      if (trimmed.endsWith('"')) {
        mergedLines.push(buffer);
        buffer = "";
      }
    } else {
      mergedLines.push(trimmed);
    }
  }
  if (buffer) mergedLines.push(buffer);

  // Remove quotes
  const cleanLines = mergedLines.map((l) => l.replace(/"/g, ""));

  if (cleanLines.length < 2) return null;

  // Find header row: look for "DIA"/"DÍA"/"DI" as first column
  let headerIndex = -1;
  for (let i = 0; i < cleanLines.length; i++) {
    const first = (cleanLines[i].split("\t")[0] || "").toUpperCase().trim();
    if (first === "DIA" || first === "DÍA" || first === "DI") {
      headerIndex = i;
      break;
    }
  }

  // If no DIA header but first lines look like time headers (contain "AM"/"PM" or "07:00"),
  // treat them as header rows to skip. This handles pastes where the DIA column header
  // is empty and the first row is "07:00 AM-01:00 PM ..." split across quoted lines.
  const isFallback = headerIndex === -1;
  const timeHeaderPattern = /(?:0?7:00|01:00|0?1:00)\s*(?:AM|PM)/i;

  // Parse data rows
  const dataRows: ScheduleDay[] = [];
  const startIdx = headerIndex !== -1 ? headerIndex + 1 : 0;

  for (let i = startIdx; i < cleanLines.length; i++) {
    const line = cleanLines[i];
    // Skip any line that looks like a time header (contains time patterns) and is not a day row
    if (isFallback && timeHeaderPattern.test(line) && !/^\s*\d+\s*\t/.test(line)) {
      continue;
    }
    const parts = line.split("\t");
    if (parts.length < 4) {
      // Also try splitting by 2+ spaces if tabs were collapsed during copy (Excel sometimes uses spaces)
      const altParts = line.split(/\s{2,}/);
      if (altParts.length >= 4) {
        // Check if altParts looks like day row
        const altDay = parseInt(altParts[0], 10);
        if (!isNaN(altDay) && altDay >= 1 && altDay <= 31) {
          const altNameCols = [altParts[1], altParts[2], altParts[3]];
          if (isFallback && altNameCols.some((c) => /\d/.test(c))) continue;
          dataRows.push({
            dia: altDay,
            manana: (altParts[1] || "").trim(),
            tarde: (altParts[2] || "").trim(),
            noche: (altParts[3] || "").trim(),
          });
          continue;
        }
      }
      continue;
    }
    const dayNum = parseInt(parts[0], 10);
    if (isNaN(dayNum) || dayNum < 1 || dayNum > 31) continue;
    // In fallback mode (no DIA header), skip rows where any data column
    // contains time patterns (digits, colons, AM/PM) — those are headers,
    // not data rows. Data columns should be names (alphabetic only).
    const nameCols = [parts[1], parts[2], parts[3]];
    if (isFallback && nameCols.some((c) => /\d/.test(c))) continue;
    dataRows.push({
      dia: dayNum,
      manana: (parts[1] || "").trim(),
      tarde: (parts[2] || "").trim(),
      noche: (parts[3] || "").trim(),
    });
  }

  return dataRows.length > 0 ? dataRows : null;
}

/**
 * Auto-detect column indices from header labels or first-row value patterns.
 * Tries header labels first (fecha crea, fecha egreso, n factura, etc.),
 * falls back to value pattern matching (date regex, FEV prefix, estado pattern).
 * Handles FEV standalone prefix + next column digits concatenation.
 */
export function autoDetectColumns(
  headers: string[],
  primeraFila: string[],
): { cols: ColumnIndexes; foundLabels: Record<number, string> } {
  const cols: ColumnIndexes = {
    fechaCreaIdx: -1,
    fechaEgresoIdx: -1,
    facturaIdx: -1,
    areaIdx: -1,
    pacienteIdx: -1,
    estadoIdx: -1,
    hcPendienteIdx: -1,
    fechaCierreIdx: -1,
  };

  let dateCount = 0;
  const dateIdxs: number[] = [];
  const foundLabels: Record<number, string> = {};

  const searchIn = headers.length > 0 ? headers : primeraFila;

  for (let i = 0; i < searchIn.length; i++) {
    const val = (searchIn[i] || "").toString().trim().toLowerCase();
    const raw = (primeraFila[i] || "").toString().trim();

    // Detect by header label
    if (val) {
      if (val.includes(HEADER_DETECTION.fechaCrea)) {
        cols.fechaCreaIdx = i;
        foundLabels[i] = "Fecha Crea";
        continue;
      }
      if (
        val.includes(HEADER_DETECTION.fechaCierre) ||
        val === HEADER_DETECTION.fechaCierreAlt
      ) {
        cols.fechaCierreIdx = i;
        foundLabels[i] = "Fec. Cierre";
        continue;
      }
      if (
        val.includes(HEADER_DETECTION.fechaEgreso) ||
        val === HEADER_DETECTION.fechaEgresoAlt
      ) {
        cols.fechaEgresoIdx = i;
        foundLabels[i] = "Fecha Egreso";
        continue;
      }
      if (
        val.includes(HEADER_DETECTION.factura) ||
        val.includes(HEADER_DETECTION.facturaAlt)
      ) {
        cols.facturaIdx = i;
        foundLabels[i] = "N° Factura";
        continue;
      }
      if (val === HEADER_DETECTION.estado) {
        cols.estadoIdx = i;
        foundLabels[i] = "Estado";
        continue;
      }
      if (val.includes(HEADER_DETECTION.area)) {
        cols.areaIdx = i;
        foundLabels[i] = "Área";
        continue;
      }
      if (
        val.includes(HEADER_DETECTION.historia) ||
        val.includes(HEADER_DETECTION.historiaAlt)
      ) {
        // historiaIdx deprecated, use área
        continue;
      }
      if (val.includes(HEADER_DETECTION.paciente)) {
        cols.pacienteIdx = i;
        foundLabels[i] = "Paciente";
        continue;
      }
      if (
        val.includes(HEADER_DETECTION.hcPendiente) ||
        val.includes(HEADER_DETECTION.hcPendienteAlt)
      ) {
        cols.hcPendienteIdx = i;
        foundLabels[i] = "HC Pendiente";
        continue;
      }
    }

    // Detect by value in first data row
    if (raw && PATTERNS.date.test(raw)) {
      dateCount++;
      if (dateCount === 1) {
        cols.fechaCreaIdx = i;
        foundLabels[i] = "Fecha Crea";
      } else {
        // Track every later date; the egreso is resolved after the loop
        // (last date before the factura column).
        dateIdxs.push(i);
      }
    }

    // Detect factura: first with digits, then standalone prefix
    if (cols.facturaIdx === -1) {
      if (PATTERNS.factFull.test(raw)) {
        cols.facturaIdx = i;
        foundLabels[i] = "N° Factura";
      } else if (PATTERNS.factPrefixOnly.test(raw)) {
        // Standalone prefix (FEV alone) — check if next column has digits
        const nextRaw = (primeraFila[i + 1] || "").toString().trim();
        if (/^\d+$/.test(nextRaw)) {
          cols.facturaIdx = i;
          foundLabels[i] = "N° Factura";
        }
      }
    }

    if (PATTERNS.area.test(raw)) {
      cols.areaIdx = i;
      foundLabels[i] = "Área";
    }
    if (PATTERNS.estado.test(raw) && i !== cols.facturaIdx) {
      cols.estadoIdx = i;
      foundLabels[i] = "Estado";
    }
    if (PATTERNS.hc.test(raw)) {
      cols.hcPendienteIdx = i;
      foundLabels[i] = "HC Pendiente";
    }
  }

  // Egreso: the LAST date column before the factura column. In the real
  // export the egreso sits right before the FEV number (index 9); Cerrada
  // rows may carry an extra cierre date before it (index 8) and Abierta
  // rows may have an empty slot there. Late audit dates after the factura
  // column must not win.
  if (cols.fechaEgresoIdx === -1 && dateIdxs.length > 0) {
    const beforeFactura =
      cols.facturaIdx !== -1
        ? dateIdxs.filter((d) => d < cols.facturaIdx)
        : dateIdxs;
    const egresoIdx =
      beforeFactura.length > 0
        ? beforeFactura[beforeFactura.length - 1]
        : dateIdxs[0];
    if (egresoIdx !== cols.fechaCreaIdx) {
      cols.fechaEgresoIdx = egresoIdx;
      foundLabels[egresoIdx] = "Fecha Egreso";
    }
  }

  // Paciente: column not detected as something else that looks like a name
  for (let i = 0; i < primeraFila.length; i++) {
    if (
      i === cols.fechaCreaIdx ||
      i === cols.fechaEgresoIdx ||
      i === cols.facturaIdx ||
      i === cols.areaIdx ||
      i === cols.estadoIdx ||
      i === cols.hcPendienteIdx
    )
      continue;
    const raw = (primeraFila[i] || "").toString().trim();
    if (raw && PATTERNS.name.test(raw) && raw.split(/\s+/).length >= 3) {
      cols.pacienteIdx = i;
      foundLabels[i] = "Paciente";
      break;
    }
  }

  return { cols, foundLabels };
}

/**
 * Parse a date string in dd/mm/yyyy hh:mm:ss format.
 * Returns Date object or null if parsing fails.
 */
function parseDate(str: string): Date | null {
  if (!str || !str.trim()) return null;
  const parts = str
    .trim()
    .match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$/);
  if (!parts) return null;
  return new Date(
    +parts[3],
    +parts[2] - 1,
    +parts[1],
    +parts[4],
    +parts[5],
    +parts[6],
  );
}

/**
 * Determina el responsable para una factura según fecha de creación y egreso.
 *
 * Reglas de negocio:
 * - 30-min reception rule: mañana 06:30–12:29, tarde 12:30–18:29, noche 18:30–06:29
 * - Night crosses midnight: egreso < 06:30 → lookup `noche` of previous day
 * - Returns "Sin Egreso" if no egreso or egreso <= creación
 * - Returns "Sin horario" when no schedule for egreso month
 * - Maps short name via NOMBRE_MAP
 */
export function calcularResponsable(
  fechaCreaStr: string,
  fechaEgresoStr: string,
  cronograma: ScheduleDay[] | null,
): string {
  // 1. Parse dates
  if (!fechaCreaStr || !fechaCreaStr.trim()) return "—";

  const fechaCrea = parseDate(fechaCreaStr);
  if (!fechaCrea) return "—";

  // 2. Check if egreso exists
  if (!fechaEgresoStr || !fechaEgresoStr.trim()) return "Sin Egreso";

  const fechaEgreso = parseDate(fechaEgresoStr);
  if (!fechaEgreso) {
    console.error("[FRONT][ERROR] Parse fecha egreso fallo:", fechaEgresoStr);
    return "Sin horario";
  }

  // 3. If egreso <= crea → patient still in room
  if (fechaEgreso <= fechaCrea) return "Sin Egreso";

  // 4. Determine shift by egreso time
  const dia = fechaEgreso.getDate();
  const hora = fechaEgreso.getHours();
  const minutos = fechaEgreso.getMinutes();
  const horaMinutos = hora + minutos / 60;

  type TurnoKey = "manana" | "tarde" | "noche";
  let turno: TurnoKey;
  let diaBuscar = dia;

  if (horaMinutos >= 6.5 && horaMinutos < 12.5) {
    turno = "manana";
  } else if (horaMinutos >= 12.5 && horaMinutos < 18.5) {
    turno = "tarde";
  } else {
    turno = "noche";
    // Night crosses midnight: egreso before 06:30 → previous day's night
    if (horaMinutos < 6.5) {
      diaBuscar = dia - 1;
      // Month-boundary: 01/09 00:01 → diaBuscar 0 → should be last day of previous month
      if (diaBuscar < 1) {
        // Last day of previous month (e.g. 31/08 for 01/09)
        const prevMonthLastDay = new Date(fechaEgreso.getFullYear(), fechaEgreso.getMonth(), 0).getDate();
        diaBuscar = prevMonthLastDay;
      }
    }
  }

  // 5. Lookup in cronograma
  if (!cronograma || cronograma.length === 0) return "Sin horario";

  const diaData = cronograma.find((d) => d.dia === diaBuscar);
  if (!diaData) return "Día " + diaBuscar + " sin asignación";

  const nombreCorto = diaData[turno];
  if (!nombreCorto) return "Sin turno";

  // 6. Map to full name
  const nombreNormalizado = NOMBRE_MAP[nombreCorto.toUpperCase().trim()];
  return nombreNormalizado || nombreCorto;
}

// ─── Shift-counting helpers ────────────────────────────────────────────

type ShiftKey = "manana" | "tarde" | "noche";

const SLOT_ORDER: ReadonlyArray<[ShiftKey, number]> = [
  ["manana", 0],
  ["tarde", 1],
  ["noche", 2],
] as const;

/** Reverse map: full name → short name, built once from NOMBRE_MAP. */
const REVERSE_NOMBRE_MAP: Record<string, string> = {};
for (const [shortName, fullName] of Object.entries(NOMBRE_MAP)) {
  REVERSE_NOMBRE_MAP[fullName] = shortName;
}

/**
 * Returns the shift slot index for a given hour-minute value.
 * 06:30–12:29 → 0 (manana), 12:30–18:29 → 1 (tarde), 18:30–06:29 → 2 (noche).
 * Uses the same boundaries as `calcularResponsable`.
 */
function slotIndex(hourMin: number): 0 | 1 | 2 {
  if (hourMin >= 6.5 && hourMin < 12.5) return 0;
  if (hourMin >= 12.5 && hourMin < 18.5) return 1;
  return 2;
}

/**
 * Returns true if the same responsible person appears in ≥2 completed
 * shifts counting from the egreso's own shift (inclusive), according
 * to the loaded schedule. The current in-progress shift is NOT counted.
 *
 * Falls back to false if egreso is in a different month/year from now.
 */
export function masDeDosTurnosMismoResponsable(
  fechaEgreso: string,
  responsable: string,
  schedule: ScheduleDay[],
  now?: Date,
): boolean {
  const egreso = parseDate(fechaEgreso);
  const nowDate = now ?? new Date();

  // Guard: same month/year
  if (
    !egreso ||
    egreso.getMonth() !== nowDate.getMonth() ||
    egreso.getFullYear() !== nowDate.getFullYear()
  ) {
    return false;
  }

  // Resolve egreso shift index with night correction
  const hourMin = egreso.getHours() + egreso.getMinutes() / 60;
  let egresoSlot = slotIndex(hourMin);
  let egresoDay = egreso.getDate();
  if (hourMin < 6.5) {
    // Before 06:30 → belongs to previous day's noche
    egresoSlot = 2;
    egresoDay -= 1;
  }
  const egresoIdx = egresoDay * 3 + egresoSlot;

  // Resolve "now" shift index with night correction
  const hourMinNow = nowDate.getHours() + nowDate.getMinutes() / 60;
  let nowSlot = slotIndex(hourMinNow);
  let nowDay = nowDate.getDate();
  if (hourMinNow < 6.5) {
    nowSlot = 2;
    nowDay -= 1;
  }
  const nowIdx = nowDay * 3 + nowSlot;

  // Use reverse name map (fullName → shortName)
  const shortName = REVERSE_NOMBRE_MAP[responsable] ?? responsable;

  // Count matched shifts: egresoIdx inclusive, nowIdx exclusive
  let count = 0;
  for (const day of schedule) {
    for (const [key, idx] of SLOT_ORDER) {
      const shiftIdx = day.dia * 3 + idx;
      if (shiftIdx < egresoIdx) continue;
      if (shiftIdx >= nowIdx) continue;
      const slotValue = (day[key] ?? "").toUpperCase().trim();
      if (slotValue === shortName || slotValue === responsable) {
        count++;
      }
    }
  }

  return count >= 2;
}

// ─── Sin Egreso Guard ────────────────────────────────────────────────

export interface SinEgresoButtonConfig {
  disabled: boolean;
  title: string;
}

/**
 * Returns the button configuration for the "Enviar a Control" action.
 * The button must be disabled (with an explanatory tooltip) when the
 * factura has no responsable asignado ("Sin Egreso"), when its estado
 * is "Cerrada", or when no horario exists for the egreso month ("Sin horario").
 */
export function getSinEgresoButtonConfig(
  isSinEgreso: boolean,
  estado?: string,
  isSinHorario?: boolean,
): SinEgresoButtonConfig {
  if (isSinHorario) {
    return {
      disabled: true,
      title: "Sin horario: cargue horario de ese mes",
    };
  }
  if (isSinEgreso) {
    return {
      disabled: true,
      title: "Sin egreso — no hay responsable asignado",
    };
  }
  if (estado && estado.trim().toLowerCase() === "cerrada") {
    return {
      disabled: true,
      title: "Factura cerrada — no se puede enviar",
    };
  }
  return {
    disabled: false,
    title: "Enviar a Control de Errores",
  };
}

// ─── Filter Utilities ────────────────────────────────────────────────

/**
 * Extract unique, alphabetically sorted responsables from results.
 * Null/empty values are normalized to "—".
 */
export function getUniqueResponsables(results: FacturaResult[]): string[] {
  if (!results || results.length === 0) return [];
  return Array.from(
    new Set(results.map((r) => r.responsable || "—")),
  ).sort();
}

/**
 * Filter results by responsable when a filter is active.
 * Returns the original array (same reference) when filter is empty ("Todos").
 * Returns null when results is null.
 */
export function filterResultsByResponsable(
  results: FacturaResult[] | null,
  filterResponsable: string,
): FacturaResult[] | null {
  if (!results) return null;
  if (!filterResponsable) return results;
  return results.filter((r) => r.responsable === filterResponsable);
}

// ─── Utility Functions (clipboard, escape) ────────────────────────────

/** Escape HTML special characters. */
export function escapeHtml(text: string | null | undefined): string {
  if (text == null) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/** Write text to clipboard with fallback for HTTP and older browsers. */
function writeClipboard(text: string): Promise<void> {
  if (!navigator.clipboard) {
    // navigator.clipboard is undefined on HTTP pages
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    return Promise.resolve();
  }
  return navigator.clipboard.writeText(text).catch(() => {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  });
}

/** Copy schedule table as TSV to clipboard. */
export async function copiarHorario(
  cronogramaDias: ScheduleDay[],
  showToast: (msg: string) => void,
): Promise<void> {
  if (!cronogramaDias || cronogramaDias.length === 0) {
    showToast("No hay horario para copiar.");
    return;
  }
  const headers = ["Día", "07:00-13:00", "13:00-19:00", "19:00-07:00"];
  const lines = [headers.join("\t")];
  for (const row of cronogramaDias) {
    lines.push(
      [row.dia, row.manana || "", row.tarde || "", row.noche || ""].join(
        "\t",
      ),
    );
  }
  const text = lines.join("\n");
  await writeClipboard(text);
  showToast(
    "✅ " + cronogramaDias.length + " filas copiadas al portapapeles",
  );
}

/** Copy results table as TSV to clipboard, including an Envío status column. */
export async function copiarResultados(
  results: FacturaResult[],
  envioExistentes: Set<string>,
  envioEnviadas: Set<string>,
  showToast: (msg: string) => void,
): Promise<void> {
  if (!results || results.length === 0) {
    showToast("No hay datos para copiar.");
    return;
  }

  const headers = [
    "Fecha Crea",
    "Fecha Egreso",
    "N° Factura",
    "Estado",
    "Responsable",
    "Área",
    "Paciente",
    "HC Pendiente",
    "Envío",
  ];

  const lines = [headers.join("\t")];
  for (const r of results) {
    let envio = "";
    if (r._enviada || envioEnviadas.has(r.factura)) envio = "Enviado";
    else if (envioExistentes.has(r.factura))
      envio = "Ya existe";
    lines.push(
      [
        r.fechaCrea || "",
        r.fechaEgreso || "",
        r.factura || "",
        r.estado || "",
        r.responsable || "",
        r.area || "",
        r.paciente || "",
        r.hcPendiente || "",
        envio,
      ].join("\t"),
    );
  }

  const text = lines.join("\n");
  await writeClipboard(text);
  showToast("✅ " + results.length + " filas copiadas al portapapeles");
}
