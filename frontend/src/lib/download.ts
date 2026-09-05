/**
 * Download helpers for the Exámenes module (D7/D9).
 *
 * `downloadBlob` triggers the browser download from a blob (SPA-safe — the
 * control-novedades `window.location` trick is Jinja2-only). `filenameFromDisposition`
 * extracts the ASCII `filename=` from a Content-Disposition header so the
 * client uses the server's single source of truth (D9).
 */

/** Trigger a browser download from a blob (D7). */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Filename from a Content-Disposition header (ASCII `filename=`; D9).
 * Handles plain and quoted forms; returns null when absent so the caller can
 * fall back to a default name.
 */
export function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const match = header.match(/filename="?([^";]+)"?/i);
  return match ? match[1] : null;
}