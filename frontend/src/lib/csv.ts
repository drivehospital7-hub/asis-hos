/**
 * CSV export for the Exámenes module (EX-14).
 *
 * Exact header, UTF-8 BOM for Excel, X→SI / AUTH→AUTH / empty mapping, one
 * row per item, and a month-scoped filename (`Todos_los_meses` for "all").
 * Only the records passed in (the filtered view) are exported.
 */

import { normalizeItem, type Prefactura } from "./examenes";

/** Exact EX-14 header (Cedula without accent, Fecha/Hora, Cant after Examen). */
export const CSV_HEADERS = [
  "N°",
  "Paciente",
  "Cedula",
  "Codigo",
  "Examen",
  "Cant",
  "NEPS",
  "MALLAM",
  "EMSS",
  "Facturador",
  "Fecha/Hora",
] as const;

/** X→SI, AUTH→AUTH, anything else → empty (CSV flavor of the mapping). */
export function tcCsv(v: string | null | undefined): string {
  if (v === "X") return "SI";
  if (v === "AUTH") return "AUTH";
  return "";
}

/**
 * Filename-safe month label: "Agosto de 2026" → "Agosto_de_2026";
 * null (all months) → "Todos_los_meses".
 */
export function csvLabelFor(monthLabel: string | null): string {
  if (monthLabel === null) return "Todos_los_meses";
  return monthLabel.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "");
}

export interface CsvResult {
  csv: string;
  filename: string;
}

/**
 * Build the CSV (BOM + header + one row per item) for the given listado and
 * a filename using the provided month label (null → all months).
 */
export function buildCsv(listado: Prefactura[], monthLabel: string | null): CsvResult {
  let body = CSV_HEADERS.join(",") + "\n";
  let n = 0;
  for (const pf of listado) {
    for (const item of pf.items) {
      n++;
      body += `${n},"${pf.paciente}","${pf.cedula}","${item.cod}","${item.nom}","${normalizeItem(item).cantidad}","${tcCsv(item.neps)}","${tcCsv(item.mall)}","${tcCsv(item.emss)}","${pf.facturador}","${pf.hora}"\n`;
    }
  }
  const label = csvLabelFor(monthLabel);
  return {
    csv: "\uFEFF" + body,
    filename: `Listado_Lab_HospitalOrito_${label}.csv`,
  };
}

/** Trigger the browser download (DOM side; kept thin for testability). */
export function downloadCsv(csv: string, filename: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}