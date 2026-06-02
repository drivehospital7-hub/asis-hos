import { useState, useRef } from "react";
import {
  Upload,
  Info,
  FileSpreadsheet,
  ArrowRight,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface FacturaItem {
  tipo_error: string;
  factura: string;
  fec_factura: string;
  responsable_cierra: string;
  descripcion: string;
  procedimiento: string;
  detalle: string;
  fecha_cierre_vacia?: boolean;
}

interface TipoGroup {
  tipo: string;
  tipo_key: string;
  cantidad: number;
  facturas: FacturaItem[];
}

interface FacturaGroup {
  tipo_factura: string;
  total: number;
  tipos: TipoGroup[];
}

interface ProcesarPageProps {
  can_write?: boolean;
}

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export function ProcesarPage(_props: ProcesarPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    errores: FacturaGroup[];
    total_errores: number;
    tipos_procesados: string[];
  } | null>(null);
  const [error, setError] = useState("");
  const [expandedAreas, setExpandedAreas] = useState<Set<string>>(new Set());
  const inputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const toggleArea = (tipo_factura: string) => {
    const isCurrentlyOpen = expandedAreas.has(tipo_factura);
    setExpandedAreas((prev) => {
      const next = new Set(prev);
      if (next.has(tipo_factura)) next.delete(tipo_factura);
      else next.add(tipo_factura);
      return next;
    });
    // Scroll al centro de la pantalla al abrir
    if (!isCurrentlyOpen) {
      setTimeout(() => {
        const el = document.getElementById(`area-${tipo_factura}`);
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 50);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError("");
    setResult(null);

    const fd = new FormData();
    fd.append("file_upload", file);

    try {
      const res = await fetch("/procesar/", { method: "POST", body: fd });
      const json = await res.json();

      if (json.status === "error") {
        setError(json.errors?.[0] || "Error al procesar el archivo");
      } else {
        setResult(json.data);
      }
    } catch {
      setError("Error de conexión con el servidor");
    } finally {
      setLoading(false);
    }
  };

  const allFacturas = result?.errores?.flatMap((fg) => fg.tipos.flatMap((tg) => tg.facturas)) ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Procesar" }]} />
      <PageTitle
        eyebrow="Procesamiento Unificado"
        title="Procesar facturas"
        description="Cargá el reporte detallado en formato Excel. El sistema detecta automáticamente los tipos de factura y aplica las reglas correspondientes."
      />

      {/* Upload card */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <h2 className="font-display font-semibold text-foreground mb-1">Subir archivo Excel</h2>
        <p className="text-xs text-muted-foreground mb-4">
          Formatos aceptados: .xlsx, .xls, .xlsm
        </p>

        <form ref={formRef} onSubmit={handleSubmit}>
          <label
            htmlFor="file-upload"
            className="flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-10 cursor-pointer transition-colors mb-4"
            style={{ borderColor: file ? "var(--color-primary)" : "var(--color-border)" }}
          >
            {file ? (
              <div className="text-center">
                <FileSpreadsheet className="h-10 w-10 mx-auto mb-2" style={{ color: "var(--color-primary)" }} />
                <p className="text-sm font-medium text-foreground">{file.name}</p>
                <p className="text-xs mt-1" style={{ color: "var(--color-muted-foreground)" }}>
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            ) : (
              <div className="text-center">
                <Upload className="h-10 w-10 mx-auto mb-2" style={{ color: "var(--color-muted-foreground)" }} />
                <p className="text-sm" style={{ color: "var(--color-muted-foreground)" }}>
                  Arrastrá un Excel acá o <strong style={{ color: "var(--color-primary)" }}>hacé click</strong>
                </p>
                <p className="text-xs mt-1" style={{ color: "var(--color-muted-foreground)" }}>
                  Formatos: .xlsx .xls .xlsm
                </p>
              </div>
            )}
            <input
              ref={inputRef}
              id="file-upload"
              type="file"
              accept=".xlsx,.xls,.xlsm"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
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
                Los reportes cargados deben estar sin modificaciones y haberse descargado en formato detallado (Enc., Detall. o HC).
              </p>
            </div>
          </div>

          <div className="mt-5 flex justify-end">
            <Button
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
              disabled={loading || !file}
              onClick={handleSubmit}
            >
              {loading ? "Procesando…" : "Procesar archivo"}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </div>
        </form>
      </Card>

      {/* Resultados */}
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
              <div className="font-display text-2xl font-semibold text-danger">{result?.total_errores ?? allFacturas.length}</div>
              <div className="text-xs text-muted-foreground">total</div>
            </div>
          </div>

          {result?.errores?.map((fg: FacturaGroup) => {
            const isOpen = expandedAreas.has(fg.tipo_factura);
            const tiposResumen = fg.tipos.map((t) => `${t.tipo}: ${t.cantidad}`).join(" · ");
            return (
              <div key={fg.tipo_factura} className="mb-3 rounded-md border border-border overflow-hidden">
                {/* Area header — collapsible card header */}
                <button
                  id={`area-${fg.tipo_factura}`}
                  onClick={() => toggleArea(fg.tipo_factura)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-muted/40 hover:bg-muted/70 transition-colors text-left"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {isOpen ? (
                      <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    )}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-display text-sm font-semibold text-foreground">{fg.tipo_factura}</h3>
                        <StatusBadge tone="danger">{fg.total} registros</StatusBadge>
                      </div>
                      {!isOpen && tiposResumen && (
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">{tiposResumen}</p>
                      )}
                    </div>
                  </div>
                  {isOpen && (
                    <span className="text-xs text-muted-foreground shrink-0">ocultar</span>
                  )}
                </button>

                {/* Area content — tables by tipo_error */}
                {isOpen && (
                  <div className="p-4 space-y-4 border-t border-border">
                    {fg.tipos?.map((tg: TipoGroup) => (
                      <div key={tg.tipo_key}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-semibold text-foreground">{tg.tipo}</span>
                          <StatusBadge tone="danger">{tg.cantidad} registros</StatusBadge>
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
                              {tg.facturas.slice(0, 50).map((f: FacturaItem, i: number) => (
                                <tr
                                  key={`${f.factura}-${i}`}
                                  className={cn(
                                    "hover:bg-muted/30 transition-colors",
                                    f.fecha_cierre_vacia && "bg-amber-50"
                                  )}
                                >
                                  <td className="px-4 py-3 text-xs text-foreground/80">{f.fec_factura || "-"}</td>
                                  <td className="px-4 py-3 font-mono text-xs font-medium text-foreground">{f.factura}</td>
                                  <td className="px-4 py-3 text-xs text-foreground/80">{f.responsable_cierra || "-"}</td>
                                  <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs">{f.descripcion}</td>
                                  <td className="px-4 py-3 text-xs text-foreground/70 max-w-xs">{f.procedimiento || "-"}</td>
                                  <td className="px-4 py-3">
                                    <StatusBadge tone="warning">{f.detalle || "-"}</StatusBadge>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {tg.facturas.length > 50 && (
                            <div className="px-4 py-2 text-xs text-muted-foreground bg-muted/30 border-t border-border">
                              Mostrando 50 de {tg.cantidad} registros
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
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
