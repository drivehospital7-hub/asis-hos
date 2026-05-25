import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Upload, Info, FileSpreadsheet, ArrowRight, AlertTriangle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle, StatusBadge } from "@/components/status-badge";

export const Route = createFileRoute("/urgencias")({
  head: () => ({
    meta: [
      { title: "Urgencias · Hospital Orito" },
      { name: "description", content: "Procesamiento y validación de facturas del servicio de urgencias." },
      { property: "og:title", content: "Urgencias · Hospital Orito" },
      { property: "og:description", content: "Procesamiento y validación de facturas del servicio de urgencias." },
    ],
  }),
  component: UrgenciasPage,
});

const errores = [
  {
    factura: "CAP500990",
    responsable: "ARIAS CULCHA ANGIE CAROLINA",
    descripcion: "Centro de costo debería ser HOSPITALIZACIÓN - ESTANCIA GENERAL",
    procedimiento: "890601H - Valoración Inicial Intrahospitalaria por el Médico General",
    detalle: "URGENCIAS",
    categoria: "Centro de Costo",
  },
  {
    factura: "FEV421550",
    responsable: "ARIAS CULCHA ANGIE CAROLINA",
    descripcion: "Centro de costo debería ser HOSPITALIZACIÓN - ESTANCIA GENERAL",
    procedimiento: "890601H - Valoración Inicial Intrahospitalaria por el Médico General",
    detalle: "URGENCIAS",
    categoria: "Centro de Costo",
  },
  {
    factura: "FEV421557",
    responsable: "ARIAS CULCHA ANGIE CAROLINA",
    descripcion: "Centro de costo debería ser APOYO DIAGNÓSTICO",
    procedimiento: "873420 - Radiografía de Rodilla Ap. Lateral u Oblicua",
    detalle: "URGENCIAS",
    categoria: "Centro de Costo",
  },
];

function UrgenciasPage() {
  const [fileName, setFileName] = useState<string | null>("URGENCIAS MAYO.xlsx");

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Urgencias" }]} />
      <PageTitle
        eyebrow="Servicio de Urgencias"
        title="Procesamiento de facturas"
        description="Carga el reporte detallado en formato Excel para validar los registros y detectar inconsistencias."
      />

      {/* Upload card */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <h2 className="font-display font-semibold text-foreground mb-1">Subir archivo Excel</h2>
        <p className="text-xs text-muted-foreground mb-4">
          Formatos aceptados: .xlsx, .xls, .xlsm, .xlsb
        </p>

        <label
          htmlFor="file-upload"
          className="flex items-center gap-4 rounded-md border-2 border-dashed border-border bg-muted/40 p-5 cursor-pointer hover:border-primary/50 hover:bg-muted/60 transition-colors"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Upload className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            {fileName ? (
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-success" />
                <span className="text-sm font-medium text-foreground truncate">{fileName}</span>
              </div>
            ) : (
              <span className="text-sm text-muted-foreground">
                Arrastra el archivo aquí o haz clic para seleccionar
              </span>
            )}
          </div>
          <input
            id="file-upload"
            type="file"
            className="sr-only"
            accept=".xlsx,.xls,.xlsm,.xlsb"
            onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
          />
        </label>

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
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
            Procesar archivo
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </Card>

      {/* Errores */}
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
            <div className="font-display text-2xl font-semibold text-danger">31</div>
            <div className="text-xs text-muted-foreground">total</div>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-3">
          <h3 className="font-display text-sm font-semibold text-foreground">Centros de Costo</h3>
          <StatusBadge tone="danger">6 registros</StatusBadge>
        </div>

        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="text-left font-medium px-4 py-3">Factura</th>
                <th className="text-left font-medium px-4 py-3">Responsable cierre</th>
                <th className="text-left font-medium px-4 py-3">Descripción</th>
                <th className="text-left font-medium px-4 py-3">Procedimiento</th>
                <th className="text-left font-medium px-4 py-3">Detalle</th>
                <th className="text-right font-medium px-4 py-3">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {errores.map((e) => (
                <tr key={e.factura} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs font-medium text-foreground">{e.factura}</td>
                  <td className="px-4 py-3 text-xs text-foreground/80">{e.responsable}</td>
                  <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs">{e.descripcion}</td>
                  <td className="px-4 py-3 text-xs text-foreground/70 max-w-xs">{e.procedimiento}</td>
                  <td className="px-4 py-3">
                    <StatusBadge tone="warning">{e.detalle}</StatusBadge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button size="sm" variant="secondary" className="bg-secondary hover:bg-secondary/90">
                      Controlar
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
