import { useState, useRef, useEffect, useCallback } from "react";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Users,
  CalendarDays,
  Upload,
  FileEdit,
  Trash2,
  Check,
  ClipboardCopy,
  Plus,
  Loader2,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { cn } from "@/lib/utils";
import { TOAST_DURATION } from "./constants";
import {
  parseScheduleText,
  autoDetectColumns,
  calcularResponsable,
  copiarHorario,
  copiarResultados,
  escapeHtml,
  type ScheduleDay,
  type FacturaResult,
} from "./utils";

interface AbiertasUrgenciasPageProps {
  can_write?: boolean;
}

// ─── Toast ────────────────────────────────────────────────────────────

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
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50">
      <div className="rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background shadow-lg">
        {message}
      </div>
    </div>
  );
}

// ─── Vencida helper ───────────────────────────────────────────────────

function parseFecha(str: string): Date | null {
  if (!str || !str.trim()) return null;
  const parts = str
    .trim()
    .match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$/);
  if (!parts) return null;
  return new Date(+parts[3], +parts[2] - 1, +parts[1]);
}

function esVencida(estado: string, fechaEgreso: string): boolean {
  if (estado !== "Abierta") return false;
  const egreso = parseFecha(fechaEgreso);
  if (!egreso) return false;
  const hoy = new Date();
  const hoyInicio = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  const diff = Math.floor(
    (hoyInicio.getTime() - egreso.getTime()) / 86400000,
  );
  return diff > 4;
}

// ─── Component ────────────────────────────────────────────────────────

