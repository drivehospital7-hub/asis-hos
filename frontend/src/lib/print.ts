/**
 * Print document builders + print window for the Exámenes module (EX-13).
 *
 * Preserves the source print documents: E.S.E. HOSPITAL ORITO header, NIT
 * 846000474-7, green header (`pdoc-hdr`), per-item tags, signature and
 * footer. `printContenido` opens a print window with auto-print+close and
 * falls back to printing on the current page when the popup is blocked.
 *
 * Pure HTML builders live here so they are unit-testable; only
 * `printContenido` touches the DOM.
 */

import type { Prefactura, PrefacturaItem } from "./examenes";
import { normalizeItem, tcDisplay } from "./examenes";

/** Escapa texto de usuario para interpolar en HTML sin ejecutar (R1-001). */
export function escapeHtml(value: string | null | undefined): string {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]!,
  );
}

/** Print stylesheet mirroring the source print window. */
export const PRINT_CSS = `*{box-sizing:border-box;margin:0;padding:0;}
  .pdoc-hdr{background:#1a4731;color:white;padding:13px 17px;border-radius:7px 7px 0 0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
  .pdoc-hdr h2{margin:0;font-size:15px;font-weight:700;}
  .pdoc-hdr p{margin:3px 0 0;font-size:10px;opacity:.8;}
  .pdoc-body{border:1px solid #ccc;border-top:none;border-radius:0 0 7px 7px;padding:16px;}
  .prow{display:flex;gap:8px;margin-bottom:8px;}
  .plbl{font-size:11px;color:#666;width:110px;flex-shrink:0;font-weight:700;}
  .pval{font-size:13px;font-weight:700;}
  .psep{height:1px;background:#e0e0e0;margin:10px 0;}
  .ptbl{width:100%;border-collapse:collapse;margin-top:10px;}
  .ptbl th{background:#1a4731;color:white;padding:7px 6px;font-size:10px;text-align:left;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
  .ptbl td{padding:6px;border-bottom:1px solid #eee;font-size:11px;vertical-align:middle;}
  .ptbl tr:nth-child(even) td{background:#f7faf8;}
  .ptag{display:inline-block;font-size:9px;padding:2px 7px;border-radius:10px;border:1px solid;font-weight:700;margin-right:2px;}
  .tneps{background:#e6f1fb;color:#0c447c;border-color:#b5d4f4;}
  .tmall{background:#eaf3de;color:#27500a;border-color:#c0dd97;}
  .temss{background:#faeeda;color:#633806;border-color:#fac775;}
  .tauth{background:#fdf0ee;color:#a32d2d;border-color:#f5c6c0;}
  .pfirma{margin-top:24px;border-top:1px solid #aaa;width:260px;font-size:10px;padding-top:5px;color:#555;}
  .pfooter{margin-top:12px;font-size:9px;color:#aaa;display:flex;justify-content:space-between;border-top:1px solid #eee;padding-top:7px;}`;

/** Full print window sheet: adds the page-level body rule. */
export const PRINT_STYLES = `<style>
  body{font-family:Arial,sans-serif;font-size:12px;color:#111;padding:24px;}
  ${PRINT_CSS}
</style>`;

/** In-page preview sheet: pdoc classes only (no global body override). */
export const PREVIEW_STYLES = `<style>
  ${PRINT_CSS}
</style>`;

/** Print tags (source `renderTagsPrint`): X→NEPS, AUTH→N⚠AUTH, none→—. */
export function renderTagsPrint(item: PrefacturaItem): string {
  let t = "";
  if (item.neps === "X") t += `<span class="ptag tneps">NEPS</span>`;
  else if (item.neps === "AUTH") t += `<span class="ptag tauth">NEPS⚠AUTH</span>`;
  if (item.mall === "X") t += `<span class="ptag tmall">MALLAM</span>`;
  else if (item.mall === "AUTH") t += `<span class="ptag tauth">MALL⚠AUTH</span>`;
  if (item.emss === "X") t += `<span class="ptag temss">EMSS</span>`;
  else if (item.emss === "AUTH") t += `<span class="ptag tauth">EMSS⚠AUTH</span>`;
  return t || "—";
}

