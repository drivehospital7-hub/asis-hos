import { useState, useEffect } from "react";
import {
  Play,
  FileDown,
  AlertCircle,
  CheckCircle2,
  XCircle,
  FolderOpen,
  FileText,
  Save,
  Plus,
  Trash2,
  Radio,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

interface ConfigResponse {
  status: string;
  data: {
    roots: string[];
    fuente: string;
    ultima_actualizacion: string | null;
  };
  errors: string[];
}

interface ScanResponse {
  status: string;
  data: {
    monitoring?: boolean;
    cached?: boolean;
    message?: string;
    events_count?: number;
    observer_alive?: boolean;
    facturas: InvoiceData[];
    indicadores: Record<string, number>;
    duplicados: Array<{ filename: string; facturadores: string[] }>;
    vacias: Array<{ facturador: string; folder: string }>;
    errores_scan: Array<{ root: string; error: string }>;
    excel_download: string | null;
    scanned_roots: string[];
  };
  errors: string[];
}

export function MonitoreoCarpetasPage({ can_write = false }: { can_write?: boolean }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResponse["data"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [facturadorFilter, setFacturadorFilter] = useState<string>("");

  // Config state
  const [configRoots, setConfigRoots] = useState<string[]>([]);
  const [configSavedRoots, setConfigSavedRoots] = useState<string[]>([]);
  const [configFuente, setConfigFuente] = useState<string>("");
  const [configSaving, setConfigSaving] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configSuccess, setConfigSuccess] = useState<string | null>(null);

  // Derived: config is dirty when roots differ from last saved state
  const configDirty =
    configRoots.length !== configSavedRoots.length ||
    configRoots.some((r, i) => r !== configSavedRoots[i]);

  // Fetch config + cached scan data on mount
  useEffect(() => {
    fetch("/monitoreo-carpetas/config")
      .then((res) => res.json())
      .then((data: ConfigResponse) => {
        if (data.status === "success") {
          setConfigRoots(data.data.roots);
          setConfigSavedRoots(data.data.roots);
          setConfigFuente(data.data.fuente);
        }
      })
      .catch(() => {
        // Silently fail
      });

    // Load cached scan data if available (survives page reload)
    fetch("/monitoreo-carpetas/data")
      .then((res) => res.json())
      .then((data: ScanResponse) => {
        if (data.status === "success" && data.data.cached) {
          setResult(data.data);
        }
      })
      .catch(() => {
        // Silently fail — no cache yet
      });
  }, []);

  const handleAddRoot = () => {
    setConfigRoots((prev) => [...prev, ""]);
  };

  const handleRemoveRoot = (idx: number) => {
    setConfigRoots((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleRootChange = (idx: number, value: string) => {
    // Strip surrounding quotes commonly pasted from paths
    const cleaned = value.replace(/^["']+|["']+$/g, "");
    setConfigRoots((prev) => {
      const next = [...prev];
      next[idx] = cleaned;
      return next;
    });
  };

  const handleSaveConfig = async () => {
    setConfigSaving(true);
    setConfigError(null);
    setConfigSuccess(null);

    try {
      const res = await fetch("/monitoreo-carpetas/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roots: configRoots.filter((r) => r.trim()) }),
      });
      const data = await res.json();

      if (data.status === "success") {
        setConfigRoots(data.data.roots);
        setConfigSavedRoots(data.data.roots);
        setConfigFuente(data.data.fuente);
        setConfigSuccess("Rutas guardadas correctamente.");
      } else {
        setConfigError(data.errors?.join(", ") || "Error al guardar rutas.");
      }
    } catch (err) {
      setConfigError("Error de conexión: " + (err as Error).message);
    } finally {
      setConfigSaving(false);
    }
  };

  const handleScan = async () => {
    setLoading(true);
    setError(null);

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

  // Derived: unique facturadores for filter dropdown
  const facturadores = result?.facturas
    ? [...new Set(result.facturas.map((inv) => inv.facturador))].sort()
    : [];

  // Derived: filtered facturas
  const filteredFacturas = result?.facturas?.filter(
    (inv) => !facturadorFilter || inv.facturador === facturadorFilter,
  ) ?? [];

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

      {/* Config card */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-display font-semibold text-foreground text-sm">
              Carpetas Raíz
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {configFuente === "manual"
                ? "Rutas configuradas manualmente. Los cambios requieren Guardar."
                : configFuente === "env"
                  ? "Rutas desde variable de entorno. Editalas abajo para personalizar."
                  : "Sin rutas configuradas."}
            </p>
          </div>
          {can_write && (
            <Button variant="outline" size="sm" onClick={handleAddRoot}>
              <Plus className="h-3.5 w-3.5" />
              Agregar ruta
            </Button>
          )}
        </div>

        {configRoots.length === 0 && !can_write && (
          <p className="text-xs text-muted-foreground py-2">
            No hay rutas configuradas.
          </p>
        )}

        <div className="space-y-2">
          {configRoots.map((root, idx) => (
            <div key={idx} className="flex items-center gap-2">
              {can_write ? (
                <>
                  <Input
                    value={root}
                    onChange={(e) => handleRootChange(idx, e.target.value)}
                    placeholder="\\\\servidor\\ruta"
                    className="flex-1 font-mono text-xs"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveRoot(idx)}
                    className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
                    title="Eliminar ruta"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </>
              ) : (
                <div className="flex-1 rounded-lg border border-border/50 bg-muted/30 px-3 py-2 font-mono text-xs text-foreground/80">
                  {root || "—"}
                </div>
              )}
            </div>
          ))}
        </div>

        {configDirty && can_write && (
          <p className="text-xs text-warning-foreground mt-3 flex items-center gap-1">
            <AlertCircle className="h-3 w-3" />
            Tenés cambios sin guardar. El escaneo usará las rutas guardadas previamente.
          </p>
        )}

        {can_write && (
          <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border">
            <Button onClick={handleSaveConfig} disabled={configSaving}>
              <Save className="h-4 w-4" />
              {configSaving ? "Guardando..." : "Guardar"}
            </Button>
          </div>
        )}

        {configSuccess && (
          <p className="text-xs text-success mt-2">{configSuccess}</p>
        )}
        {configError && (
          <p className="text-xs text-danger mt-2">{configError}</p>
        )}
      </Card>

      {/* Trigger card */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h3 className="font-display font-semibold text-foreground text-sm">
                Escanear Carpetas de Red
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                La primera vez ejecuta un escaneo completo. Luego watchdog monitorea cambios en tiempo real.
              </p>
            </div>
            {result?.monitoring && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-3 py-1 text-xs font-medium text-success shrink-0">
                <Radio className="h-3 w-3" />
                Monitoreando
                {result.events_count != null && (
                  <span className="text-success/70 ml-0.5">({result.events_count} eventos)</span>
                )}
              </span>
            )}
          </div>
          <Button onClick={handleScan} disabled={loading}>
            {loading ? (
              "Verificando..."
            ) : (
              <>
                <Play className="h-4 w-4" />
                Verificar
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

      {/* Scanned roots info */}
      {result && result.scanned_roots && result.scanned_roots.length > 0 && (
        <Card className="p-4 border-border bg-card shadow-none mb-4">
          <div className="flex items-center gap-2 mb-1">
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
            <p className="text-xs font-semibold text-foreground">
              Rutas escaneadas ({result.scanned_roots.length})
            </p>
          </div>
          <ul className="space-y-0.5">
            {result.scanned_roots.map((root, idx) => (
              <li key={idx} className="font-mono text-[11px] text-foreground/70 pl-6">
                {root}
              </li>
            ))}
          </ul>
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
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-success" />
                  <h3 className="font-display font-semibold text-foreground text-sm">
                    Facturas Encontradas
                    {facturadorFilter && (
                      <span className="text-muted-foreground ml-1">
                        ({filteredFacturas.length} de {result.facturas.length})
                      </span>
                    )}
                    {!facturadorFilter && (
                      <span className="text-muted-foreground ml-1">
                        ({result.facturas.length})
                      </span>
                    )}
                  </h3>
                </div>
                {facturadores.length > 1 && (
                  <select
                    value={facturadorFilter}
                    onChange={(e) => setFacturadorFilter(e.target.value)}
                    className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="">Todos los facturadores</option>
                    {facturadores.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                )}
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
                    {filteredFacturas.map((inv, idx) => (
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
