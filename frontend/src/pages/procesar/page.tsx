import { useState, useRef, useCallback } from "react";
import {
  Upload,
  Info,
  FileSpreadsheet,
  ArrowRight,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { ResultadosProcesar } from "@/components/procesar/ResultadosProcesar";
import type { ProcesarResultData } from "@/components/procesar/types";
import { useEnvioControl } from "@/hooks/useEnvioControl";
import { Toast } from "@/components/procesar/Toast";
import { norm } from "./utils";

interface ProcesarPageProps {
  can_write?: boolean;
  canControl?: boolean;
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
  const [result, setResult] = useState<ProcesarResultData | null>(null);
  const [error, setError] = useState("");
  const [exportId, setExportId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // ── Envío a Control (hook compartido con el simulador) ──
  const markEnviada = useCallback((factura: string) => {
    setResult((prev) =>
      prev
        ? {
            ...prev,
            errores: prev.errores.map((fg) => ({
              ...fg,
              tipos: fg.tipos.map((tg) => ({
                ...tg,
                facturas: tg.facturas.map((x) =>
                  norm(x.factura) === norm(factura)
                    ? { ...x, _enviada: true }
                    : x,
                ),
              })),
            })),
          }
        : prev,
    );
  }, []);

  const {
    showEnvio,
    envioExistentes,
    envioEnviadas,
    envioVersion,
    toastMessage,
    setToastMessage,
    handleSendToControl,
  } = useEnvioControl({ can_write, canControl, onEnviada: markEnviada });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError("");
    setResult(null);
    setExportId(null);

    const fd = new FormData();
    fd.append("file_upload", file);

    try {
      const res = await fetch("/procesar/", { method: "POST", body: fd });
      const json = await res.json();

      if (json.status === "error") {
        setError(json.errors?.[0] || "Error al procesar el archivo");
      } else {
        setResult(json.data);
        setExportId(json.data?.export_id ?? null);
      }
    } catch {
      setError("Error de conexión con el servidor");
    } finally {
      setLoading(false);
    }
  };

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

      {/* Resultados (componente compartido con el simulador) */}
      {result && (
        <ResultadosProcesar
          errores={result.errores}
          totalErrores={result.total_errores}
          exportHref={exportId ? `/procesar/export?id=${exportId}` : null}
          showEnvio={showEnvio}
          envioExistentes={envioExistentes}
          envioEnviadas={envioEnviadas}
          envioVersion={envioVersion}
          onSendToControl={handleSendToControl}
        />
      )}
    </div>
  );
}