/** Single prefactura print doc (source `verListadoRegistro`). */
export function buildPrefacturaDoc(pf: Prefactura, fechaStr: string): string {
  const rows = pf.items
    .map(
      (item, i) => `
      <tr>
        <td style="color:#888;text-align:center;">${i + 1}</td>
        <td style="font-weight:700;color:#1a4731;">${escapeHtml(item.cod)}</td>
        <td>${escapeHtml(item.nom)}</td>
        <td style="text-align:center;">${normalizeItem(item).cantidad}</td>
        <td>${renderTagsPrint(item)}</td>
      </tr>`,
    )
    .join("");
  return `
    <div class="pdoc-hdr">
      <h2>E.S.E. HOSPITAL ORITO</h2>
      <p>NIT 846000474-7 &nbsp;·&nbsp; Prefactura de Servicios de Laboratorio Clínico</p>
    </div>
    <div class="pdoc-body">
      <div class="prow"><span class="plbl">Fecha:</span><span class="pval">${escapeHtml(fechaStr)}</span></div>
      <div class="psep"></div>
      <div class="prow"><span class="plbl">Paciente:</span><span class="pval">${escapeHtml(pf.paciente)}</span></div>
      <div class="prow"><span class="plbl">Cédula / Doc.:</span><span class="pval">${escapeHtml(pf.cedula)}</span></div>
      <div class="psep"></div>
      <table class="ptbl">
        <thead><tr><th style="width:30px;">#</th><th style="width:80px;">Código</th><th>Examen</th><th style="width:40px;">Cant</th><th style="width:160px;">Aplica en</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="pfirma">Facturador(a): ${escapeHtml(pf.facturador)}</div>
      <div class="pfooter">
        <span>Hora: ${escapeHtml(pf.hora)}</span>
        <span>Laboratorio Clínico — E.S.E. Hospital Orito</span>
      </div>
    </div>`;
}

/**
 * Full listado print doc: ALL prefacturas as sections (never month-filtered),
 * each with `page-break-inside:avoid` (source `verListadoPrint`).
 */
export function buildListadoDoc(listado: Prefactura[], fechaStr: string): string {
  const sections = listado
    .map((pf) => {
      const itemsHtml = pf.items
        .map(
          (item, j) => `
          <tr>
            <td style="color:#aaa;text-align:center;">${j + 1}</td>
            <td style="font-weight:700;color:#1a4731;">${escapeHtml(item.cod)}</td>
            <td style="font-size:10px;">${escapeHtml(item.nom)}</td>
            <td style="text-align:center;">${normalizeItem(item).cantidad}</td>
            <td style="text-align:center;">${tcDisplay(item.neps)}</td>
            <td style="text-align:center;">${tcDisplay(item.mall)}</td>
            <td style="text-align:center;">${tcDisplay(item.emss)}</td>
          </tr>`,
        )
        .join("");
      return `
      <div style="margin-bottom:18px;border:1px solid #ddd;border-radius:7px;padding:12px;page-break-inside:avoid;">
        <div style="font-size:12px;font-weight:700;color:#1a4731;margin-bottom:4px;">${escapeHtml(pf.paciente)}</div>
        <div style="font-size:10px;color:#666;margin-bottom:8px;">Cédula: ${escapeHtml(pf.cedula)} &nbsp;|&nbsp; Facturador: ${escapeHtml(pf.facturador)} &nbsp;|&nbsp; Hora: ${escapeHtml(pf.hora)}</div>
        <table class="ptbl" style="min-width:460px;">
          <thead><tr><th style="width:30px;">#</th><th style="width:80px;">Código</th><th>Examen</th><th style="width:40px;">Cant</th><th style="width:50px;">NEPS</th><th style="width:55px;">MALL</th><th style="width:55px;">EMSS</th></tr></thead>
          <tbody>${itemsHtml}</tbody>
        </table>
      </div>`;
    })
    .join("");
  return `
    <div class="pdoc-hdr">
      <h2>E.S.E. Hospital Orito — Listado Diario de Prefacturas</h2>
      <p>${escapeHtml(fechaStr)} &nbsp;·&nbsp; Total: ${listado.length} prefacturas &nbsp;·&nbsp; NIT: 846000474-7</p>
    </div>
    <div class="pdoc-body">
      ${sections}
      <div class="pfooter" style="margin-top:12px;">
        <span>Impreso: ${escapeHtml(new Date().toLocaleString("es-CO"))}</span>
        <span>Laboratorio Clínico — E.S.E. Hospital Orito</span>
      </div>
    </div>`;
}

/**
 * Print a doc fragment: popup window with auto-print + close; when the popup
 * is blocked (window.open returns null), fall back to printing on the
 * current page (source `imprimirHTML` / `imprimirContenido`).
 */
export function printContenido(contenido: string): void {
  const pw = window.open("", "_blank", "width=850,height=700");
  if (pw && !pw.closed) {
    pw.document.write(
      '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Imprimir</title>' +
        PRINT_STYLES +
        "</head><body>" +
        contenido +
        '<script>window.onload=function(){window.print();window.close();}<\/script></body></html>',
    );
    pw.document.close();
  } else {
    const tmp = document.createElement("div");
    tmp.innerHTML = contenido;
    tmp.style.cssText =
      "position:fixed;top:0;left:0;width:100%;z-index:99999;background:#fff;padding:20px;";
    document.body.appendChild(tmp);
    setTimeout(() => {
      window.print();
      document.body.removeChild(tmp);
    }, 200);
  }
}