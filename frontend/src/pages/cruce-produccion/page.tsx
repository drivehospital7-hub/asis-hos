import { useState } from "react";
import {
  Upload,
  Info,
  FileSpreadsheet,
  ArrowRight,
  FileDown,
  Search,
  FolderOpen,
  AlertTriangle,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";

interface Faltante {
  codigo: string;
  numero_factura_original: string;
  responsable: string;
  fec_factura: string | null;
  estado_novedad: string | null;
  facturador: string;
}

interface RevisarRow {
  numero_factura_original: string;
  responsable: string;
  fec_factura: string | null;
  facturador: string;
}

interface Desactualizado {
  codigo: string;
  facturador: string;
  full_path: string;
  mtime_carpeta: string | null;
  estado_novedad: string;
  motivo: string;
  fecha_estado: string | null;
}

interface CruceResumen {
  total_produccion: number;
  total_carpetas: number;
  total_faltantes: number;
  total_revisar: number;
  total_desactualizados: number;
}

interface CruceResult {
  faltantes: Faltante[];
  revisar: RevisarRow[];
  desactualizados: Desactualizado[];
  resumen: CruceResumen;
  export_id?: string | null;
  scanned_roots: string[];
  last_scan_at?: string | null;
}

// Header XHR: el decorador de permisos hace redirect al login en POST
// sin X-Requested-With; con el header devuelve 403 JSON.
const XHR_HEADERS = { "X-Requested-With": "XMLHttpRequest" };

function formatScanDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

export function CruceProduccionPage({ can_write = false }: { can_write?: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CruceResult | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError("");
    setResult(null);

    const fd = new FormData();
    fd.append("file_upload", file);

    try {
      const res = await fetch("/cruce-produccion/cruce", {
        method: "POST",
        headers: XHR_HEADERS,
        body: fd,
      });
      const json = await res.json();

      if (json.status === "error") {
        setError(json.errors?.[0] || "Error al cruzar el archivo");
      } else {
        setResult(json.data as CruceResult);
      }
    } catch {
      setError("Error de conexión con el servidor");
    } finally {
      setLoading(false);
    }
  };

  const filteredFaltantes =
    result?.faltantes.filter((f) => {
      if (!filter.trim()) return true;
      const q = filter.trim().toLowerCase();
      return (
        f.codigo.toLowerCase().includes(q) ||
        f.responsable.toLowerCase().includes(q) ||
        f.facturador.toLowerCase().includes(q)
      );
    }) ?? [];
  const filteredDesactualizados =
    result?.desactualizados?.filter((d) => {
      if (!filter.trim()) return true;
      const q = filter.trim().toLowerCase();
      return (
        d.codigo.toLowerCase().includes(q) ||
        d.facturador.toLowerCase().includes(q) ||
        d.motivo.toLowerCase().includes(q)
      );
    }) ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Cruce Producción" }]} />
      <PageTitle
        eyebrow="EPS MALLAMAS"
        title="Cruce Producción vs Carpetas"
        description="Cargá el reporte de producción en Excel. El sistema cruza cada factura contra las carpetas de red y lista las faltantes con su responsable."
      />

      {/* Upload card (igual a procesar) */}
      {can_write ? (
        <Card className="p-6 border-border bg-card shadow-none mb-6">
          <h2 className="font-display font-semibold text-foreground mb-1">Subir archivo Excel</h2>
          <p className="text-xs text-muted-foreground mb-4">
            Formatos aceptados: .xlsx, .xls, .xlsm
          </p>

          <form onSubmit={handleSubmit}>
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
                  El archivo debe incluir las columnas Número Factura, Responsable Cierra Facturar y Fec. Factura.
                  El cruce escanea las carpetas de red en el momento y puede tardar unos segundos.
                </p>
              </div>
            </div>

            <div className="mt-5 flex justify-end">
              <Button
                className="bg-primary hover:bg-primary/90 text-primary-foreground"
                disabled={loading || !file}
                onClick={handleSubmit}
              >
                {loading ? "Cruzando…" : "Cruzar"}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </Button>
            </div>
          </form>
        </Card>
      ) : (
        <Card className="p-4 border-border bg-card shadow-none mb-6">
          <p className="text-xs text-muted-foreground">
            Solo lectura: no tenés permiso para subir archivos y cruzar. Pedí acceso de escritura si lo necesitás.
          </p>
        </Card>
      )}

      {/* Resultados */}
      {result && (
        <>
          {/* Resumen */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Producción
              </p>
              <p className="text-2xl font-display font-bold text-foreground mt-1">
                {result.resumen.total_produccion}
              </p>
            </Card>
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Con carpeta
              </p>
              <p className="text-2xl font-display font-bold text-foreground mt-1">
                {result.resumen.total_carpetas}
              </p>
            </Card>
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Faltantes
              </p>
              <p className="text-2xl font-display font-bold text-danger mt-1">
                {result.resumen.total_faltantes}
              </p>
            </Card>
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Revisar
              </p>
              <p className="text-2xl font-display font-bold text-warning-foreground mt-1">
                {result.resumen.total_revisar}
              </p>
            </Card>
            <Card className="p-4 border-border bg-card shadow-none">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Soportes desactualizados
              </p>
              <p className="text-2xl font-display font-bold text-warning-foreground mt-1">
                {result.resumen.total_desactualizados}
              </p>
            </Card>
          </div>

          {/* Scan info */}
          <Card className="p-4 border-border bg-card shadow-none mb-4">
            <div className="flex items-center gap-2 mb-1">
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs font-semibold text-foreground">
                Rutas escaneadas ({result.scanned_roots.length}) · Último escaneo:{" "}
                <span className="font-medium">{formatScanDateTime(result.last_scan_at)}</span>
              </p>
            </div>
            <ul className="space-y-0.5">
              {result.scanned_roots.map((root, idx) => (
                <li key={idx} className="font-mono text-[11px] text-foreground/70 pl-6">
                  {root}
                </li>
              ))}
            </ul>
          </Card>

          {/* Exportar */}
          {result.export_id && (
            <div className="mb-6">
              <a href={`/cruce-produccion/export?id=${result.export_id}`} download>
                <Button variant="outline">
                  <FileDown className="h-4 w-4" />
                  Exportar Excel
                </Button>
              </a>
            </div>
          )}

          {/* Buscador compartido: filtra faltantes y soportes no actualizados */}
          <div className="flex justify-end mb-4">
            <div className="relative">
              <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Buscar código, responsable, facturador o motivo…"
                className="pl-8 w-64 text-xs"
              />
            </div>
          </div>

          {/* Faltantes en carpetas */}
          <Card className="p-6 border-border bg-card shadow-none mb-6">
            <details>
              <summary className="flex items-center gap-2 cursor-pointer pb-3 border-b border-border list-none">
                <FolderOpen className="h-5 w-5 text-danger" />
                <h3 className="font-display font-semibold text-foreground text-sm">
                  Faltantes en carpetas
                  {filter.trim() ? (
                    <span className="text-muted-foreground ml-1">
                      ({filteredFaltantes.length} de {result.faltantes.length})
                    </span>
                  ) : (
                    <span className="text-muted-foreground ml-1">
                      ({result.faltantes.length})
                    </span>
                  )}
                </h3>
              </summary>
              {filteredFaltantes.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2 pt-3">
                {result.faltantes.length === 0
                  ? "Sin faltantes: toda la producción tiene carpeta."
                  : "Sin coincidencias para el filtro actual."}
              </p>
            ) : (
              <div className="overflow-x-auto pt-3">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Código</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Número Factura</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Responsable</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Fec. Factura</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Novedad</th>
                      <th className="text-left font-semibold text-foreground pb-2 pr-3">Facturador</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFaltantes.map((f, idx) => (
                      <tr key={idx} className="border-b border-border/50 last:border-0">
                        <td className="py-1.5 pr-3 text-foreground/90 font-medium">{f.codigo}</td>
                        <td className="py-1.5 pr-3 text-foreground/80 max-w-[220px] truncate" title={f.numero_factura_original}>
                          {f.numero_factura_original}
                        </td>
                        <td className="py-1.5 pr-3 text-foreground/80">{f.responsable}</td>
                        <td className="py-1.5 pr-3 text-foreground/80">
                          {f.fec_factura ? formatScanDateTime(f.fec_factura) : "—"}
                        </td>
                        <td className="py-1.5 pr-3">
                          {f.estado_novedad === "S" ? (
                            <span className="inline-flex items-center rounded-full border border-danger/30 bg-danger/5 px-2 py-0.5 text-[11px] font-medium text-danger">
                              Pendiente
                            </span>
                          ) : f.estado_novedad ? (
                            <span className="inline-flex items-center rounded-full border border-info/30 bg-info/5 px-2 py-0.5 text-[11px] font-medium text-info">
                              Resuelto
                            </span>
                          ) : (
                            <span className="text-foreground/60">—</span>
                          )}
                        </td>
                        <td className="py-1.5 pr-3 text-foreground/60">{f.facturador}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            </details>
          </Card>

          {/* Soportes no actualizados */}
          <Card className="p-6 border-border bg-card shadow-none mb-6">
            <details>
              <summary className="flex items-center gap-2 cursor-pointer pb-3 border-b border-border list-none">
                <AlertTriangle className="h-5 w-5 text-warning-foreground" />
                <h3 className="font-display font-semibold text-foreground text-sm">
                  Soportes no actualizados
                  {filter.trim() ? (
                    <span className="text-muted-foreground ml-1">
                      ({filteredDesactualizados.length} de {(result.desactualizados ?? []).length})
                    </span>
                  ) : (
                    <span className="text-muted-foreground ml-1">
                      ({(result.desactualizados ?? []).length})
                    </span>
                  )}
                </h3>
              </summary>
              {filteredDesactualizados.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2 pt-3">
                  {(result.desactualizados ?? []).length === 0
                    ? "Sin soportes desactualizados: las carpetas están al día con las novedades."
                    : "Sin coincidencias para el filtro actual."}
                </p>
              ) : (
                <div className="overflow-x-auto pt-3">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Código</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Facturador</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Modificada</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Estado novedad</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Motivo</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Fecha estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredDesactualizados.map((d, idx) => (
                        <tr key={idx} className="border-b border-border/50 last:border-0">
                          <td className="py-1.5 pr-3 text-foreground/90 font-medium" title={d.full_path}>
                            {d.codigo}
                          </td>
                          <td className="py-1.5 pr-3 text-foreground/60">{d.facturador}</td>
                          <td className="py-1.5 pr-3 text-foreground/80">
                            {d.mtime_carpeta ? formatScanDateTime(d.mtime_carpeta) : "—"}
                          </td>
                          <td className="py-1.5 pr-3">
                            {d.estado_novedad === "S" ? (
                              <span className="inline-flex items-center rounded-full border border-danger/30 bg-danger/5 px-2 py-0.5 text-[11px] font-medium text-danger">
                                Pendiente
                              </span>
                            ) : (
                              <span className="inline-flex items-center rounded-full border border-info/30 bg-info/5 px-2 py-0.5 text-[11px] font-medium text-info">
                                {d.estado_novedad} · Resuelto
                              </span>
                            )}
                          </td>
                          <td className="py-1.5 pr-3 text-foreground/80 max-w-[220px] truncate" title={d.motivo}>
                            {d.motivo}
                          </td>
                          <td className="py-1.5 pr-3 text-foreground/80">
                            {d.fecha_estado ? formatScanDateTime(d.fecha_estado) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </details>
          </Card>

          {/* Tabla Revisar */}
          {result.revisar.length > 0 && (
            <Card className="p-6 border-border bg-card shadow-none">
              <details>
                <summary className="flex items-center gap-2 cursor-pointer pb-3 border-b border-border list-none">
                  <AlertTriangle className="h-5 w-5 text-warning-foreground" />
                  <h3 className="font-display font-semibold text-foreground text-sm">
                    Revisar: sin código extraíble ({result.revisar.length})
                  </h3>
                </summary>
                <div className="overflow-x-auto pt-3">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Número Factura</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Responsable</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Fec. Factura</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Facturador</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.revisar.map((r, idx) => (
                        <tr key={idx} className="border-b border-border/50 last:border-0">
                          <td className="py-1.5 pr-3 text-foreground/80 max-w-[220px] truncate" title={r.numero_factura_original}>
                            {r.numero_factura_original}
                          </td>
                          <td className="py-1.5 pr-3 text-foreground/80">{r.responsable}</td>
                          <td className="py-1.5 pr-3 text-foreground/80">
                            {r.fec_factura ? formatScanDateTime(r.fec_factura) : "—"}
                          </td>
                          <td className="py-1.5 pr-3 text-foreground/60">{r.facturador}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
