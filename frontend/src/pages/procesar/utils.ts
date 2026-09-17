/** Pure helpers for /procesar → control-novedades envío column. */

export function norm(s: string | null | undefined): string {
  return (s ?? "").trim().toUpperCase();
}

export function buildObservacion(
  descripcion: string,
  detalle: string,
): string {
  const desc = (descripcion ?? "").trim();
  const det = (detalle ?? "").trim();
  const full =
    det.length > 0 ? `[Procesar] ${desc} | ${det}` : `[Procesar] ${desc}`;
  return full.slice(0, 500);
}

export function buildEnvioSet(
  errores: Array<{ factura?: string }> | null | undefined,
): Set<string> {
  const set = new Set<string>();
  if (!Array.isArray(errores)) return set;
  for (const e of errores) {
    const raw = e?.factura ?? "";
    if (raw.trim().length === 0) continue;
    set.add(norm(raw));
  }
  return set;
}

export type EnvioEstado = "enviada" | "duplicada" | "nueva";

export function getEnvioEstado(
  factura: string,
  enviada: boolean,
  existentes: Set<string>,
): EnvioEstado {
  if (enviada) return "enviada";
  if (existentes?.has(norm(factura))) return "duplicada";
  return "nueva";
}

export function hasControlWrite(
  permisos: string[] | null | undefined,
): boolean {
  if (!Array.isArray(permisos)) return false;
  return permisos.includes("control_urgencias:write") || permisos.includes("*");
}

export function canShowEnvio(
  can_write: boolean,
  canControl: boolean,
): boolean {
  return Boolean(can_write && canControl);
}
