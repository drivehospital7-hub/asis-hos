import { useState } from "react";
import {
  FolderOpen,
  Play,
  FileText,
  CheckCircle2,
  AlertCircle,
  XCircle,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";

interface CarpetaData {
  archivos: string[];
  datos?: {
    pdfs?: Array<{
      datos?: {
        documento?: string;
        nombre?: string;
        vigencia?: string;
        regimen?: string;
        ips?: string;
        servicios?: string[];
      };
      validacion?: {
        es_valido?: boolean;
        errores?: string[];
        warnings?: string[];
      };
    }>;
  };
}

interface ProcesarResponse {
  status: string;
  data: {
    mensaje: string;
    estructura: Record<string, CarpetaData>;
    total_carpetas: number;
    total_archivos: number;
    total_validos?: number;
  };
}

export function DerechosPage() {
  const [ruta, setRuta] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProcesarResponse["data"] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruta.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/derechos/procesar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ruta: ruta.trim() }),
      });
      const data = await res.json();

      if (data.status === "success") {
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

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Derechos" }]} />
      <PageTitle
        eyebrow="EPS MALLAMAS"
        title="Módulo Derechos"
        description="Ingresa la ruta de la carpeta que contiene los archivos PDF a procesar."
      />

      {/* Form card */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <form onSubmit={handleSubmit}>
          <label htmlFor="rutaInput" className="block text-xs font-semibold text-foreground mb-1.5 uppercase tracking-wider">
            Ruta de la carpeta
          </label>
          <div className="flex gap-2">
            <input
              id="rutaInput"
              type="text"
              value={ruta}
              onChange={(e) => setRuta(e.target.value)}
              placeholder="C:\Users\Documents\Carpetas\..."
              className="flex-1 rounded-md border border-border bg-background px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>
          <p className="text-xs text-muted-foreground mt-1.5 mb-4">
            Escribe la ruta completa de la carpeta con archivos PDE.
          </p>

          <div className="flex justify-end">
            <Button type="submit" disabled={loading || !ruta.trim()}>
              {loading ? (
                "Buscando..."
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Procesar
                </>
              )}
            </Button>
          </div>
        </form>
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
        <Card className="p-6 border-border bg-card shadow-none">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-success" />
              <div>
                <h2 className="font-display font-semibold text-foreground">{result.mensaje}</h2>
                <p className="text-xs text-muted-foreground">
                  {result.total_carpetas} carpetas · {result.total_archivos} archivos PDF
                  {result.total_validos !== undefined && ` · ${result.total_validos} válidos`}
                </p>
              </div>
            </div>
          </div>

          {Object.entries(result.estructura).map(([carpeta, info]) => {
            const pdfs = info.datos?.pdfs ?? [];
            const validacion = pdfs[0]?.validacion ?? {};
            const datos = pdfs[0]?.datos ?? {};
            const isValid = validacion.es_valido === true;
            const isError = validacion.es_valido === false;

            return (
              <div key={carpeta} className="mb-4 last:mb-0 rounded-md border border-border p-4">
                <div className="flex items-center gap-2 mb-2">
                  <FolderOpen className="h-4 w-4 text-muted-foreground" />
                  <span className="font-display font-semibold text-foreground text-sm">{carpeta}</span>
                  {isValid && <StatusBadge tone="success">Válido</StatusBadge>}
                  {isError && <StatusBadge tone="danger">Error</StatusBadge>}
                </div>

                {info.archivos.length > 0 && (
                  <ul className="ml-6 space-y-0.5 mb-2">
                    {info.archivos.map((a) => (
                      <li key={a} className="text-xs text-muted-foreground flex items-center gap-1.5">
                        <FileText className="h-3 w-3" />
                        {a}
                      </li>
                    ))}
                  </ul>
                )}

                {datos.documento && (
                  <div className="ml-6 text-xs text-foreground/80 space-y-0.5">
                    {datos.documento && <p><strong>Documento:</strong> {datos.documento}</p>}
                    {datos.nombre && <p><strong>Nombre:</strong> {datos.nombre}</p>}
                    {datos.regimen && <p><strong>Régimen:</strong> {datos.regimen}</p>}
                    {datos.vigencia && <p><strong>Vigencia:</strong> {datos.vigencia}</p>}
                    {datos.ips && <p><strong>IPS:</strong> {datos.ips}</p>}
                    {datos.servicios && datos.servicios.length > 0 && (
                      <p><strong>Servicios:</strong> {datos.servicios.join(", ")}</p>
                    )}
                  </div>
                )}

                {validacion.errores && validacion.errores.length > 0 && (
                  <div className="ml-6 mt-1 flex items-center gap-1.5 text-xs text-danger">
                    <AlertCircle className="h-3 w-3" />
                    {validacion.errores.join(", ")}
                  </div>
                )}
                {validacion.warnings && validacion.warnings.length > 0 && (
                  <div className="ml-6 mt-1 text-xs text-warning-foreground">
                    ⚠️ {validacion.warnings.join(", ")}
                  </div>
                )}
              </div>
            );
          })}
        </Card>
      )}
    </div>
  );
}