export function AbiertasUrgenciasPage({
  can_write = false,
}: AbiertasUrgenciasPageProps) {
  // ── Schedule state ──
  const [schedule, setSchedule] = useState<ScheduleDay[] | null>(null);
  const [scheduleStatus, setScheduleStatus] = useState<
    "loading" | "loaded" | "empty"
  >("loading");
  const [scheduleText, setScheduleText] = useState("");
  const [showParseCard, setShowParseCard] = useState(false);

  // ── Responsible assignment state ──
  const [facturasText, setFacturasText] = useState("");
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<FacturaResult[] | null>(null);
  const [showRespCard, setShowRespCard] = useState(false);
  const [showResults, setShowResults] = useState(false);

  // ── Envío tracking refs (no re-renders needed) ──
  const envioExistentes = useRef(new Set<string>());
  const envioEnviadas = useRef(new Set<string>());

  // ── UI state ──
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = useCallback(
    (msg: string) => {
      setToastMessage(msg);
    },
    [],
  );

  // ── Schedule card toggle ──
  const [openHorario, setOpenHorario] = useState(true);

  // ── Load schedule on mount ──
  const loadSchedule = useCallback(async () => {
    setScheduleStatus("loading");
    try {
      const res = await fetch("/abiertas-urgencias/api/schedule");
      const result = await res.json();
      if (result.status === "success" && result.data?.horario) {
        const dias = result.data.horario.dias || [];
        setSchedule(dias);
        setScheduleStatus(dias.length > 0 ? "loaded" : "empty");
      } else {
        setSchedule(null);
        setScheduleStatus("empty");
      }
    } catch {
      setSchedule(null);
      setScheduleStatus("empty");
    }
  }, []);

  useEffect(() => {
    loadSchedule();
  }, [loadSchedule]);

  // ── Schedule handlers ──
  const handleToggleParseCard = () => {
    if (!can_write) {
      showToast("Iniciá sesión para modificar");
      return;
    }
    setShowParseCard((p) => !p);
  };

  const handleParseAndSave = async () => {
    if (!can_write) {
      showToast("Iniciá sesión para modificar");
      return;
    }
    if (!scheduleText.trim()) {
      showToast("Pegá el texto del horario primero.");
      return;
    }

    const dias = parseScheduleText(scheduleText);
    if (!dias) {
      showToast("No se pudo parsear el horario. Verificá el formato.");
      return;
    }

    try {
      const res = await fetch("/abiertas-urgencias/api/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dias }),
      });
      const result = await res.json();
      if (result.status === "success") {
        showToast("✅ Horario guardado — " + dias.length + " días");
        setSchedule(dias);
        setScheduleStatus("loaded");
        setShowParseCard(false);
        setScheduleText("");
      } else {
        const errs = result.errors || ["Error desconocido"];
        showToast("Error al guardar: " + errs.join(", "));
      }
    } catch {
      showToast("Error de conexión al guardar el horario.");
    }
  };

  const handleDeleteSchedule = async () => {
    if (!can_write) {
      showToast("Iniciá sesión para modificar");
      return;
    }
    if (!confirm("¿Eliminar el horario cargado?")) return;

    try {
      const res = await fetch("/abiertas-urgencias/api/schedule", {
        method: "DELETE",
      });
      const result = await res.json();
      if (result.status === "success") {
        showToast("Horario eliminado");
        setSchedule(null);
        setScheduleStatus("empty");
      }
    } catch {
      showToast("Error al eliminar");
    }
  };

  const handleCopiarHorario = () => {
    if (schedule) copiarHorario(schedule, showToast);
  };

  // ── Responsible assignment handlers ──
  const handleProcesarFacturas = () => {
    if (!facturasText.trim()) {
      showToast("Pegá los datos de facturación primero.");
      return;
    }

    if (!schedule || schedule.length === 0) {
      showToast(
        "⚠️ No hay horario cargado. Primero cargá el cronograma en la sección de arriba.",
      );
      return;
    }

    setProcessing(true);

    try {
      const rawLines = facturasText
        .replace(/\r\n/g, "\n")
        .replace(/\r/g, "\n")
        .split("\n");
      const lines = rawLines.filter((l) => l.trim() !== "");

      if (lines.length < 2) {
        showToast("Se necesitan al menos 2 líneas (encabezados + datos).");
        setProcessing(false);
        return;
      }

      const firstRow = lines[0].split("\t");
      const secondRow = lines[1].split("\t");
      const hasHeaders =
        firstRow.length >= 4 &&
        firstRow.length === secondRow.length &&
        firstRow.some((h) => /[a-z]/i.test(h)) &&
        !/^\d/.test(firstRow[0]);

      const headers = hasHeaders ? firstRow.map((h) => h.trim()) : [];
      const dataLines = hasHeaders ? lines.slice(1) : lines;

      const firstDataRow = dataLines[0].split("\t").map((c) => c.trim());
      const { cols } = autoDetectColumns(headers, firstDataRow);

      if (cols.fechaCreaIdx === -1 || cols.fechaEgresoIdx === -1) {
        showToast(
          "No se pudieron detectar las columnas de fecha. Verificá el formato.",
        );
        setProcessing(false);
        return;
      }

      // Pre-load existing records for duplicate detection
      fetch("/api/control-errores")
        .then((res) => res.json())
        .then((data) => {
          const set = new Set<string>();
          if (
            data.status === "success" &&
            data.data &&
            data.data.errores
          ) {
            data.data.errores.forEach(
              (e: { factura?: string }) => e.factura && set.add(e.factura),
            );
          }
          envioExistentes.current = set;
        })
        .catch(() => {
          envioExistentes.current = new Set();
        });

      // Process each row
      const newResults: FacturaResult[] = [];
      for (const line of dataLines) {
        const cells = line.split("\t").map((c) => c.trim());

        const fechaCrea =
          cols.fechaCreaIdx >= 0 ? cells[cols.fechaCreaIdx] || "" : "";
        const fechaEgreso =
          cols.fechaEgresoIdx >= 0 ? cells[cols.fechaEgresoIdx] || "" : "";
        let factura =
          cols.facturaIdx >= 0 ? cells[cols.facturaIdx] || "" : "";
        // Concatenate FEV standalone prefix with next column digits
        if (
          factura &&
          /^(CAP|FEV)$/i.test(factura) &&
          cols.facturaIdx + 1 < cells.length
        ) {
          const nextVal = (cells[cols.facturaIdx + 1] || "").trim();
          if (/^\d+$/.test(nextVal)) factura = factura + nextVal;
        }
        const estado =
          cols.estadoIdx >= 0 ? cells[cols.estadoIdx] || "" : "";
        const area = cols.areaIdx >= 0 ? cells[cols.areaIdx] || "" : "";
        const paciente =
          cols.pacienteIdx >= 0 ? cells[cols.pacienteIdx] || "" : "";
        const hcPendiente =
          cols.hcPendienteIdx >= 0 ? cells[cols.hcPendienteIdx] || "" : "";

        const responsable = calcularResponsable(
          fechaCrea,
          fechaEgreso,
          schedule,
        );

        newResults.push({
          fechaCrea,
          fechaEgreso,
          factura,
          estado,
          responsable,
          area,
          paciente,
          hcPendiente,
        });
      }

      if (newResults.length === 0) {
        showToast("No se encontraron filas de datos válidas.");
        setProcessing(false);
        return;
      }

      setResults(newResults);
      setShowResults(true);
      setShowRespCard(false);
      showToast("✅ " + newResults.length + " facturas procesadas");
    } catch {
      showToast("Error al procesar los datos.");
    } finally {
      setProcessing(false);
    }
  };

  const handleSendToControl = async (
    factura: string,
    responsable: string,
    _idx: number,
  ) => {
    if (!can_write) {
      showToast("Iniciá sesión para enviar");
      return;
    }
    if (!factura) return;

    const alreadyExists = envioExistentes.current.has(factura);
    if (alreadyExists) {
      if (
        !confirm(
          `La factura "${factura}" ya existe en la tabla de Control de Errores.\n¿Querés duplicarla de todas formas?`,
        )
      ) {
        return;
      }
    } else {
      if (
        !confirm(
          `¿Enviar factura "${factura}" a Control de Errores como "Factura Abierta"?`,
        )
      ) {
        return;
      }
    }

    // Find the result to get area and egreso
    const r = results?.find((x) => x.factura === factura);
    const area = r?.area || "";
    const egreso = r?.fechaEgreso || "";

    let egresoShort = "";
    if (egreso) {
      const match = egreso.match(/^(\d{2}\/\d{2}\/\d{4})/);
      egresoShort = match ? match[1] : egreso.substring(0, 10);
    }

    const observacion = [
      area,
      egresoShort,
      "Factura abierta con responsable segun cronograma de facturadores",
    ]
      .filter(Boolean)
      .join(" - ");

    const data = {
      tipo_error: "Factura Abierta",
      factura,
      observacion,
      observacion_facturador: "",
      estado: "S" as const,
      responsable: responsable || "",
    };

    try {
      const res = await fetch("/api/control-errores", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await res.json();
      if (result.status === "success") {
        envioEnviadas.current.add(factura);
        envioExistentes.current.add(factura);
        // Mark result as sent
        setResults((prev) =>
          prev
            ? prev.map((x) =>
                x.factura === factura ? { ...x, _enviada: true } : x,
              )
            : prev,
        );
        showToast(
          '✅ Factura "' + factura + '" enviada a Control de Errores',
        );
      } else {
        const errs = result.errors || ["Error desconocido"];
        showToast("Error: " + errs.join(", "));
      }
    } catch {
      showToast("Error de conexión al enviar");
    }
  };

  const handleCopiarResultados = () => {
    if (results) {
      copiarResultados(
        results,
        envioExistentes.current,
        envioEnviadas.current,
        showToast,
      );
    }
  };

  // ── Render helpers ──

  const statusIcon = () => {
    if (scheduleStatus === "loading")
      return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />;
    if (scheduleStatus === "loaded")
      return <Check className="h-5 w-5 text-success" />;
    return <CalendarDays className="h-5 w-5 text-warning" />;
  };

  const statusTitle = () => {
    if (scheduleStatus === "loading") return "Cargando...";
    if (scheduleStatus === "loaded")
      return (
        <>
          Horario cargado — <strong>{schedule?.length ?? 0} días</strong>
        </>
      );
    return "Falta cargar horario";
  };

  const statusMeta = () => {
    if (scheduleStatus === "loading") return "";
    if (scheduleStatus === "loaded")
      return (
        "Actualizado. " +
        (schedule?.length ?? 0) +
        " turnos cargados para el mes."
      );
    return 'No hay horario para el mes actual. Usá "Cargar" para agregar los turnos del mes.';
  };

  return (
    <div className="mx-auto max-w-5xl">
      {/* Toast */}
      {toastMessage && (
        <Toast
          message={toastMessage}
          onDone={() => setToastMessage(null)}
        />
      )}

      <Breadcrumbs items={[{ label: "Abiertas Urgencias" }]} />

      <PageTitle
        eyebrow="Servicio de Urgencias"
        title="Abiertas Urgencias"
        description="Visualiza y gestiona los horarios del personal asignado a urgencias."
        actions={
          <Button variant="outline" size="sm" asChild>
            <a href="/control-novedades">
              <ArrowLeft className="h-4 w-4" />
              Volver a control
            </a>
          </Button>
        }
      />

      {/* ═══════════════════ Asignar Responsable ═══════════════════ */}
      <Card className="border-border bg-card shadow-none mb-4 overflow-hidden">
        <button
          onClick={() => setShowRespCard((p) => !p)}
          className="w-full flex items-center gap-4 p-5 text-left hover:bg-muted/30 transition-colors"
        >
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Users className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground">
              Asignar responsable desde horario
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Pega los datos de facturación para asignar automáticamente el
              responsable según el cronograma
            </p>
          </div>
          {showRespCard ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </button>
        {showRespCard && (
          <div className="border-t border-border p-5 bg-muted/20">
            <textarea
              value={facturasText}
              onChange={(e) => setFacturasText(e.target.value)}
              placeholder="Pega aquí los datos de facturación…"
              rows={10}
              className="w-full min-h-32 rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <div className="mt-3 flex justify-end gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setShowRespCard(false);
                  setFacturasText("");
                }}
              >
                Cancelar
              </Button>
              <Button
                size="sm"
                className="bg-primary hover:bg-primary/90"
                disabled={processing || !can_write}
                title={
                  !can_write ? "Iniciá sesión para modificar" : undefined
                }
                onClick={handleProcesarFacturas}
              >
                {processing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Procesando…
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4" />
                    Procesar y Asignar Responsable
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* ═══════════════════ Resultados Responsable ═══════════════════ */}
      {showResults && results && results.length > 0 && (
        <Card className="border-border bg-card shadow-none mb-4 overflow-hidden">
          <div className="flex items-center justify-between p-5 border-b border-border">
            <div>
              <h3 className="font-semibold text-foreground">
                Facturas con Responsable Asignado
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {results.length} facturas
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleCopiarResultados}
            >
              <ClipboardCopy className="h-4 w-4" />
              Copiar a Excel
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs table-fixed" style={{ minWidth: 720 }}>
              <colgroup>
                <col className="w-[13%]" />
                <col className="w-[13%]" />
                <col className="w-[11%]" />
                <col className="w-[9%]" />
                <col className="w-[13%]" />
                <col className="w-[9%]" />
                <col className="w-[18%]" />
                <col className="w-[6%]" />
                <col className="w-[8%]" />
              </colgroup>
              <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="text-left font-medium px-2 py-2">Crea</th>
                  <th className="text-left font-medium px-2 py-2">Egreso</th>
                  <th className="text-left font-medium px-2 py-2">Factura</th>
                  <th className="text-left font-medium px-2 py-2">Estado</th>
                  <th className="text-left font-medium px-2 py-2">Resp.</th>
                  <th className="text-left font-medium px-2 py-2">Área</th>
                  <th className="text-left font-medium px-2 py-2">Paciente</th>
                  <th className="text-center font-medium px-1 py-2">HC</th>
                  <th className="text-center font-medium px-1 py-2">Envío</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {results.map((r, idx) => {
                  const isVencida = esVencida(r.estado, r.fechaEgreso);
                  const yaExiste = envioExistentes.current.has(r.factura);
                  const yaEnviada =
                    r._enviada || envioEnviadas.current.has(r.factura);
                  const isSinEgreso = r.responsable === "Sin Egreso";

                  let actionHtml: React.ReactNode;
                  if (yaEnviada) {
                    actionHtml = (
                      <span
                        className="inline-flex items-center justify-center rounded-sm bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success"
                        title="Enviada a Control"
                      >
                        <Check className="h-3 w-3" />
                      </span>
                    );
                  } else if (!can_write) {
                    actionHtml = (
                      <span
                        className="inline-flex items-center justify-center rounded-sm bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground opacity-40"
                        title="Iniciá sesión para enviar"
                      >
                        {yaExiste ? "⚠" : "+"}
                      </span>
                    );
                  } else if (yaExiste) {
                    actionHtml = (
                      <button
                        className="inline-flex items-center justify-center rounded-sm bg-warning/10 px-1.5 py-0.5 text-[10px] font-medium text-warning-foreground hover:bg-warning/20 transition-colors w-full"
                        title="Ya está en Control — Click para duplicar"
                        onClick={() =>
                          handleSendToControl(r.factura, r.responsable, idx)
                        }
                      >
                        ⚠
                      </button>
                    );
                  } else {
                    actionHtml = (
                      <button
                        className="inline-flex items-center justify-center rounded-sm bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary hover:bg-primary/20 transition-colors w-full"
                        title="Enviar a Control de Errores"
                        onClick={() =>
                          handleSendToControl(r.factura, r.responsable, idx)
                        }
                      >
                        <Plus className="h-3 w-3" />
                      </button>
                    );
                  }

                  return (
                    <tr
                      key={`${r.factura}-${idx}`}
                      className={cn(
                        "hover:bg-muted/30 transition-colors",
                        isVencida && "resp-row--vencida bg-danger/5",
                      )}
                    >
                      <td className="px-2 py-1.5 font-mono text-xs text-foreground truncate">
                        {escapeHtml(r.fechaCrea || "—")}
                      </td>
                      <td className="px-2 py-1.5 font-mono text-xs text-foreground truncate">
                        {escapeHtml(r.fechaEgreso || "—")}
                      </td>
                      <td className="px-2 py-1.5 font-mono text-xs font-semibold text-foreground truncate">
                        {escapeHtml(r.factura || "—")}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-foreground/80 truncate">
                        {escapeHtml(r.estado || "—")}
                      </td>
                      <td className="px-2 py-1.5 text-xs truncate">
                        <span className={cn(isSinEgreso && "text-warning-foreground")}>
                          {escapeHtml(r.responsable || "—")}
                        </span>
                      </td>
                      <td className="px-2 py-1.5 text-xs text-foreground/80 truncate">
                        {escapeHtml(r.area || "—")}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-foreground/80 truncate">
                        {escapeHtml(r.paciente || "—")}
                      </td>
                      <td className="px-1 py-1.5 text-xs text-foreground/70 text-center">
                        {escapeHtml(r.hcPendiente || "—")}
                      </td>
                      <td className="px-1 py-1.5 text-center">{actionHtml}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ═══════════════════ Status Bar ═══════════════════ */}
      <Card
        className={cn(
          "border-border bg-card shadow-none mb-4 overflow-hidden",
        )}
      >
        <div className="flex items-center gap-4 p-5">
          <div
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-md",
              scheduleStatus === "loading" && "bg-muted text-muted-foreground",
              scheduleStatus === "loaded" && "bg-success/10 text-success",
              scheduleStatus === "empty" && "bg-warning/10 text-warning-foreground",
            )}
          >
            {statusIcon()}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground">{statusTitle()}</h3>
            {statusMeta() && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {statusMeta()}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={!can_write}
              title={
                !can_write ? "Iniciá sesión para modificar" : undefined
              }
              onClick={handleToggleParseCard}
            >
              <FileEdit className="h-4 w-4" />
              {scheduleStatus === "loaded" ? "Editar" : "Cargar"}
            </Button>
            {scheduleStatus === "loaded" && (
              <Button
                size="sm"
                variant="destructive"
                disabled={!can_write}
                title={
                  !can_write ? "Iniciá sesión para modificar" : undefined
                }
                onClick={handleDeleteSchedule}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* ═══════════════════ Parse Card (collapsible) ═══════════════════ */}
      {showParseCard && (
        <Card className="border-border bg-card shadow-none mb-4 overflow-hidden">
          <div className="border-t border-border p-5 bg-muted/20">
            <textarea
              value={scheduleText}
              onChange={(e) => setScheduleText(e.target.value)}
              placeholder="Pegá acá el texto del horario..."
              rows={12}
              className="w-full rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <div className="mt-3 flex justify-end gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setShowParseCard(false);
                  setScheduleText("");
                }}
              >
                Cancelar
              </Button>
              <Button
                size="sm"
                className="bg-primary hover:bg-primary/90"
                disabled={!can_write}
                title={
                  !can_write ? "Iniciá sesión para modificar" : undefined
                }
                onClick={handleParseAndSave}
              >
                <Upload className="h-4 w-4" />
                Parsear y Guardar
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* ═══════════════════ Ver Horario ═══════════════════ */}
      <Card className="border-border bg-card shadow-none mb-4 overflow-hidden">
        <button
          onClick={() => setOpenHorario(!openHorario)}
          className="w-full flex items-center gap-4 p-5 text-left hover:bg-muted/30 transition-colors"
        >
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-secondary/15 text-secondary">
            <CalendarDays className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground">Ver horario</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {schedule && schedule.length > 0
                ? schedule.length + " días cargados — clic para ver"
                : "Turnos cargados del mes en curso"}
            </p>
          </div>
          {openHorario ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </button>
        {openHorario && (
          <div className="border-t border-border">
            <div className="overflow-x-auto">
              <table className="w-full text-xs table-fixed" style={{ minWidth: 400 }}>
                <colgroup>
                  <col className="w-[12%]" />
                  <col className="w-[29.3%]" />
                  <col className="w-[29.3%]" />
                  <col className="w-[29.3%]" />
                </colgroup>
                <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="text-center font-medium px-2 py-2">Día</th>
                    <th className="text-left font-medium px-2 py-2">07-13</th>
                    <th className="text-left font-medium px-2 py-2">13-19</th>
                    <th className="text-left font-medium px-2 py-2">19-07</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {schedule && schedule.length > 0 ? (
                    <>
                      {schedule.map((row) => (
                        <tr
                          key={row.dia}
                          className="hover:bg-muted/30 transition-colors"
                        >
                          <td className="px-2 py-1.5 text-xs font-medium text-foreground text-center">
                            {row.dia}
                          </td>
                          <td className="px-2 py-1.5 text-xs text-foreground/80 truncate">
                            {escapeHtml(row.manana)}
                          </td>
                          <td className="px-2 py-1.5 text-xs text-foreground/80 truncate">
                            {escapeHtml(row.tarde)}
                          </td>
                          <td className="px-2 py-1.5 text-xs text-foreground/80 truncate">
                            {escapeHtml(row.noche)}
                          </td>
                        </tr>
                      ))}
                    </>
                  ) : (
                    <tr>
                      <td
                        colSpan={4}
                        className="px-3 py-10 text-center text-muted-foreground"
                      >
                        <CalendarDays className="h-6 w-6 text-muted-foreground/40 mx-auto mb-1" />
                        <p className="text-xs">
                          {scheduleStatus === "loading"
                            ? "Cargando..."
                            : 'Sin datos de horario'}
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {schedule && schedule.length > 0 && (
              <div className="border-t border-border px-3 py-2 flex justify-end">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCopiarHorario}
                >
                  <ClipboardCopy className="h-3.5 w-3.5" />
                  Copiar
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
