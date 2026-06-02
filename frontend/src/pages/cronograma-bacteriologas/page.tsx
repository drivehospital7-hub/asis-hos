import { useState, useEffect, useCallback } from "react";
import { ClipboardPaste, Save, Trash2, CalendarClock, ChevronDown, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";

const BACTERIOLOGAS = [
  "KAREN", "VALENTINA", "KAROL", "LISBETH", "ALEJANDRA",
];

const NOMBRE_MAP: Record<string, string> = {
  KAREN: "MADROÑERO BURBANO KAREN LIZETH",
  VALENTINA: "MARIN ZULUAGA VALENTINA",
  KAROL: "MOLINA ALVAREZ KAROL DAYANNA",
  LISBETH: "PEÑA PEÑA LISBETH PAOLA",
  ALEJANDRA: "PABON GARCIA ALEJANDRA",
};

const now = new Date();
const currentMonth = now.getMonth() + 1;
const currentYear = now.getFullYear();
const currentDay = now.getDate();

function daysInMonth(m: number, y: number) {
  return new Date(y, m, 0).getDate();
}

const DAY_NAMES: Record<number, string> = {
  0: "D", 1: "L", 2: "M", 3: "M", 4: "J", 5: "V", 6: "S",
};

export function CronogramaPage() {
  const [mes] = useState(currentMonth);
  const [anio] = useState(currentYear);
  const [data, setData] = useState<Record<string, string>[]>([]);
  const [rawText, setRawText] = useState("");
  const [turnoHoy, setTurnoHoy] = useState<{ nombre: string; codigo: string }[]>([]);
  const [saving, setSaving] = useState(false);
  const [showPaste, setShowPaste] = useState(false);

  const totalDias = daysInMonth(mes, anio);

  const fetchCronograma = useCallback(async () => {
    try {
      const res = await fetch(`/cronograma-bacteriologas/api?mes=${mes}&anio=${anio}`);
      const json = await res.json();
      if (json.status === "success" && json.data?.dias) {
        const rows = BACTERIOLOGAS.map((nombre) => {
          const turnos: Record<string, string> = { nombre };
          json.data.dias.forEach((d: { dia: number; turnos: Record<string, string> }) => {
            turnos[String(d.dia)] = d.turnos?.[nombre] || "";
          });
          return turnos;
        });
        setData(rows);
      }
    } catch {
      // ignore
    }
  }, [mes, anio]);

  const fetchTurno = useCallback(async () => {
    try {
      const res = await fetch(`/cronograma-bacteriologas/api/turno?mes=${mes}&anio=${anio}&dia=${currentDay}`);
      const json = await res.json();
      if (json.status === "success") {
        setTurnoHoy(json.data?.en_turno || []);
      }
    } catch {
      // ignore
    }
  }, [mes, anio]);

  useEffect(() => { fetchCronograma(); fetchTurno(); }, [fetchCronograma, fetchTurno]);

  const handleParse = () => {
    const raw = rawText.trim();
    // Unir líneas que no empiezan con un nombre conocido (continuación de celda)
    const lines = raw.split("\n").reduce((acc, line) => {
      const trimmed = line.trim();
      if (!trimmed) return acc;
      const firstCol = trimmed.split("\t")[0]?.trim().toUpperCase() || "";
      if (BACTERIOLOGAS.some((b) => firstCol.startsWith(b)) || firstCol === "FECHA" || firstCol === "DIA") {
        acc.push(trimmed);
      } else if (acc.length > 0) {
        acc[acc.length - 1] += ` ${trimmed}`;
      }
      return acc;
    }, [] as string[]);

    if (lines.length < 3) return;

    // Obtener columnas del header: ["FECHA", "1", "2", "", "", "3", ...]
    const headerParts = lines[0].split("\t");
    // Mapa: posición → día (null si está vacío)
    const colMap: { pos: number; dia: number | null }[] = [];
    headerParts.forEach((h, idx) => {
      const d = parseInt(h.trim(), 10);
      colMap.push({ pos: idx, dia: isNaN(d) ? null : d });
    });

    const rows: Record<string, string>[] = [];
    for (let i = 2; i < lines.length; i++) {
      const parts = lines[i].split("\t");
      const nombreRaw = parts[0]?.trim().toUpperCase() || "";
      const bacterioMatch = BACTERIOLOGAS.find((b) => nombreRaw.startsWith(b));
      if (!bacterioMatch) continue;

      const row: Record<string, string> = { nombre: bacterioMatch };
      colMap.forEach((col) => {
        if (col.dia !== null && col.pos < parts.length) {
          row[String(col.dia)] = parts[col.pos]?.trim() || "";
        }
      });
      rows.push(row);
    }
    setData(rows);
  };

  const handleSave = async () => {
    setSaving(true);
    const dias = [];
    for (let d = 1; d <= totalDias; d++) {
      const turnos: Record<string, string> = {};
      data.forEach((row) => {
        turnos[row.nombre] = row[String(d)] || "";
      });
      dias.push({ dia: d, turnos });
    }
    try {
      await fetch("/cronograma-bacteriologas/api", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mes, anio, dias }),
      });
      setShowPaste(false);
      await fetchTurno();
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!await (window as any).__showConfirm?.("¿Eliminar el cronograma cargado?")) return;
    try {
      await fetch("/cronograma-bacteriologas/api", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mes, anio, dias: [] }),
      });
      setData([]);
      setRawText("");
      setTurnoHoy([]);
    } catch {
      // ignore
    }
  };

  const getCellColor = (val: string) => {
    const v = val.toUpperCase().trim();
    if (v === "L") return "bg-green-100 text-green-800";       // Libre
    if (v === "C") return "bg-purple-100 text-purple-800";     // Coordinadora
    if (v === "M") return "bg-teal-100 text-teal-800";         // Mañana
    if (v === "T") return "bg-orange-100 text-orange-800";     // Tarde
    if (v === "D") return "bg-yellow-100 text-yellow-800";     // Día
    if (v === "N") return "bg-blue-100 text-blue-800";         // Noche
    if (v.includes("CE") || v.includes("PYM")) return "bg-red-100 text-red-800 font-bold";
    return "";
  };

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Cronograma Bacteriólogas" }]} />
      <PageTitle
        eyebrow="Programación de Turnos"
        title="Cronograma Bacteriólogas"
        description="Gestión del cronograma mensual de bacteriólogas."
      />

      {/* Turno de hoy */}
      {turnoHoy.length > 0 && (
        <Card className="p-4 mb-6 border border-red-200 bg-red-50">
          <div className="flex items-center gap-2">
            <CalendarClock className="h-5 w-5 text-red-600" />
            <p className="text-sm font-semibold text-red-800">Hoy (día {currentDay}):</p>
            {turnoHoy.map((t) => (
              <span key={t.nombre} className="text-sm bg-red-200 text-red-900 px-2 py-0.5 rounded font-semibold">
                {NOMBRE_MAP[t.nombre] || t.nombre} ({t.codigo})
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Paste section - collapsible when data exists */}
      <Card className="p-6 mb-6">
        <button
          onClick={() => setShowPaste(!showPaste)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-2">
            <h3 className="font-display font-semibold text-foreground">Pegar cronograma desde Excel</h3>
            {data.length > 0 && (
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">Cargado</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {data.length > 0 && !showPaste && (
              <>
                <button
                  onClick={(e) => { e.stopPropagation(); setShowPaste(true); }}
                  className="text-xs text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50"
                >
                  Editar
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(); }}
                  className="text-xs text-red-600 hover:text-red-800 px-2 py-1 rounded hover:bg-red-50"
                >
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
              Copiá la tabla desde Excel y pegalá acá. La primera fila debe tener "FECHA" seguido de los días.
            </p>
            <textarea
              className="w-full h-32 border rounded-md p-3 text-xs font-mono"
              placeholder="Pegar acá el cronograma..."
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
            />
            <div className="flex gap-2 mt-3">
              <Button onClick={handleParse} disabled={!rawText.trim()}>
                <ClipboardPaste className="h-4 w-4 mr-1" /> Parsear
              </Button>
              <Button onClick={handleSave} disabled={data.length === 0 || saving}>
                <Save className="h-4 w-4 mr-1" /> {saving ? "Guardando..." : "Guardar"}
              </Button>
            </div>
          </>
        )}
      </Card>

      {/* Tabla del cronograma */}
      {data.length > 0 && (
        <Card className="p-4 border-border bg-card shadow-none overflow-x-auto">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display font-semibold text-foreground">
              {mes}/{anio}
            </h3>
          </div>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                <th className="sticky left-0 bg-white z-10 px-2 py-1 text-left font-semibold text-foreground border-b min-w-[120px]">
                  Bacterióloga
                </th>
                {Array.from({ length: totalDias }, (_, i) => i + 1).map((d) => (
                    <th
                      key={d}
                      className={`px-1 py-1 text-center font-medium border-b ${
                        d === currentDay ? "bg-red-50 text-red-800" : "text-muted-foreground"
                      }`}
                  >
                    <div>{d}</div>
                    <div className="text-[10px]">{DAY_NAMES[new Date(anio, mes - 1, d).getDay()]}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.nombre}>
                  <td className="sticky left-0 bg-white z-10 px-2 py-1 text-xs font-medium text-foreground border-b whitespace-nowrap">
                    {NOMBRE_MAP[row.nombre] || row.nombre}
                  </td>
                  {Array.from({ length: totalDias }, (_, i) => i + 1).map((d) => {
                    const val = row[String(d)] || "";
                    return (
                      <td
                        key={d}
                        className={`px-1 py-1 text-center border-b ${getCellColor(val)} ${
                          d === currentDay ? "border-l-2 border-l-red-500" : ""
                        }`}
                      >
                        {val || "-"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Leyenda */}
          <div className="flex gap-4 mt-4 text-xs text-muted-foreground flex-wrap">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-purple-100 inline-block"></span> C=Coordinadora</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-100 inline-block"></span> CE=Consulta Externa</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-100 inline-block"></span> PYM=Apoyo PyM</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-100 inline-block"></span> D=Turno Día</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-blue-100 inline-block"></span> N=Turno Noche</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-teal-100 inline-block"></span> M=Turno Mañana</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-100 inline-block"></span> T=Turno Tarde</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-100 inline-block"></span> L=Libre</span>
          </div>
        </Card>
      )}
    </div>
  );
}
