import { useState, useRef } from "react";
import {
  Upload,
  AlertTriangle,
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
}

interface Discrepancia {
  numero_factura: string;
  nombre_completo: string;
  primer_nombre: string;
  segundo_nombre?: string;
  sexo_excel: string;
  sexo_api: string;
  nombre_normalizado: string;
}

interface FacturasResponse {
  status: string;
  data?: {
    registros: Array<{
      numero_factura: string;
      nombre_completo: string;
      primer_nombre: string;
      segundo_nombre?: string;
      sexo: string;
      nombre_normalizado: string;
    }>;
    total: number;
  };
  errors?: string[];
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
  const [extractedData, setExtractedData] = useState<FacturasResponse["data"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [, setActiveTab] = useState<"extract" | "verify">("extract");
  const dropRef = useRef<HTMLDivElement>(null);

  const selectFile = (f: File) => {
    setFile(f);
    setResult(null);
    setExtractedData(null);
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
  };

  const extractData = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setExtractedData(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/import/facturas-nombres", { method: "POST", body: formData });
      const data: FacturasResponse = await res.json();
      if (data.status === "success" && data.data) {
        setExtractedData(data.data);
        setActiveTab("extract");
      } else {
        setError(data.errors?.join(", ") || "Error al extraer datos");
      }
    } catch (err) {
      setError("Error de conexión: " + (err as Error).message);
    } finally {
      setLoading(false);
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
        setActiveTab("verify");
      } else {
        setError(data.errors?.join(", ") || "Error al verificar");
      }
    } catch (err) {
      setError("Error de conexión: " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const corrigeGenero = async (nombreNormalizado: string, sexoExcel: string) => {
    try {
      const res = await fetch("/api/import/cache-corregir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre_normalizado: nombreNormalizado, genero: sexoExcel }),
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

  const exportExcel = () => {
    if (!extractedData?.registros) return;
    const headers = ["Numero Factura", "Primer Nombre", "Segundo Nombre", "Nombre Completo", "Sexo"];
    const rows = extractedData.registros.map((r) => [
      r.numero_factura, r.primer_nombre, r.segundo_nombre || "", r.nombre_completo, r.sexo,
    ]);
    const text = [headers.join("\t"), ...rows.map((r) => r.join("\t"))].join("\n");
    navigator.clipboard.writeText(text).then(() => {
      Modal.toast("✓ Datos copiados al portapapeles. Puedes pegarlos en Excel.");
    });
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold font-heading tracking-tight mb-1"
              style={{ color: "oklch(0.15 0.02 160)" }}>
            Verificar Sexo — Genderize
          </h1>
          <p className="text-sm" style={{ color: "oklch(0.55 0.04 160)" }}>
            Sube el Excel de facturas para verificar el sexo contra la API Genderize
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
              onChange={(e) => e.target.files?.[0] && selectFile(e.target.files[0])}
            />
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <Button onClick={extractData} disabled={!file || loading} variant="secondary">
              Extraer datos
            </Button>
            <Button onClick={verifyData} disabled={!file || loading}
                    className="bg-success hover:bg-success/90 text-white">
              Verificar y Comparar
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

        {/* Stats (from verify) */}
        {result?.stats && (
          <Card className="p-6 border shadow-none mb-6"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
            <h3 className="text-sm font-semibold mb-3" style={{ color: "oklch(0.15 0.02 160)" }}>
              Estadísticas
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
                <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>API calls</p>
              </div>
            </div>
          </Card>
        )}

        {/* Discrepancies */}
        {result?.discrepancies && result.discrepancies.length > 0 && (
          <Card className="p-6 border shadow-none"
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
                    <th className="py-3 px-4 text-left">Número Factura</th>
                    <th className="py-3 px-4 text-left">Nombre Completo</th>
                    <th className="py-3 px-4 text-left">Nombres Evaluados</th>
                    <th className="py-3 px-4 text-left">Sexo Excel</th>
                    <th className="py-3 px-4 text-left">Sexo API</th>
                    <th className="py-3 px-4 text-left">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {result.discrepancies.map((d, i) => (
                    <tr key={i} className="border-b"
                        style={{ background: "oklch(0.45 0.18 25 / 0.08)", borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                      <td className="py-3 px-4 font-mono text-xs">{d.numero_factura}</td>
                      <td className="py-3 px-4 font-medium text-xs">{d.nombre_completo}</td>
                      <td className="py-3 px-4 text-xs">
                        <span className="inline-block bg-gray-100 rounded px-1.5 py-0.5 text-xs">{d.primer_nombre}</span>
                        {d.segundo_nombre && (
                          <><span className="mx-1" style={{ color: "oklch(0.55 0.04 160)" }}>+</span>
                            <span className="inline-block bg-gray-100 rounded px-1.5 py-0.5 text-xs">{d.segundo_nombre}</span></>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs">{d.sexo_excel}</td>
                      <td className="py-3 px-4 text-xs">{d.sexo_api}</td>
                      <td className="py-3 px-4">
                        <Button size="sm" variant="outline"
                                onClick={() => corrigeGenero(d.nombre_normalizado, d.sexo_excel)}>
                          Corregir → {d.sexo_excel}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Extracted data table */}
        {extractedData?.registros && extractedData.registros.length > 0 && (
          <Card className="p-6 border shadow-none"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold" style={{ color: "oklch(0.15 0.02 160)" }}>
                Datos extraídos ({extractedData.total} registros)
              </h3>
              <Button size="sm" variant="secondary" onClick={exportExcel}>
                <Download className="h-3.5 w-3.5" />
                Exportar
              </Button>
            </div>
            <div className="overflow-x-auto rounded-lg border"
                 style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: "oklch(0.55 0.04 160)" }}>
                    <th className="py-3 px-4 text-left">Número Factura</th>
                    <th className="py-3 px-4 text-left">Nombre Completo</th>
                    <th className="py-3 px-4 text-left">Primer Nombre</th>
                    <th className="py-3 px-4 text-left">Sexo</th>
                  </tr>
                </thead>
                <tbody>
                  {extractedData.registros.slice(0, 50).map((r, i) => (
                    <tr key={i} className="border-b hover:bg-gray-50 transition-colors"
                        style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                      <td className="py-3 px-4 font-mono text-xs">{r.numero_factura}</td>
                      <td className="py-3 px-4 text-xs">{r.nombre_completo}</td>
                      <td className="py-3 px-4 text-xs">{r.primer_nombre}</td>
                      <td className="py-3 px-4">
                        <StatusBadge tone={r.sexo === "M" ? "info" : "success"}>{r.sexo}</StatusBadge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {extractedData.total > 50 && (
              <p className="text-xs mt-2" style={{ color: "oklch(0.55 0.04 160)" }}>
                Mostrando 50 de {extractedData.total} registros
              </p>
            )}
          </Card>
        )}
    </div>
  );
}
