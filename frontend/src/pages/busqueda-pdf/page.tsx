import { useEffect, useState, useCallback } from "react";
import {
  FileText,
  Search,
  Loader2,
  Plus,
  X,
  Play,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/status-badge";
import { PageTitle } from "@/components/page-title";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface TerminoResult {
  termino: string;
  tipo: string;
  contexto: string;
}

interface ResultadoItem {
  pdf: string;
  ruta_completa: string;
  terminos: TerminoResult[];
}

interface ResumenData {
  pdfs_procesados: number;
  pdfs_con_hallazgos: number;
  pdfs_sin_texto: number;
  pdfs_error: number;
}

interface BuscarData {
  resultados: ResultadoItem[];
  resumen: ResumenData;
  errores: string[];
}

interface BuscarResponse {
  status: string;
  data: BuscarData;
  errors: string[];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const CONDICIONES = [
  "Conductor", "Ciclista", "Peatón", "Ocupante",
];

const TRANSPORTES = [
  "Automóvil", "Bus", "Buseta", "Camión", "Camioneta",
  "Campero", "Microbus", "Tractocamion", "Motocicleta",
  "Motocarro", "Mototriciclo", "Cuatrimoto",
  "Moto extranjera", "Vehiculo extranjero", "Volqueta",
  "No aplica",
];

/* ------------------------------------------------------------------ */
/*  SynonymsInput                                                     */
/* ------------------------------------------------------------------ */

function SynonymsInput({
  synonyms,
  onChange,
}: {
  synonyms: Record<string, string[]>;
  onChange: (s: Record<string, string[]>) => void;
}) {
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");

  const handleAdd = () => {
    if (!key.trim() || !value.trim()) return;
    const existing = synonyms[key.trim()] ?? [];
    onChange({ ...synonyms, [key.trim()]: [...existing, value.trim()] });
    setValue("");
  };

  const handleRemove = (k: string, idx: number) => {
    const updated = { ...synonyms };
    const arr = updated[k].filter((_, i) => i !== idx);
    if (arr.length === 0) {
      delete updated[k];
    } else {
      updated[k] = arr;
    }
    onChange(updated);
  };

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">Sinónimos personalizados</p>
      <div className="flex gap-2">
        <Input
          placeholder="Condición/Transporte (ej: Ocupante)"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          className="flex-1"
        />
        <Input
          placeholder="Sinónimo"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="flex-1"
        />
        <Button variant="outline" size="sm" onClick={handleAdd} type="button">
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      {Object.entries(synonyms).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(synonyms).map(([k, vals]) =>
            vals.map((v, i) => (
              <span
                key={`${k}-${i}`}
                className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground"
              >
                {k}: {v}
                <button
                  type="button"
                  onClick={() => handleRemove(k, i)}
                  className="ml-0.5 rounded-full p-0.5 hover:bg-muted"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )),
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ResultsTable                                                      */
/* ------------------------------------------------------------------ */

function ResultsTable({ resultados }: { resultados: ResultadoItem[] }) {
  if (resultados.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No se encontraron resultados.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="pb-2 pr-4 font-medium">PDF</th>
            <th className="pb-2 pr-4 font-medium">Término</th>
            <th className="pb-2 pr-4 font-medium">Tipo</th>
            <th className="pb-2 font-medium">Contexto</th>
          </tr>
        </thead>
        <tbody>
          {resultados.map((r) =>
            r.terminos.map((t, i) => (
              <tr key={`${r.pdf}-${i}`} className="border-b last:border-0">
                {i === 0 && (
                  <td
                    className="py-2 pr-4 align-top font-medium"
                    rowSpan={r.terminos.length}
                  >
                    {r.pdf}
                  </td>
                )}
                <td className="py-2 pr-4">
                  <StatusBadge tone={t.tipo === "condicion" ? "info" : "primary"}>
                    {t.termino}
                  </StatusBadge>
                </td>
                <td className="py-2 pr-4 text-muted-foreground">{t.tipo}</td>
                <td className="py-2 max-w-xs truncate text-muted-foreground" title={t.contexto}>
                  {t.contexto}
                </td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page Component                                               */
/* ------------------------------------------------------------------ */

export function BusquedaPdfPage() {
  /* ---- state ---- */
  const [ruta, setRuta] = useState("");
  const [condicion, setCondicion] = useState("");
  const [transporte, setTransporte] = useState("");
  const [synonyms, setSynonyms] = useState<Record<string, string[]>>({});
  const setSynonymsLoaded = useState(false)[1];
  const [searchLoading, setSearchLoading] = useState(false);
  const [resultados, setResultados] = useState<ResultadoItem[]>([]);
  const [resumen, setResumen] = useState<ResumenData | null>(null);
  const [searchErrors, setSearchErrors] = useState<string[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  /* ---- search ---- */
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruta.trim() || !condicion || !transporte) return;

    setSearchLoading(true);
    setSearchError(null);
    setSearchErrors([]);
    setResultados([]);
    setResumen(null);

    try {
      const body: Record<string, unknown> = {
        ruta: ruta.trim(),
        condicion,
        transporte,
      };
      if (Object.keys(synonyms).length > 0) {
        body.sinonimos = synonyms;
      }

      const res = await fetch("/busqueda-pdf/buscar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json: BuscarResponse = await res.json();

      if (json.status === "success") {
        setResultados(json.data.resultados);
        setResumen(json.data.resumen);
        setSearchErrors(json.data.errores || []);
      } else {
        setSearchError(json.errors?.join(", ") || "Error al buscar");
      }
    } catch (err) {
      setSearchError("Error de conexión: " + (err as Error).message);
    } finally {
      setSearchLoading(false);
    }
  };

  /* ---- load persisted synonyms on mount ---- */
  useEffect(() => {
    fetch("/busqueda-pdf/sinonimos")
      .then((r) => r.json())
      .then((json) => {
        if (json.status === "success" && json.data?.sinonimos) {
          setSynonyms(json.data.sinonimos);
        }
      })
      .catch(() => {
        // Silently fail — synonyms default to empty
      })
      .finally(() => setSynonymsLoaded(true));
  }, []);

  /* ---- auto-save synonyms when they change ---- */
  const saveSynonyms = useCallback(async (s: Record<string, string[]>) => {
    try {
      await fetch("/busqueda-pdf/sinonimos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sinonimos: s }),
      });
    } catch {
      // Silently fail — will retry on next change
    }
  }, []);

  const handleSynonymsChange = useCallback((s: Record<string, string[]>) => {
    setSynonyms(s);
    saveSynonyms(s);
  }, [saveSynonyms]);

  return (
    <div className="space-y-6">
      <PageTitle
        eyebrow="Búsqueda PDF"
        title="Búsqueda de términos en PDFs"
        description="Ingresá la ruta de la carpeta, elegí Condición y Transporte para buscar términos relacionados no seleccionados."
      />

      {/* Input & Search Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-4 w-4" />
            Parámetros de búsqueda
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="space-y-4">
            {/* Ruta */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Ruta de la carpeta</label>
              <Input
                value={ruta}
                onChange={(e) => setRuta(e.target.value)}
                placeholder="D:\Carpeta\con\PDFs"
                required
              />
            </div>

            {/* Condición y Transporte */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Condición</label>
                <select
                  value={condicion}
                  onChange={(e) => setCondicion(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
                >
                  <option value="">Seleccionar condición</option>
                  {CONDICIONES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Transporte</label>
                <select
                  value={transporte}
                  onChange={(e) => setTransporte(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
                >
                  <option value="">Seleccionar transporte</option>
                  {TRANSPORTES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
            </div>

            <SynonymsInput synonyms={synonyms} onChange={handleSynonymsChange} />

            {searchError && (
              <p className="text-sm text-destructive">{searchError}</p>
            )}

            <div className="flex justify-end">
              <Button type="submit" disabled={!ruta.trim() || !condicion || !transporte || searchLoading}>
                {searchLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Buscando…
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    Buscar
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Results Card */}
      {resumen && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Resultados
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Summary */}
            <div className="flex flex-wrap gap-3">
              <StatusBadge tone="info">
                Procesados: {resumen.pdfs_procesados}
              </StatusBadge>
              <StatusBadge tone="success">
                Con hallazgos: {resumen.pdfs_con_hallazgos}
              </StatusBadge>
              {resumen.pdfs_sin_texto > 0 && (
                <StatusBadge tone="warning">
                  Sin texto: {resumen.pdfs_sin_texto}
                </StatusBadge>
              )}
              {resumen.pdfs_error > 0 && (
                <StatusBadge tone="danger">
                  Errores: {resumen.pdfs_error}
                </StatusBadge>
              )}
            </div>

            {searchErrors.length > 0 && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm space-y-1">
                <p className="font-medium text-destructive">Detalle de errores:</p>
                {searchErrors.map((e, i) => (
                  <p key={i} className="text-muted-foreground">• {e}</p>
                ))}
              </div>
            )}

            <ResultsTable resultados={resultados} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
