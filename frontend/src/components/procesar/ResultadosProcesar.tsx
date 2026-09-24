import { useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  FileDown,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";
import { getEnvioEstado, norm } from "@/pages/procesar/utils";
import type {
  FacturaGroup,
  FacturaItem,
  TipoGroup,
} from "./types";

interface ResultadosProcesarProps {
  errores: FacturaGroup[];
  totalErrores: number;
  /** Href for the full .xlsx download (null hides the Exportar button). */
  exportHref: string | null;
  showEnvio: boolean;
  envioExistentes: React.RefObject<Set<string>>;
  envioEnviadas: React.RefObject<Set<string>>;
  /** State version bumped after preload/sends (refs don't trigger renders). */
  envioVersion: number;
  onSendToControl: (
    factura: string,
    descripcion: string,
    responsable: string,
    detalleA?: string,
    detalleB?: string,
  ) => void;
}

/**
 * Shared /procesar results card: grouped errors by area + tipo with
 * per-row send-to-control. Used by /procesar and the rules simulator.
 */
export function ResultadosProcesar({
  errores,
  totalErrores,
  exportHref,
  showEnvio,
  envioExistentes,
  envioEnviadas,
  envioVersion,
  onSendToControl,
}: ResultadosProcesarProps) {
  const [expandedAreas, setExpandedAreas] = useState<Set<string>>(new Set());

  // Referencia envioVersion para re-render tras preload/envío (refs no disparan render)
  void envioVersion;

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

  const renderEnvioCell = (f: FacturaItem): React.ReactNode => {
    const estado = getEnvioEstado(
      f.factura,
      Boolean(
        f._enviada || envioEnviadas.current?.has(norm(f.factura)),
      ),
      envioExistentes.current ?? new Set(),
    );
    if (estado === "enviada") {
      return (
        <span
          className="inline-flex items-center justify-center rounded-sm bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success"
          title="Enviada a Control"
        >
          <Check className="h-3 w-3" />
        </span>
      );
    }
    if (!showEnvio) {
      return null;
    }
    if (estado === "duplicada") {
      return (
        <button
          className="inline-flex items-center justify-center rounded-sm bg-warning/10 px-1.5 py-0.5 text-[10px] font-medium text-warning-foreground hover:bg-warning/20 transition-colors w-full"
          title="Ya está en Control — Click para duplicar"
          onClick={() =>
            onSendToControl(
              f.factura,
              f.descripcion,
              f.responsable_cierra || "",
              f.procedimiento || "",
              f.detalle || "",
            )
          }
        >
          ⚠
        </button>
      );
    }
    return (
      <button
        className="inline-flex items-center justify-center rounded-sm bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary w-full hover:bg-primary/20 transition-colors"
        title="Enviar a Control de Errores"
        onClick={() =>
          onSendToControl(
            f.factura,
            f.descripcion,
            f.responsable_cierra || "",
            f.procedimiento || "",
            f.detalle || "",
          )
        }
      >
        <Plus className="h-3 w-3" />
      </button>
    );
  };

  const allFacturas = errores.flatMap((fg) =>
    fg.tipos.flatMap((tg) => tg.facturas),
  );
  if (allFacturas.length === 0) return null;

  return (
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

      {/* Exportar tabla completa a Excel (backend: GET export?id=) */}
      {exportHref && (
        <div className="mb-5">
          <a href={exportHref} download>
            <Button variant="outline">
              <FileDown className="h-4 w-4" />
              Exportar Excel
            </Button>
          </a>
        </div>
      )}

      {errores.map((fg: FacturaGroup) => {
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
                              <td className="px-4 py-3 font-mono text-xs text-foreground/70">{f.regla || "-"}</td>
                              <td className="px-4 py-3 text-xs text-foreground/80">{f.responsable_cierra || "-"}</td>
                              <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs">{f.descripcion}</td>
                              <td className="px-4 py-3 text-xs text-foreground/70 max-w-xs">{f.procedimiento || "-"}</td>
                              <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs">{f.detalle || "-"}</td>
                              {showEnvio && (
                                <td className="px-4 py-3 text-center">{renderEnvioCell(f)}</td>
                              )}
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
  );
}
