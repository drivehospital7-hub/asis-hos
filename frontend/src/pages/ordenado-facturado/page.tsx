import { useState } from "react";
import {
  Upload,
  FileSpreadsheet,
  ArrowRight,
  AlertTriangle,
  ClipboardCopy,
  CheckCircle2,
  Info,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";

interface TotalizadoItem {
  codigo: string;
  procedimiento: string;
  total_reporte: number;
  total_ordenadas: number;
  total_no_facturado: number;
  es_notas?: boolean;
}

interface NoFacturadoItem {
  factura: string;
  paciente: string;
  identificacion: string;
  tipo_factura_servicio: string;
  entidad_administradora: string;
  profesional_solicito: string;
  cups: string;
  procedimiento_solicitado: string;
  fecha_solicitud: string;
  fecha_cierre?: string | null;
}

interface CruceResponse {
  status: string;
  data?: {
    totalizado: TotalizadoItem[];
    no_facturados: NoFacturadoItem[];
    fecha_warning?: string;
  };
  errors?: string[];
}

export function OrdenadoFacturadoPage() {
  const [reporteName, setReporteName] = useState<string | null>(null);
  const [ayudasName, setAyudasName] = useState<string | null>(null);
  const [notasName, setNotasName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CruceResponse["data"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [cerradas, setCerradas] = useState(false);

  const handleSubmit = async () => {
    const fileInput1 = document.getElementById("archivo_reporte") as HTMLInputElement;
    const fileInput2 = document.getElementById("archivo_ayudas") as HTMLInputElement;
    const fileInput3 = document.getElementById("archivo_notas") as HTMLInputElement;

    if (!fileInput1?.files?.length || !fileInput2?.files?.length) {
      setError("Debes seleccionar los 2 archivos obligatorios");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("archivo_reporte", fileInput1.files[0]);
    formData.append("archivo_ayudas", fileInput2.files[0]);
    if (fileInput3?.files?.length) {
      formData.append("archivo_notas", fileInput3.files[0]);
    }
    if (cerradas) {
      formData.append("cerradas", "true");
    }

    try {
      const res = await fetch("/ordenado-facturado/procesar", {
        method: "POST",
        body: formData,
      });
      const data: CruceResponse = await res.json();

      if (data.status === "success" && data.data) {
        setResult(data.data);
      } else {
        setError(data.errors?.join(", ") || "Error al procesar");
      }
    } catch (err) {
      setError("Error de conexión: " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  /** Escapa HTML para el formato text/html del clipboard */
  const escHtml = (s: string) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  const copyToClipboard = async () => {
    if (!result?.no_facturados?.length) return;

    const headers = [
      "N° Factura", "Paciente", "Nº Identificación",
      "Tipo Factura (Servicio)", "Entidad Administradora",
      "Profesional Solicitó", "CUPS", "Procedimiento Solicitado",
      "Fecha Solicitud",
    ];
    const rows = result.no_facturados.map((item) => [
      item.factura || "", item.paciente || "", item.identificacion || "",
      item.tipo_factura_servicio || "", item.entidad_administradora || "",
      item.profesional_solicito || "", item.cups || "",
      item.procedimiento_solicitado || "", item.fecha_solicitud || "",
    ]);

    // text/plain con tabs y CRLF (para editores de texto)
    const textPlain = [headers.join("\t"), ...rows.map((r) => r.join("\t"))].join("\r\n");

    // text/html — Excel reconoce <table> y separa en celdas automáticamente
    //    (usamos solo <tr>/<td> sin thead/tbody para máxima compatibilidad)
    const htmlParts: string[] = [
      "<table>",
      `<tr>${headers.map((h) => `<th>${escHtml(h)}</th>`).join("")}</tr>`,
      ...rows.map(
        (r) => `<tr>${r.map((v) => `<td>${escHtml(v)}</td>`).join("")}</tr>`,
      ),
      "</table>",
    ];
    const textHtml = htmlParts.join("");

    // 1. Intentar con navigator.clipboard (HTTPS)
    try {
      await navigator.clipboard.writeText(textPlain);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
      return;
    } catch {
      // HTTP → continuar con fallback
    }

    // 2. Fallback: copy event + execCommand con contentEditable
    //    Necesitamos una selección real para que execCommand dispare el evento copy
    //    Pone text/html primero (Excel le da prioridad sobre text/plain)
    const handler = (e: ClipboardEvent) => {
      e.preventDefault();
      e.clipboardData?.setData("text/html", textHtml);
      e.clipboardData?.setData("text/plain", textPlain);
    };
    document.addEventListener("copy", handler);

    try {
      // Creamos un div contentEditable con selección para forzar el evento copy
      const dummy = document.createElement("div");
      dummy.contentEditable = "true";
      dummy.textContent = ".";  // contenido mínimo para que la selección sea válida
      dummy.style.position = "fixed";
      dummy.style.opacity = "0";
      dummy.style.pointerEvents = "none";
      document.body.appendChild(dummy);
      dummy.focus();

      const sel = window.getSelection();
      if (sel) {
        sel.removeAllRanges();
        const range = document.createRange();
        range.selectNodeContents(dummy);
        sel.addRange(range);
      }

      document.execCommand("copy");
      document.body.removeChild(dummy);
    } catch {
      // 3. Último recurso: textarea (solo text/plain)
      const textarea = document.createElement("textarea");
      textarea.value = textPlain;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      textarea.style.pointerEvents = "none";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    document.removeEventListener("copy", handler);

    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Equipos Básicos" }, { label: "Ordenado y Facturado" }]} />
      <PageTitle
        eyebrow="Equipos Básicos"
        title="Ordenado y Facturado"
        description="Revisa que cada (Factura, CUPS) de Ayudas Diagnósticas esté facturado en el Reporte. Los que falten se listan como no facturados."
      />

      {/* Upload card */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        {/* Reporte */}
        <div className="mb-5">
          <label className="block text-xs font-semibold text-foreground mb-1.5 uppercase tracking-wider">
            Reporte <StatusBadge tone="info">Excel Estándar</StatusBadge>
          </label>
          <label className="flex items-center gap-4 rounded-md border-2 border-dashed border-border bg-muted/40 p-4 cursor-pointer hover:border-primary/50 hover:bg-muted/60 transition-colors">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Upload className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              {reporteName ? (
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="h-4 w-4 text-success" />
                  <span className="text-sm font-medium text-foreground truncate">{reporteName}</span>
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">Seleccionar archivo de reporte</span>
              )}
            </div>
            <input
              id="archivo_reporte"
              type="file"
              className="sr-only"
              accept=".xlsx,.xls,.xlsm,.xlsb"
              onChange={(e) => setReporteName(e.target.files?.[0]?.name ?? null)}
            />
          </label>
        </div>

        {/* Ayudas */}
        <div className="mb-5">
          <label className="block text-xs font-semibold text-foreground mb-1.5 uppercase tracking-wider">
            Reporte Ayudas Diagnósticas
          </label>
          <label className="flex items-center gap-4 rounded-md border-2 border-dashed border-border bg-muted/40 p-4 cursor-pointer hover:border-primary/50 hover:bg-muted/60 transition-colors">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Upload className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              {ayudasName ? (
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="h-4 w-4 text-success" />
                  <span className="text-sm font-medium text-foreground truncate">{ayudasName}</span>
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">Seleccionar archivo de ayudas</span>
              )}
            </div>
            <input
              id="archivo_ayudas"
              type="file"
              className="sr-only"
              accept=".xlsx,.xls,.xlsm,.xlsb"
              onChange={(e) => setAyudasName(e.target.files?.[0]?.name ?? null)}
            />
          </label>
        </div>

        {/* Notas (opcional) */}
        <details className="group mb-5">
          <summary className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 border border-border rounded-md text-xs font-medium text-muted-foreground bg-background hover:bg-muted/30 transition-colors list-none">
            + Opcional
          </summary>
          <div className="mt-3 p-3 border border-dashed border-border rounded-md">
            <label className="block text-xs font-semibold text-foreground mb-1.5 uppercase tracking-wider">
              Notas Enfermería
            </label>
            <label className="flex items-center gap-3 rounded-md border-2 border-dashed border-border bg-muted/40 p-3 cursor-pointer hover:border-primary/50 hover:bg-muted/60 transition-colors">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Upload className="h-3.5 w-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                {notasName ? (
                  <span className="text-sm font-medium text-foreground truncate">{notasName}</span>
                ) : (
                  <span className="text-xs text-muted-foreground">Seleccionar archivo de notas (opcional)</span>
                )}
              </div>
              <input
                id="archivo_notas"
                type="file"
                className="sr-only"
                accept=".xlsx,.xls,.xlsm,.xlsb"
                onChange={(e) => setNotasName(e.target.files?.[0]?.name ?? null)}
              />
            </label>
            <p className="text-xs text-muted-foreground mt-1.5">
              Busca <strong>OCF066</strong> para filtrar traslados.
            </p>

            <label className="flex items-center gap-2 cursor-pointer mt-4 pt-3 border-t border-border">
              <input
                id="cerradas"
                type="checkbox"
                className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                checked={cerradas}
                onChange={(e) => setCerradas(e.target.checked)}
              />
              <span className="text-xs font-medium text-foreground">Cerradas</span>
            </label>
          </div>
        </details>

        {error && (
          <div className="mb-4 flex items-start gap-2 rounded-md border border-danger/30 bg-danger/5 p-3">
            <AlertTriangle className="h-4 w-4 text-danger mt-0.5 shrink-0" />
            <p className="text-xs text-danger">{error}</p>
          </div>
        )}

        <div className="flex justify-end">
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? "Procesando..." : (
              <>
                Procesar
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Results */}
      {result && (
        <Card className="p-6 border-border bg-card shadow-none">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-success" />
              <div>
                <h2 className="font-display font-semibold text-foreground">Resultado del Cruce</h2>
                <p className="text-xs text-muted-foreground">
                  {result.no_facturados?.length || 0} registros no facturados
                </p>
              </div>
            </div>
          </div>

          {/* Totalizado */}
          {result.totalizado && result.totalizado.length > 0 && (
            <div className="mb-6">
              <h3 className="font-display text-sm font-semibold text-foreground mb-3">Totalizado por Código</h3>
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="text-left font-medium px-4 py-3">Código</th>
                      <th className="text-left font-medium px-4 py-3">Procedimiento</th>
                      <th className="text-right font-medium px-4 py-3">Total Reporte</th>
                      <th className="text-right font-medium px-4 py-3">Total Ordenadas</th>
                      <th className="text-right font-medium px-4 py-3">Total No Facturadas</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {result.totalizado.map((item) => (
                      <tr key={item.codigo} className={item.es_notas ? "bg-muted/20" : "hover:bg-muted/30 transition-colors"}>
                        <td className="px-4 py-3 font-mono text-xs font-medium text-foreground">{item.codigo}</td>
                        <td className="px-4 py-3 text-xs text-foreground/80">{item.procedimiento}</td>
                        <td className="px-4 py-3 text-xs text-right text-foreground/80">{item.total_reporte}</td>
                        <td className="px-4 py-3 text-xs text-right text-foreground/80">{item.total_ordenadas}</td>
                        <td className="px-4 py-3 text-xs text-right font-semibold text-danger">{item.total_no_facturado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Fecha warning */}
          {result.fecha_warning && (
            <div className="mb-4 flex items-start gap-2 rounded-md border border-info/30 bg-info/5 p-3">
              <Info className="h-4 w-4 text-info mt-0.5 shrink-0" />
              <p className="text-xs text-foreground/80 italic">{result.fecha_warning}</p>
            </div>
          )}

          {/* No facturados */}
          {result.no_facturados && result.no_facturados.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-display text-sm font-semibold text-foreground">Detalle de No Facturados</h3>
                <div className="flex items-center gap-2">
                  {copied && (
                    <span className="text-xs text-success font-semibold">✓ Copiado al portapapeles</span>
                  )}
                  <Button variant="secondary" size="sm" onClick={copyToClipboard}>
                    <ClipboardCopy className="h-3.5 w-3.5" />
                    Copiar individuales
                  </Button>
                </div>
              </div>
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="text-left font-medium px-4 py-3">Factura</th>
                      <th className="text-left font-medium px-4 py-3">Paciente</th>
                      <th className="text-left font-medium px-4 py-3">Identificación</th>
                      <th className="text-left font-medium px-4 py-3">CUPS</th>
                      <th className="text-left font-medium px-4 py-3">Procedimiento</th>
                      <th className="text-left font-medium px-4 py-3">Fecha Solicitud</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {result.no_facturados.map((item, i) => (
                      <tr key={i} className="hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs font-medium text-foreground">{item.factura}</td>
                        <td className="px-4 py-3 text-xs text-foreground/80">{item.paciente}</td>
                        <td className="px-4 py-3 text-xs text-foreground/70">{item.identificacion}</td>
                        <td className="px-4 py-3 font-mono text-xs text-foreground/70">{item.cups}</td>
                        <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs truncate">{item.procedimiento_solicitado}</td>
                        <td className="px-4 py-3 text-xs text-foreground/70">{item.fecha_solicitud}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
