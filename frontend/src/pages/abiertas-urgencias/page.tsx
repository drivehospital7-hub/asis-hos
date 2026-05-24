import { useState } from "react";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Users,
  CalendarDays,
  AlertCircle,
  Upload,
  FileEdit,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { cn } from "@/lib/utils";

export function AbiertasUrgenciasPage() {
  const [openAsignar, setOpenAsignar] = useState(false);
  const [openHorario, setOpenHorario] = useState(true);

  return (
    <div className="mx-auto max-w-5xl">
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

      {/* Asignar responsable */}
      <Card className="border-border bg-card shadow-none mb-4 overflow-hidden">
        <button
          onClick={() => setOpenAsignar(!openAsignar)}
          className="w-full flex items-center gap-4 p-5 text-left hover:bg-muted/30 transition-colors"
        >
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Users className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground">Asignar responsable desde horario</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Pega los datos de facturación para asignar automáticamente el responsable según el cronograma
            </p>
          </div>
          {openAsignar ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </button>
        {openAsignar && (
          <div className="border-t border-border p-5 bg-muted/20">
            <textarea
              placeholder="Pega aquí los datos de facturación…"
              className="w-full min-h-32 rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <div className="mt-3 flex justify-end">
              <Button size="sm" className="bg-primary hover:bg-primary/90">Asignar</Button>
            </div>
          </div>
        )}
      </Card>

      {/* Ver horario */}
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
            <p className="text-xs text-muted-foreground mt-0.5">Turnos cargados del mes en curso</p>
          </div>
          {openHorario ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </button>
        {openHorario && (
          <div className="border-t border-border">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="text-left font-medium px-5 py-3 w-32">Día</th>
                    <th className="text-left font-medium px-5 py-3">07:00 – 13:00</th>
                    <th className="text-left font-medium px-5 py-3">13:00 – 19:00</th>
                    <th className="text-left font-medium px-5 py-3">19:00 – 07:00</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td colSpan={4} className="px-5 py-12 text-center">
                      <CalendarDays className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">Sin datos de horario</p>
                      <p className="text-xs text-muted-foreground/70 mt-1">
                        Carga el cronograma del mes para visualizar los turnos.
                      </p>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      {/* Aviso falta cargar horario */}
      <Card className={cn(
        "border-warning/40 bg-warning/5 shadow-none p-5",
      )}>
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-warning/20 text-warning-foreground">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground">Falta cargar el horario</h3>
            <p className="text-sm text-muted-foreground mt-0.5">
              No hay horario para el mes actual. Usa &ldquo;Cargar&rdquo; para agregar los turnos del mes.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline">
              <FileEdit className="h-4 w-4" />
              Editar
            </Button>
            <Button size="sm" className="bg-primary hover:bg-primary/90">
              <Upload className="h-4 w-4" />
              Cargar
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
