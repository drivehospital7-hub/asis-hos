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
import { AdvertenciasProcesar } from "@/components/procesar/AdvertenciasProcesar";
import type { ProcesarResultData } from "@/components/procesar/types";
import { useEnvioControl } from "@/hooks/useEnvioControl";
import { Toast } from "@/components/procesar/Toast";
import { norm } from "./utils";

interface ProcesarPageProps {
  can_write?: boolean;
  canControl?: boolean;
}

/** Campos del principal ofrecidos como anexo display-only (claves internas). */
const ANEXO_FIELDS = [
  { key: "responsable_cierra", label: "Responsable cierre" },
  { key: "entidad_cobrar", label: "Entidad" },
  { key: "entidad_afiliacion", label: "Entidad afiliación" },
  { key: "convenio_facturado", label: "Convenio" },
  { key: "tipo_usuario", label: "Tipo usuario" },
];

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export function ProcesarPage({
  can_write = false,
  canControl = false,
}: ProcesarPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fuente, setFuente] = useState("facturacion");
  const [filePrincipal, setFilePrincipal] = useState<File | null>(null);
  const [camposAnexo, setCamposAnexo] = useState<string[]>(["responsable_cierra"]);
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
    fd.append("fuente", fuente);
    if (fuente === "furips" && filePrincipal) {
      fd.append("file_principal", filePrincipal);
      fd.append("campos_anexo", JSON.stringify(camposAnexo));
    }

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
        <div className="flex items-end justify-between gap-4 mb-4">
          <h2 className="font-display font-semibold text-foreground mb-1">Subir archivo Excel</h2>
          <label className="text-xs text-muted-foreground flex items-center gap-2">
            Fuente
            <select
              value={fuente}
              onChange={(e) => setFuente(e.target.value)}
              className="rounded-md border border-border bg-card px-2 py-1.5 text-xs text-foreground"
            >
              <option value="facturacion">Facturación</option>
              <option value="furips">FURIPS</option>
            </select>
          </label>
        </div>
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

          {fuente === "furips" && (
            <div className="mb-4 rounded-md border border-border p-4">
              <p className="text-xs font-semibold text-foreground mb-1">
                Excel principal (opcional)
              </p>
              <p className="text-xs text-muted-foreground mb-2">
                Trae campos display-only por factura. No alimenta reglas.
              </p>
              <input
                type="file"
                accept=".xlsx,.xls,.xlsm"
                className="text-xs text-foreground/80 mb-3"
                onChange={(e) => setFilePrincipal(e.target.files?.[0] || null)}
              />
              {filePrincipal && (
                <div className="flex flex-wrap gap-3">
                  {ANEXO_FIELDS.map((f) => (
                    <label key={f.key} className="text-xs text-foreground/80 flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={camposAnexo.includes(f.key)}
                        onChange={(e) =>
                          setCamposAnexo((prev) =>
                            e.target.checked
                              ? [...prev, f.key]
                              : prev.filter((k) => k !== f.key),
                          )
                        }
                      />
                      {f.label}
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

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

      {/* Advertencias: reglas sin datos + valores no reconocidos */}
      {result && (
        <AdvertenciasProcesar
          advertenciasReglas={result.advertencias_reglas}
          valoresNoCatalogados={result.valores_no_catalogados}
        />
      )}

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
