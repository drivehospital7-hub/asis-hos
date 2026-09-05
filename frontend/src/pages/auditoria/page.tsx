import { useState } from "react";
import {
  FolderOpen,
  FileText,
  Play,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronRight,
  ChevronDown,
  Download,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface ArchivoItem {
  tipo: string;
  archivo: string;
  data?: Record<string, unknown>;
  texto?: string;
  error?: string;
}

interface ValidacionResult {
  fev_normalizado?: Record<string, unknown>;
  pde_normalizado?: Record<string, unknown>;
  diferencias?: Record<string, unknown>;
}

interface ValidacionSoportes {
  validacion_soportes?: Array<Record<string, unknown>>;
  codigos_sin_regla?: string[];
}

interface CarpetaExpediente {
  archivos: ArchivoItem[];
  validacion?: ValidacionResult | null;
  validacion_soportes?: ValidacionSoportes | null;
  alerta_archivos?: { mensaje: string };
  duplicado_global?: { mensaje: string; ubicaciones: string[] };
  error?: string;
}

type EstructuraTree = Record<string, CarpetaExpediente | Record<string, unknown>>;

interface ProcesarResponse {
  status: string;
  data: {
    ruta: string;
    estructura: EstructuraTree;
  };
  errors: string[];
}

/* ------------------------------------------------------------------ */
/*  Helper: extract leaf folders with "archivos" from nested tree     */
/* ------------------------------------------------------------------ */

function collectExpedientes(tree: EstructuraTree, prefix = ""): Array<{ nombre: string; data: CarpetaExpediente }> {
  const result: Array<{ nombre: string; data: CarpetaExpediente }> = [];
  for (const [key, value] of Object.entries(tree)) {
    const fullName = prefix ? `${prefix} / ${key}` : key;
    if (value && typeof value === "object" && "archivos" in value) {
      result.push({ nombre: fullName, data: value as CarpetaExpediente });
    } else if (value && typeof value === "object") {
      result.push(...collectExpedientes(value as EstructuraTree, fullName));
    }
  }
  return result;
}

/* ------------------------------------------------------------------ */
/*  Status icon helpers                                               */
/* ------------------------------------------------------------------ */

function getFileTypeIcon(tipo: string) {
  switch (tipo) {
    case "FEV":
      return <FileText className="h-3.5 w-3.5 text-blue-500" />;
    case "PDE":
      return <FileText className="h-3.5 w-3.5 text-emerald-500" />;
    case "SOPORTE":
      return <FileText className="h-3.5 w-3.5 text-amber-500" />;
    default:
      return <FileText className="h-3.5 w-3.5 text-muted-foreground" />;
  }
}

function hasError(data: CarpetaExpediente): boolean {
  return data.archivos.some((a) => a.error) || data.alerta_archivos?.mensaje?.toLowerCase().includes("no existe") === true;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export function AuditoriaPage() {
  const [ruta, setRuta] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProcesarResponse["data"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggleExpand = (key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleDownload = async () => {
    if (!ruta.trim()) return;
    try {
      const res = await fetch(`/derechos/auditoria/procesar?descargar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ruta: ruta.trim() }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const nombreCarpeta = ruta.trim().replace(/[/\\]+$/, "").split(/[/\\]/).pop() || "auditoria";
      a.download = `auditoria_${nombreCarpeta}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError("Error al descargar: " + (err as Error).message);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruta.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/derechos/auditoria/procesar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ruta: ruta.trim() }),
      });
      const json: ProcesarResponse = await res.json();

      if (json.status === "success") {
        setResult(json.data);
      } else {
        setError(json.errors?.join(", ") || "Error al procesar");
      }
    } catch (err) {
      setError("Error de conexión: " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  /* ---------- expedientes flat list ---------- */
  const expedientes = result ? collectExpedientes(result.estructura) : [];

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Auditoría PDF" }]} />
      <PageTitle
        eyebrow="EPS MALLAMAS"
        title="Auditoría de Expedientes PDF"
        description="Ingresa la ruta de la carpeta para analizar FEV, PDE y soportes."
      />

      {/* Input card */}
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
              placeholder="D:\Carpetas\Expedientes\..."
              className="flex-1 rounded-md border border-border bg-background px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>
          <p className="text-xs text-muted-foreground mt-1.5 mb-4">
            Ruta completa de la carpeta con subcarpetas de expedientes (FEV*.pdf, PDE*.pdf, soportes).
          </p>

          <div className="flex justify-end">
            <Button type="submit" disabled={loading || !ruta.trim()}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Procesando...
                </>
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

      {/* Error banner */}
      {error && (
        <Card className="p-6 border-danger/30 bg-danger/5 shadow-none mb-6">
          <div className="flex items-center gap-3">
            <XCircle className="h-5 w-5 text-danger" />
            <p className="text-sm font-medium text-danger">{error}</p>
          </div>
        </Card>
      )}

      {/* Loading state (no results yet) */}
      {loading && !result && (
        <Card className="p-6 border-border bg-card shadow-none mb-6">
          <div className="flex items-center justify-center py-8 gap-3">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Procesando expedientes...</p>
          </div>
        </Card>
      )}

      {/* Empty state */}
      {result && expedientes.length === 0 && (
        <Card className="p-6 border-border bg-card shadow-none mb-6">
          <div className="flex items-center justify-center py-8 gap-3">
            <FolderOpen className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No se encontraron expedientes con PDFs en la ruta especificada.</p>
          </div>
        </Card>
      )}

      {/* Results tree */}
      {result && expedientes.length > 0 && (
        <Card className="p-6 border-border bg-card shadow-none">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-success" />
              <div>
                <h2 className="font-display font-semibold text-foreground">
                  {expedientes.length} expediente{expedientes.length !== 1 ? "s" : ""} encontrado{expedientes.length !== 1 ? "s" : ""}
                </h2>
                <p className="text-xs text-muted-foreground">
                  Ruta: {result.ruta}
                </p>
              </div>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-1" />
              JSON
            </Button>
          </div>

          {expedientes.map(({ nombre, data }) => {
            const isError = hasError(data);
            const isExpanded = expanded.has(nombre);

            return (
              <div key={nombre} className="mb-3 last:mb-0 rounded-md border border-border">
                {/* Header */}
                <button
                  type="button"
                  onClick={() => toggleExpand(nombre)}
                  className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-muted/40 transition-colors rounded-t-md"
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                  )}
                  <FolderOpen className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="font-display font-semibold text-foreground text-sm truncate">
                    {nombre}
                  </span>
                  {isError && <StatusBadge tone="danger">Alerta</StatusBadge>}
                  {!isError && <StatusBadge tone="success">OK</StatusBadge>}
                </button>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-1 border-t border-border space-y-3">
                    {/* Archivos list */}
                    <div className="space-y-1">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Archivos</p>
                      {data.archivos.map((archivo) => (
                        <div key={archivo.archivo} className="flex items-center gap-2 text-xs">
                          {getFileTypeIcon(archivo.tipo)}
                          <span className={archivo.error ? "text-danger" : "text-foreground/80"}>
                            {archivo.archivo}
                          </span>
                          {archivo.error && (
                            <span className="text-danger ml-1">({archivo.error})</span>
                          )}
                          {archivo.tipo === "FEV" && archivo.data && (
                            <span className="text-muted-foreground ml-auto">
                              {(archivo.data as Record<string, unknown>)?.servicios
                                ? `${Object.keys((archivo.data as Record<string, unknown>)?.servicios as Record<string, unknown>).length} categorías`
                                : ""}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Alertas */}
                    {data.alerta_archivos && (
                      <div className="flex items-center gap-2 p-2 rounded bg-danger/5 border border-danger/20">
                        <AlertTriangle className="h-4 w-4 text-danger shrink-0" />
                        <p className="text-xs font-medium text-danger">{data.alerta_archivos.mensaje}</p>
                      </div>
                    )}

                    {/* Duplicado global */}
                    {data.duplicado_global && (
                      <div className="flex items-start gap-2 p-2 rounded bg-warning/5 border border-warning/20">
                        <AlertTriangle className="h-4 w-4 text-warning-foreground shrink-0 mt-0.5" />
                        <div>
                          <p className="text-xs font-medium text-warning-foreground">{data.duplicado_global.mensaje}</p>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            Ubicaciones: {data.duplicado_global.ubicaciones.join(", ")}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Validación FEV vs PDE */}
                    {data.validacion && (
                      <div className="space-y-1">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Validación FEV vs PDE
                        </p>
                        {data.validacion.diferencias && Object.keys(data.validacion.diferencias).length > 0 ? (
                          <div className="p-2 rounded bg-danger/5 border border-danger/20">
                            {Object.entries(data.validacion.diferencias).map(([campo, detalle]) => (
                              <p key={campo} className="text-xs text-danger">
                                <strong>{campo}:</strong> {JSON.stringify(detalle)}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-success flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Sin diferencias
                          </p>
                        )}
                      </div>
                    )}

                    {/* Validación soportes */}
                    {data.validacion_soportes && (
                      <div className="space-y-1">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Validación de Soportes
                        </p>
                        {data.validacion_soportes.validacion_soportes &&
                        data.validacion_soportes.validacion_soportes.length > 0 ? (
                          <div className="p-2 rounded bg-warning/5 border border-warning/20">
                            {data.validacion_soportes.validacion_soportes.map((s, i) => (
                              <p key={i} className="text-xs text-warning-foreground">
                                Código {String(s.codigo ?? "")}: {String(s.estado ?? "")}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-success flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Todos los soportes validados
                          </p>
                        )}
                        {data.validacion_soportes.codigos_sin_regla &&
                          data.validacion_soportes.codigos_sin_regla.length > 0 && (
                            <p className="text-xs text-muted-foreground">
                              Códigos sin regla: {data.validacion_soportes.codigos_sin_regla.join(", ")}
                            </p>
                          )}
                      </div>
                    )}
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
