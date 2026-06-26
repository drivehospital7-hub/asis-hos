import { useState } from "react";
import {
  Play,
  FileDown,
  AlertCircle,
  CheckCircle2,
  XCircle,
  FolderOpen,
  FileText,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";

interface InvoiceData {
  filename: string;
  facturador: string;
  full_path: string;
  status: string;
  invoice_type: string;
  invoice_code: string;
}

interface ScanResponse {
  status: string;
  data: {
    facturas: InvoiceData[];
    indicadores: Record<string, number>;
    duplicados: Array<{ filename: string; facturadores: string[] }>;
    vacias: Array<{ facturador: string; folder: string }>;
    errores_scan: Array<{ root: string; error: string }>;
    excel_download: string | null;
  };
  errors: string[];
}

export function MonitoreoCarpetasPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResponse["data"] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleScan = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/monitoreo-carpetas/scan", { method: "POST" });
      const data: ScanResponse = await res.json();

      if (data.status === "success") {
        setResult(data.data);
      } else {
        setError(data.errors?.join(", ") || "Error al ejecutar escaneo");
      }
    } catch (err) {
      setError("Error de conexión: " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case "Verificada":
        return <StatusBadge tone="success">Verificada</StatusBadge>;
      case "Por corregir":
        return <StatusBadge tone="danger">Por corregir</StatusBadge>;
      default:
        return <StatusBadge tone="warning">En revisión</StatusBadge>;
    }
  };

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Monitoreo de Carpetas" }]} />
      <PageTitle
        eyebrow="EPS MALLAMAS"
        title="Monitoreo de Carpetas"
        description="Escanea las carpetas de red de facturadores y genera un reporte con indicadores operacionales."
      />

      {/* Trigger card */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-display font-semibold text-foreground text-sm">
              Escanear Carpetas de Red
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Ejecuta un escaneo completo de todas las carpetas configuradas.
            </p>
          </div>
          <Button onClick={handleScan} disabled={loading}>
            {loading ? (
              "Escaneando..."
            ) : (
              <>
                <Play className="h-4 w-4" />
                Iniciar Escaneo
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Error */}
      {error && (
        <Card className="p-6 border-danger/30 bg-danger/5 shadow-none mb-6">
          <div className="flex items-center gap-3">
            <XCircle className="h-5 w-5 text-danger" />
            <p className="text-sm font-medium text-danger">{error}</p>
          </div>
        </Card>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Facturas
              </p>
              <p className="text-2xl font-display font-bold text-foreground mt-1">
                {result.indicadores?.total_facturas ?? 0}
              </p>
            </Card>
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Facturadores
              </p>
              <p className="text-2xl font-display font-bold text-foreground mt-1">
                {result.indicadores?.total_facturadores ?? 0}
              </p>
            </Card>
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Duplicados
              </p>
              <p className="text-2xl font-display font-bold text-warning-foreground mt-1">
                {result.indicadores?.total_duplicados ?? 0}
              </p>
            </Card>
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Vacías / Errores
              </p>
              <p className="text-2xl font-display font-bold text-danger mt-1">
                {(result.indicadores?.total_vacias ?? 0) + (result.indicadores?.total_errores ?? 0)}
              </p>
            </Card>
          </div>

          {/* Download button */}
          {result.excel_download && (
            <div className="mb-6">
              <a
                href={`/monitoreo-carpetas/download/${result.excel_download}`}
                download
              >
                <Button variant="outline">
                  <FileDown className="h-4 w-4" />
                  Exportar Excel
                </Button>
              </a>
            </div>
          )}

          {/* Duplicates section */}
          {result.duplicados && result.duplicados.length > 0 && (
            <Card className="p-6 border-border bg-card shadow-none mb-6">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-border">
                <AlertCircle className="h-5 w-5 text-warning-foreground" />
                <h3 className="font-display font-semibold text-foreground text-sm">
                  Facturas Duplicadas ({result.duplicados.length})
                </h3>
              </div>
              <div className="space-y-2">
                {result.duplicados.map((dup, idx) => (
                  <div key={idx} className="text-xs text-foreground/80 flex items-start gap-2">
                    <FileText className="h-3 w-3 text-muted-foreground mt-0.5 shrink-0" />
                    <div>
                      <span className="font-medium">{dup.filename}</span>
                      {" en "}
                      {dup.facturadores.join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Empty folders section */}
          {result.vacias && result.vacias.length > 0 && (
            <Card className="p-6 border-border bg-card shadow-none mb-6">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-border">
                <FolderOpen className="h-5 w-5 text-muted-foreground" />
                <h3 className="font-display font-semibold text-foreground text-sm">
                  Carpetas Vacías ({result.vacias.length})
                </h3>
              </div>
              <div className="space-y-1">
                {result.vacias.map((v, idx) => (
                  <p key={idx} className="text-xs text-foreground/80">
                    {v.facturador} — {v.folder}
                  </p>
                ))}
              </div>
            </Card>
          )}

          {/* Scan errors section */}
          {result.errores_scan && result.errores_scan.length > 0 && (
            <Card className="p-6 border-danger/30 bg-danger/5 shadow-none mb-6">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-border">
                <XCircle className="h-5 w-5 text-danger" />
                <h3 className="font-display font-semibold text-danger text-sm">
                  Errores de Escaneo ({result.errores_scan.length})
                </h3>
              </div>
              <div className="space-y-1">
                {result.errores_scan.map((e, idx) => (
                  <p key={idx} className="text-xs text-danger/80">
                    {e.root}: {e.error}
                  </p>
                ))}
              </div>
            </Card>
          )}

          {/* Results table */}
          {result.facturas && result.facturas.length > 0 && (
            <Card className="p-6 border-border bg-card shadow-none">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-border">
                <CheckCircle2 className="h-5 w-5 text-success" />
                <h3 className="font-display font-semibold text-foreground text-sm">
                  Facturas Encontradas ({result.facturas.length})
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Código</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Tipo</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Estado</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Facturador</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Archivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.facturas.map((inv, idx) => (
                      <tr key={idx} className="border-b border-border/50 last:border-0">
                        <td className="py-1.5 pr-3 text-foreground/90 font-medium">
                          {inv.invoice_code}
                        </td>
                        <td className="py-1.5 pr-3">
                          <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                            {inv.invoice_type}
                          </span>
                        </td>
                        <td className="py-1.5 pr-3">{statusBadge(inv.status)}</td>
                        <td className="py-1.5 pr-3 text-foreground/80">{inv.facturador}</td>
                        <td className="py-1.5 pr-3 text-foreground/60 max-w-[200px] truncate" title={inv.filename}>
                          {inv.filename}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
