import { useState, useRef } from "react";
import {
  Upload,
  AlertTriangle,
  Eye,
  Download,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";

interface StatsData {
  total_excel: number;
  nombres_unicos: number;
  cache_hits: number;
  api_calls_necesarias: number;
  nombres_no_cache: { nombre: string; sexo: string }[];
}

interface Discrepancia {
  numero_factura: string;
  numero_identificacion: string;
  entidad_cobrar: string;
  tipo_identificacion: string;
  nombre_completo: string;
  primer_nombre: string;
  segundo_nombre?: string;
  sexo_excel: string;
  sexo_api: string;
  nombre_normalizado: string;
}

interface VerifyResponse {
  status: string;
  data?: {
    stats: StatsData;
    discrepancies: Discrepancia[];
    total_discrepancies: number;
  };
  errors?: string[];
}

export function GenderizePage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerifyResponse["data"] | null>(null);
  const [error, setError] = useState<string | null>(null);

  /** Preview de stats SIN gastar tokens */
  const [statsPreview, setStatsPreview] = useState<StatsData | null>(null);
  const [previewing, setPreviewing] = useState(false);

  const dropRef = useRef<HTMLDivElement>(null);

  const selectFile = (f: File) => {
    setFile(f);
    setResult(null);
    setStatsPreview(null);
    setError(null);
  };

  // Auto-generar preview al seleccionar archivo
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      selectFile(f);
      fetchStatsPreview(f);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) {
      selectFile(f);
      fetchStatsPreview(f);
    }
  };

  /** Preview de stats SIN gastar tokens */
  const fetchStatsPreview = async (f?: File) => {
    const targetFile = f || file;
    if (!targetFile) return;
    setPreviewing(true);
    setStatsPreview(null);

    const formData = new FormData();
    formData.append("file", targetFile);

    try {
      const res = await fetch("/api/import/facturas-stats", { method: "POST", body: formData });
      const data = await res.json();
      if (data.status === "success" && data.data) {
        setStatsPreview(data.data);
        setError(null);
      } else if (data.errors?.length) {
        setError(data.errors.join(", "));
      }
    } catch (err) {
      setError("Error de conexión: " + (err as Error).message);
    } finally {
      setPreviewing(false);
    }
  };

  const verifyData = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/import/facturas-verify", { method: "POST", body: formData });
      const data: VerifyResponse = await res.json();
      if (data.status === "success" && data.data) {
        setResult(data.data);
      } else {
        setError(data.errors?.join(", ") || "Error al verificar");
      }
    } catch (err) {
      setError("Error de conexión: " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  /** Exportar nombres no cacheados como .txt con formato nombre\\tsexo */
  const exportNoCache = () => {
    const items = statsPreview?.nombres_no_cache ?? [];
    const text = "\uFEFF" + items.map(i => `${i.nombre}\t${i.sexo}`).join(", ");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "nombres_no_cache.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  /** Per-row selected gender for dropdown */
  const [selectedGenders, setSelectedGenders] = useState<Record<string, string>>({});

  const handleGenderChange = (nombreNormalizado: string, value: string) => {
    setSelectedGenders((prev) => ({ ...prev, [nombreNormalizado]: value }));
  };

  const corrigeGenero = async (nombreNormalizado: string, genero: string) => {
    try {
      const res = await fetch("/api/import/cache-corregir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre_normalizado: nombreNormalizado, genero }),
      });
      const data = await res.json();
      if (data.status === "success") {
        // Refresh verify results
        verifyData();
      }
    } catch {
      // Silently handle error
    }
  };

  const GENDER_OPTIONS = ["F", "M", "L", "U"] as const;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold font-heading tracking-tight mb-1"
              style={{ color: "oklch(0.15 0.02 160)" }}>
            Verificar Sexo — Genderize
          </h1>
          <p className="text-sm" style={{ color: "oklch(0.55 0.04 160)" }}>
            Sube el Excel de facturas para verificar el sexo
          </p>
        </div>

        {/* Upload card */}
        <Card className="p-6 border mb-6 shadow-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
          {/* Drop zone */}
          <div
            ref={dropRef}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => document.getElementById("fileInput")?.click()}
            className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 mb-4 hover:border-primary hover:bg-primary/5"
            style={{ borderColor: file ? "oklch(0.25 0.06 160)" : "oklch(0.55 0.04 160 / 0.3)" }}
          >
            <div className="flex flex-col items-center gap-2">
              <Upload className="h-10 w-10" style={{ color: file ? "oklch(0.25 0.06 160)" : "oklch(0.55 0.04 160)" }} />
              <p className="text-sm font-medium" style={{ color: file ? "oklch(0.15 0.02 160)" : "oklch(0.55 0.04 160)" }}>
                {file ? file.name : "Arrastrá tu archivo Excel aquí o haz clic para seleccionar"}
              </p>
              <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>.xlsx, .xls</p>
            </div>
            <input
              id="fileInput"
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
               onChange={handleFileChange}
            />
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <Button onClick={() => fetchStatsPreview()}
                    disabled={!file || loading || previewing}
                    variant="outline"
                    className="flex items-center gap-1.5">
              <Eye className="h-4 w-4" />
              {previewing ? "Calculando..." : "Ver estimación"}
            </Button>
            <Button onClick={verifyData}
                    disabled={!file || loading}
                    className="bg-success hover:bg-success/90 text-white">
              Verificar
            </Button>
          </div>
        </Card>

        {/* Error */}
        {error && (
          <Card className="p-4 border-danger/30 shadow-none mb-6"
            style={{ background: "oklch(0.45 0.18 25 / 0.08)", borderColor: "oklch(0.45 0.18 25 / 0.3)" }}>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" style={{ color: "oklch(0.45 0.18 25)" }} />
              <p className="text-sm font-medium" style={{ color: "oklch(0.45 0.18 25)" }}>{error}</p>
            </div>
          </Card>
        )}

        {/* Loading */}
        {loading && (
          <Card className="p-4 border shadow-none mb-6"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
            <p className="text-sm text-center" style={{ color: "oklch(0.55 0.04 160)" }}>
              Procesando...
            </p>
          </Card>
        )}

        {/* Stats preview (sin gastar tokens) */}
        {statsPreview && !result && (
          <Card className="p-6 border shadow-none mb-6"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"
                style={{ color: "oklch(0.15 0.02 160)" }}>
              <Eye className="h-4 w-4" />
              Estimación
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="font-semibold text-sm">{statsPreview.total_excel}</p>
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>Registros en Excel</p>
              </div>
              <div>
                <p className="font-semibold text-sm">{statsPreview.nombres_unicos}</p>
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>Nombres únicos</p>
              </div>
              <div>
                <p className="font-semibold text-sm">{statsPreview.cache_hits}</p>
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>En cache</p>
              </div>
              <div>
                <p className="font-semibold text-lg"
                    style={{ color: statsPreview.api_calls_necesarias > 0 ? "oklch(0.45 0.18 25)" : "oklch(0.25 0.06 160)" }}>
                  {statsPreview.api_calls_necesarias}
                </p>
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>No procesados</p>
              </div>
            </div>
            {statsPreview.api_calls_necesarias === 0 && (
              <p className="text-xs mt-2" style={{ color: "oklch(0.25 0.06 160)" }}>
                ✅ Todos los nombres serán procesados (están en cache).
              </p>
            )}

            {statsPreview.nombres_no_cache && statsPreview.nombres_no_cache.length > 0 && (
              <Button onClick={exportNoCache}
                      variant="outline"
                      className="flex items-center gap-1.5 mt-3">
                <Download className="h-4 w-4" />
                Exportar no-cache
              </Button>
            )}
          </Card>
        )}

        {/* Stats (from verify) */}
        {result?.stats && (
          <Card className="p-6 border shadow-none mb-6"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
            <h3 className="text-sm font-semibold mb-3" style={{ color: "oklch(0.15 0.02 160)" }}>
              Resultado de verificación
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="font-semibold text-sm">{result.stats.total_excel}</p>
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>Total Excel</p>
              </div>
              <div>
                <p className="font-semibold text-sm">{result.stats.nombres_unicos}</p>
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>Nombres únicos</p>
              </div>
              <div>
                <p className="font-semibold text-sm">{result.stats.cache_hits}</p>
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>En cache</p>
              </div>
              <div>
                <p className="font-semibold text-sm">{result.stats.api_calls_necesarias}</p>
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>No procesados</p>
              </div>
            </div>
          </Card>
        )}

        {/* Discrepancies — o todo ok */}
        {result?.discrepancies !== undefined && (
          result.discrepancies.length > 0 ? (
            <Card className="p-6 border shadow-none mb-6"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
              <p className="mb-3 font-semibold text-sm">
                Discrepancias encontradas:{" "}
                <StatusBadge tone="danger">{result.total_discrepancies}</StatusBadge>
              </p>
              <div className="overflow-x-auto rounded-lg border"
                   style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider"
                        style={{ color: "oklch(0.55 0.04 160)" }}>
                      <th className="py-3 px-4 text-left">Nº Factura</th>
                      <th className="py-3 px-4 text-left">Nº Identificación</th>
                      <th className="py-3 px-4 text-left">Entidad Cobrar</th>
                      <th className="py-3 px-4 text-left">Tipo Identificación</th>
                      <th className="py-3 px-4 text-left">Nombre Completo</th>
                      <th className="py-3 px-4 text-left">Sexo Excel</th>
                      <th className="py-3 px-4 text-left">Sexo JSON</th>
                      <th className="py-3 px-4 text-left">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.discrepancies.map((d, i) => (
                      <tr key={i} className="border-b"
                          style={{ background: "oklch(0.45 0.18 25 / 0.08)", borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                        <td className="py-3 px-4 font-mono text-xs">{d.numero_factura}</td>
                        <td className="py-3 px-4 font-mono text-xs">{d.numero_identificacion}</td>
                        <td className="py-3 px-4 font-mono text-xs">{d.entidad_cobrar}</td>
                        <td className="py-3 px-4 font-mono text-xs">{d.tipo_identificacion}</td>
                        <td className="py-3 px-4 font-medium text-xs">{d.nombre_completo}</td>
                        <td className="py-3 px-4 text-xs">{d.sexo_excel}</td>
                        <td className="py-3 px-4 text-xs">{d.sexo_api}</td>
                        <td className="py-3 px-4 flex gap-1.5 items-center">
                          <select
                            value={selectedGenders[d.nombre_normalizado] ?? d.sexo_excel}
                            onChange={(e) => handleGenderChange(d.nombre_normalizado, e.target.value)}
                            className="h-7 rounded border border-input bg-transparent px-2 text-xs font-medium transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                          >
                            {GENDER_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                          <Button size="sm" variant="outline"
                                  onClick={() => corrigeGenero(d.nombre_normalizado, selectedGenders[d.nombre_normalizado] ?? d.sexo_excel)}
                                  className="h-7 text-xs px-2 shrink-0">
                            Aplicar
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : (
            <Card className="p-6 border shadow-none mb-6"
              style={{ borderColor: "oklch(0.45 0.18 145 / 0.2)", background: "oklch(0.45 0.18 145 / 0.06)" }}>
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full flex items-center justify-center"
                     style={{ background: "oklch(0.45 0.18 145 / 0.15)" }}>
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none"
                       style={{ color: "oklch(0.35 0.15 145)" }}>
                    <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5"
                          strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-sm" style={{ color: "oklch(0.25 0.12 145)" }}>
                    Todos los datos coinciden
                  </p>
                  <p className="text-xs" style={{ color: "oklch(0.45 0.12 145)" }}>
                    No hay discrepancias entre el Excel y la API
                  </p>
                </div>
              </div>
            </Card>
          )
        )}


    </div>
  );
}
