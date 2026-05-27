import { useState, useRef } from "react";
import {
  Upload,
  Info,
  FileSpreadsheet,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";

interface ErrorGroup {
  tipo: string;
  cantidad: number;
  facturas: Array<{
    factura: string;
    fec_factura: string;
    responsable_cierra: string;
    descripcion: string;
    procedimiento: string;
    detalle: string;
  }>;
}

interface IntramuralPageProps {
  can_write?: boolean;
}

export function IntramuralPage({ can_write: _can_write = false }: IntramuralPageProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errores, setErrores] = useState<ErrorGroup[]>([]);
  const [totalErrores, setTotalErrores] = useState(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setFileName(f?.name ?? null);
    setError(null);
  };

  const handleProcesar = async () => {
    if (!file) {
      setError("Seleccioná un archivo Excel primero");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file_upload", file);
      const res = await fetch("/intramural/", { method: "POST", body: fd });
      const data = await res.json();
      if (data.status === "success") {
        const items = data.data?.errores ?? [];
        setErrores(items);
        setTotalErrores(data.data?.total_errores ?? 0);
      } else {
        setError(data.errors?.[0] ?? "Error al procesar el archivo");
      }
    } catch (err) {
      setError("Error de conexión al procesar el archivo");
    } finally {
      setLoading(false);
    }
  };

  const allFacturas = errores.flatMap((g) => g.facturas);

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Intramural" }]} />
      <PageTitle
        eyebrow="Servicio Intramural"
        title="Procesamiento de facturas"
        description="Carga el reporte detallado en formato Excel para validar los registros y detectar inconsistencias."
      />

      {/* Upload card */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <h2 className="font-display font-semibold text-foreground mb-1">Subir archivo Excel</h2>
        <p className="text-xs text-muted-foreground mb-4">
          Formatos aceptados: .xlsx, .xls, .xlsm, .xlsb
        </p>

        <label
          htmlFor="file-upload"
          className="flex items-center gap-4 rounded-md border-2 border-dashed border-border bg-muted/40 p-5 cursor-pointer hover:border-primary/50 hover:bg-muted/60 transition-colors"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Upload className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            {fileName ? (
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-success" />
                <span className="text-sm font-medium text-foreground truncate">{fileName}</span>
              </div>
            ) : (
              <span className="text-sm text-muted-foreground">
                Arrastra el archivo aquí o haz clic para seleccionar
              </span>
            )}
          </div>
          <input
            ref={fileRef}
            id="file-upload"
            type="file"
            className="sr-only"
            accept=".xlsx,.xls,.xlsm,.xlsb"
            onChange={handleFileChange}
          />
        </label>

        {error && (
          <div className="mt-3 rounded-md border border-danger/30 bg-danger/5 p-3">
            <p className="text-xs font-medium text-danger">{error}</p>
          </div>
        )}

        <div className="mt-4 flex items-start gap-3 rounded-md border border-info/30 bg-info/5 p-3.5">
          <Info className="h-4 w-4 text-info mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-semibold text-info">Importante</p>
            <p className="text-xs text-foreground/80 mt-0.5">
              Los reportes cargados deben estar sin modificaciones y haberse descargado en formato detallado.
            </p>
          </div>
        </div>

        <div className="mt-5 flex justify-end">
          <Button
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
            disabled={loading || !file}
            onClick={handleProcesar}
          >
            {loading ? "Procesando…" : "Procesar archivo"}
            {!loading && <ArrowRight className="h-4 w-4" />}
          </Button>
        </div>
      </Card>

      {/* Errores */}
      {allFacturas.length > 0 && (
        <Card className="p-6 border-border bg-card shadow-none">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-danger/10 text-danger">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-display font-semibold text-foreground">Errores detectados</h2>
                <p className="text-xs text-muted-foreground">Inconsistencias identificadas en el reporte</p>
              </div>
            </div>
            <div className="text-right">
              <div className="font-display text-2xl font-semibold text-danger">{totalErrores}</div>
              <div className="text-xs text-muted-foreground">total</div>
            </div>
          </div>

          {errores.map((grupo) => (
            <div key={grupo.tipo} className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-display text-sm font-semibold text-foreground">{grupo.tipo}</h3>
                <StatusBadge tone="danger">{grupo.cantidad} registros</StatusBadge>
              </div>
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-sm">
                    <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="text-left font-medium px-4 py-3">Fec. Factura</th>
                        <th className="text-left font-medium px-4 py-3">Factura</th>
                        <th className="text-left font-medium px-4 py-3">Responsable cierre</th>
                        <th className="text-left font-medium px-4 py-3">Descripción</th>
                        <th className="text-left font-medium px-4 py-3">Procedimiento</th>
                        <th className="text-left font-medium px-4 py-3">Detalle</th>
                      </tr>
                    </thead>
                  <tbody className="divide-y divide-border">
                    {grupo.facturas.map((f, i) => (
                      <tr key={`${f.factura}-${i}`} className={cn("hover:bg-muted/30 transition-colors")}>
                        <td className="px-4 py-3 text-xs text-foreground/80">{f.fec_factura}</td>
                        <td className="px-4 py-3 font-mono text-xs font-medium text-foreground">{f.factura}</td>
                        <td className="px-4 py-3 text-xs text-foreground/80">{f.responsable_cierra}</td>
                        <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs">{f.descripcion}</td>
                        <td className="px-4 py-3 text-xs text-foreground/70 max-w-xs">{f.procedimiento}</td>
                        <td className="px-4 py-3">
                          <StatusBadge tone="warning">{f.detalle}</StatusBadge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
