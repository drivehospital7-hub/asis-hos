/** Pure helpers for /procesar → control-novedades envío column. */

export function norm(s: string | null | undefined): string {
  return (s ?? "").trim().toUpperCase();
}

function isOmittableLine(value: string): boolean {
  const t = value.trim();
  return t === "" || t === "-" || t === "—";
}

export function buildObservacion(
  descripcion: string,
  detalleA?: string,
  detalleB?: string,
): string {
  const lines = [descripcion ?? "", detalleA ?? "", detalleB ?? ""]
    .map((s) => (s ?? "").trim())
    .filter((t) => !isOmittableLine(t));
  return lines.join("\n").slice(0, 500);
}

/**
 * Notificación (incl. legacy "Factura Abierta") = factura abierta de urgencias,
 * no un error reportado. /procesar envía como "Error", así que el aviso de
 * duplicado solo matchea categoría "Error": una Notificación existente no
 * significa que la factura ya fue reportada como error.
 */
export function isNotificacionCategoria(
  tipo_error: string | null | undefined,
): boolean {
  const t = (tipo_error ??
    "").trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  return t === "notificacion" || t === "factura abierta";
}

export function buildEnvioSet(
  errores: Array<{ factura?: string; tipo_error?: string }> | null | undefined,
): Set<string> {
  const set = new Set<string>();
  if (!Array.isArray(errores)) return set;
  for (const e of errores) {
    if (isNotificacionCategoria(e?.tipo_error)) continue;
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
  if (existentes?.has(norm(factura))) return "duplicada";
  if (enviada) return "enviada";
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
