import { useState, useEffect, useCallback } from "react";
import { ClipboardPaste, Save, Trash2, ChevronDown, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";

interface Dia {
  dia: number;
  manana?: string;
  tarde?: string;
  noche?: string;
}

export function CronogramaUrgenciasPage() {
  const [schedule, setSchedule] = useState<Dia[] | null>(null);
  const [rawText, setRawText] = useState("");
  const [showPaste, setShowPaste] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const fetchSchedule = useCallback(async () => {
    try {
      const res = await fetch("/cronograma-urgencias/api");
      const json = await res.json();
      if (json.status === "success" && json.data?.horario) {
        setSchedule(json.data.horario);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchSchedule(); }, [fetchSchedule]);

  const toast = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 3000); };

  const handleParse = () => {
    const lines = rawText.trim().split("\n").filter(Boolean);
    if (lines.length < 2) return;

    const parsed: Dia[] = [];
    for (let i = 1; i < lines.length; i++) {
      const parts = lines[i].split("\t");
      const dia = parseInt(parts[0], 10);
      if (isNaN(dia)) continue;
      parsed.push({
        dia,
        manana: parts[1]?.trim() || "",
        tarde: parts[2]?.trim() || "",
        noche: parts[3]?.trim() || "",
      });
    }
    setSchedule(parsed);
  };

  const handleSave = async () => {
    if (!schedule || schedule.length === 0) return;
    setSaving(true);
    try {
      const res = await fetch("/cronograma-urgencias/api", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ horario: schedule }),
      });
      const json = await res.json();
      if (json.status === "success") {
        toast("Cronograma guardado");
        setShowPaste(false);
      } else {
        toast("Error al guardar");
      }
    } catch {
      toast("Error de conexión");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!await (window as any).__showConfirm?.("¿Eliminar el cronograma?")) return;
    try {
      const res = await fetch("/cronograma-urgencias/api/delete", { method: "POST" });
      const json = await res.json();
      if (json.status === "success") {
        setSchedule(null);
        toast("Cronograma eliminado");
      }
    } catch {
      toast("Error al eliminar");
    }
  };

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Cronograma Urgencias" }]} />
      <PageTitle
        eyebrow="Carga de Horario"
        title="Cronograma Urgencias"
        description="Cargá, editá o eliminá el horario mensual de Urgencias."
      />

      {msg && (
        <div className="mb-4 px-4 py-2 rounded-md bg-blue-50 text-blue-800 text-sm border border-blue-200">
          {msg}
        </div>
      )}

      {/* Collapsible paste card */}
      <Card className="p-6 mb-6">
        <button
          onClick={() => setShowPaste(!showPaste)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-2">
            <h3 className="font-display font-semibold text-foreground">Cargar cronograma</h3>
            {schedule && schedule.length > 0 && (
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">Cargado</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {schedule && schedule.length > 0 && !showPaste && (
              <>
                <button onClick={(e) => { e.stopPropagation(); setShowPaste(true); }}
                  className="text-xs text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50">
                  Editar
                </button>
                <button onClick={(e) => { e.stopPropagation(); handleDelete(); }}
                  className="text-xs text-red-600 hover:text-red-800 px-2 py-1 rounded hover:bg-red-50">
                  <Trash2 className="h-3 w-3 inline mr-0.5" />Eliminar
                </button>
              </>
            )}
            {showPaste ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
          </div>
        </button>

        {showPaste && (
          <>
            <p className="text-xs text-muted-foreground mb-3 mt-2">
              Pegá la tabla desde Excel. Formato: Día (tab) Mañana (tab) Tarde (tab) Noche
            </p>
            <textarea
              className="w-full h-32 border rounded-md p-3 text-xs font-mono"
              placeholder={`1\tResponsable\tResponsable\tResponsable\n2\t...`}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
            />
            <div className="flex gap-2 mt-3">
              <Button onClick={handleParse} disabled={!rawText.trim()}>
                <ClipboardPaste className="h-4 w-4 mr-1" /> Parsear
              </Button>
              <Button onClick={handleSave} disabled={!schedule || schedule.length === 0 || saving}>
                <Save className="h-4 w-4 mr-1" /> {saving ? "Guardando..." : "Guardar"}
              </Button>
            </div>
          </>
        )}
      </Card>

      {/* Schedule table */}
      {schedule && schedule.length > 0 && (
        <Card className="p-4 border-border bg-card shadow-none overflow-x-auto">
          <h3 className="font-display font-semibold text-foreground mb-4">Horario cargado ({schedule.length} días)</h3>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                <th className="px-2 py-1 text-left font-semibold text-foreground border-b">Día</th>
                <th className="px-2 py-1 text-left font-semibold text-foreground border-b">Mañana</th>
                <th className="px-2 py-1 text-left font-semibold text-foreground border-b">Tarde</th>
                <th className="px-2 py-1 text-left font-semibold text-foreground border-b">Noche</th>
              </tr>
            </thead>
            <tbody>
              {schedule.map((d) => (
                <tr key={d.dia}>
                  <td className="px-2 py-1 border-b font-medium">{d.dia}</td>
                  <td className="px-2 py-1 border-b">{d.manana || "-"}</td>
                  <td className="px-2 py-1 border-b">{d.tarde || "-"}</td>
                  <td className="px-2 py-1 border-b">{d.noche || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
