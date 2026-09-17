import { useState, useRef, useEffect, useCallback } from "react";
import {
  Upload,
  Info,
  FileSpreadsheet,
  ArrowRight,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Check,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";
import {
  norm,
  buildObservacion,
  buildEnvioSet,
  getEnvioEstado,
  canShowEnvio,
} from "./utils";

const TOAST_DURATION = 2500;

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
  regla?: string;
  _enviada?: boolean;
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
  canControl?: boolean;
}

// ---------------------------------------------------------------------------
// Toast (clon abiertas-urgencias/page.tsx L56-75)
// ---------------------------------------------------------------------------

function Toast({
  message,
  onDone,
}: {
  message: string;
  onDone: () => void;
}) {
  useEffect(() => {
    const t = setTimeout(onDone, TOAST_DURATION);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background shadow-lg">
        {message}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export function ProcesarPage({
  can_write = false,
  canControl = false,
}: ProcesarPageProps) {
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

  // ── Envío a Control state (clon abiertas-urgencias) ──
  const envioExistentes = useRef<Set<string>>(new Set());
  const envioEnviadas = useRef<Set<string>>(new Set());
  const [envioVersion, setEnvioVersion] = useState(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
  }, []);

  const showEnvio = canShowEnvio(can_write, canControl);

  // Preload único: GET /api/control-errores → Set global normalizado
  useEffect(() => {
    if (!showEnvio) return;
    fetch("/api/control-errores")
      .then((res) => res.json())
      .then((data) => {
        const errores =
          data.status === "success" && data.data?.errores
            ? (data.data.errores as Array<{
                factura?: string;
                tipo_error?: string;
              }>)
            : [];
        envioExistentes.current = buildEnvioSet(errores);
        setEnvioVersion((v) => v + 1);
      })
      .catch(() => {
        envioExistentes.current = new Set();
      });
  }, [showEnvio]);

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

  const handleSendToControl = async (
    factura: string,
    descripcion: string,
    responsable: string,
    reglaDetalle = "",
  ) => {
    if (!can_write || !canControl) {
      showToast("Iniciá sesión para enviar");
      return;
    }
    if (!factura) return;

    const alreadyExists = envioExistentes.current.has(norm(factura));
    if (alreadyExists) {
      if (
        !(await window.__showConfirm!(
          `La factura "${factura}" ya existe en la tabla de Control de Errores.\n¿Querés duplicarla de todas formas?`,
        ))
      ) {
        return;
      }
    } else {
      if (
        !(await window.__showConfirm!(
          `¿Enviar factura "${factura}" a Control de Errores como "Factura Abierta"?`,
        ))
      ) {
        return;
      }
    }

    const observacion = buildObservacion(descripcion, reglaDetalle);

    try {
      const res = await fetch("/api/control-errores", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tipo_error: "Factura Abierta",
          factura,
          observacion,
          estado: "S",
          responsable: responsable || "",
        }),
      });
      const json = await res.json();
      if (json.status === "success") {
        envioEnviadas.current.add(norm(factura));
        envioExistentes.current.add(norm(factura));
        setResult((prev) =>
          prev
            ? {
                ...prev,
                errores: prev.errores.map((fg) => ({
                  ...fg,
                  tipos: fg.tipos.map((tg) => ({
                    ...tg,
                    facturas: tg.facturas.map((x) =>
                      x.factura === factura ? { ...x, _enviada: true } : x,
                    ),
                  })),
                })),
              }
            : prev,
        );
        setEnvioVersion((v) => v + 1);
        showToast(`✅ Factura "${factura}" enviada a Control de Errores`);
      } else {
        const errs = json.errors || ["Error desconocido"];
        showToast("Error: " + errs.join(", "));
      }
    } catch {
      showToast("Error de conexión al enviar");
    }
  };

  const allFacturas = result?.errores?.flatMap((fg) => fg.tipos.flatMap((tg) => tg.facturas)) ?? [];

  // Referencia envioVersion para re-render tras preload/envío (refs no disparan render)
  void envioVersion;

  return (
    <div className="mx-auto max-w-6xl">
      {toastMessage && (
        <Toast message={toastMessage} onDone={() => setToastMessage(null)} />
      )}
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
                                <th className="text-left font-medium px-4 py-3">Regla</th>
                                <th className="text-left font-medium px-4 py-3">Responsable cierre</th>
                                <th className="text-left font-medium px-4 py-3">Descripción</th>
                                <th className="text-left font-medium px-4 py-3">Detalle A</th>
                                <th className="text-left font-medium px-4 py-3">Detalle B</th>
                                {showEnvio && (
                                  <th className="text-center font-medium px-4 py-3">Envío</th>
                                )}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                              {tg.facturas.slice(0, 50).map((f: FacturaItem, i: number) => {
                                  const estado = getEnvioEstado(
                                    f.factura,
                                    Boolean(
                                      f._enviada ||
                                        envioEnviadas.current.has(
                                          norm(f.factura),
                                        ),
                                    ),
                                    envioExistentes.current,
                                  );
                                  let envioCell: React.ReactNode;
                                  if (estado === "enviada") {
                                    envioCell = (
                                      <span
                                        className="inline-flex items-center justify-center rounded-sm bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success"
                                        title="Enviada a Control"
                                      >
                                        <Check className="h-3 w-3" />
                                      </span>
                                    );
                                  } else if (!showEnvio) {
                                    envioCell = null;
                                  } else if (estado === "duplicada") {
                                    envioCell = (
                                      <button
                                        className="inline-flex items-center justify-center rounded-sm bg-warning/10 px-1.5 py-0.5 text-[10px] font-medium text-warning-foreground hover:bg-warning/20 transition-colors w-full"
                                        title="Ya está en Control — Click para duplicar"
                                        onClick={() =>
                                          handleSendToControl(
                                            f.factura,
                                            f.descripcion,
                                            f.responsable_cierra || "",
                                            f.regla || f.detalle || "",
                                          )
                                        }
                                      >
                                        ⚠
                                      </button>
                                    );
                                  } else {
                                    envioCell = (
                                      <button
                                        className="inline-flex items-center justify-center rounded-sm bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary w-full hover:bg-primary/20 transition-colors"
                                        title="Enviar a Control de Errores"
                                        onClick={() =>
                                          handleSendToControl(
                                            f.factura,
                                            f.descripcion,
                                            f.responsable_cierra || "",
                                            f.regla || f.detalle || "",
                                          )
                                        }
                                      >
                                        <Plus className="h-3 w-3" />
                                      </button>
                                    );
                                  }
                                  return (
                                  <tr
                                    key={`${f.factura}-${i}`}
                                    className={cn(
                                      "hover:bg-muted/30 transition-colors",
                                      f.fecha_cierre_vacia && "bg-amber-50"
                                    )}
                                  >
                                    <td className="px-4 py-3 text-xs text-foreground/80">{f.fec_factura || "-"}</td>
                                    <td className="px-4 py-3 font-mono text-xs font-medium text-foreground">{f.factura}</td>
                                    <td className="px-4 py-3 font-mono text-xs text-foreground/70">{f.regla || "-"}</td>
                                    <td className="px-4 py-3 text-xs text-foreground/80">{f.responsable_cierra || "-"}</td>
                                    <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs">{f.descripcion}</td>
                                    <td className="px-4 py-3 text-xs text-foreground/70 max-w-xs">{f.procedimiento || "-"}</td>
                                    <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs">{f.detalle || "-"}</td>
                                    {showEnvio && (
                                      <td className="px-4 py-3 text-center">{envioCell}</td>
                                    )}
                                  </tr>
                                  );
                              })}
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
