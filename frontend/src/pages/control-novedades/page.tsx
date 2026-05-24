import { useState } from "react";
import {
  Download,
  Upload,
  Plus,
  Search,
  Calendar,
  Clock,
  CheckCircle2,
  Eye,
  Pencil,
  Trash2,
  Filter,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";

interface Mes {
  label: string;
  count: number;
  active?: boolean;
}

interface Novedad {
  factura: string;
  creado: string;
  categoria: string;
  descripcion: string;
  facturador: string;
  iniciales?: string;
  estado: string;
}

interface ControlNovedadesData {
  can_write: boolean;
  username: string;
  meses: Mes[];
  novedades: Novedad[];
}

const initialData = (window as unknown as { __INITIAL_DATA__?: ControlNovedadesData }).__INITIAL_DATA__;

const meses: Mes[] = initialData?.meses ?? [
  { label: "May 2026", count: 10, active: true },
  { label: "Abr 2026", count: 0 },
  { label: "Mar 2026", count: 0 },
  { label: "Feb 2026", count: 0 },
  { label: "Ene 2026", count: 0 },
  { label: "Dic 2025", count: 0 },
];

const novedades: Novedad[] = initialData?.novedades ?? [
  { factura: "FEV9921", creado: "Ayer", categoria: "Centro de Costo", descripcion: "Reasignación", facturador: "ARIAS C.", iniciales: "AC", estado: "resuelto" },
];

export function ControlNovedadesPage() {
  const [mesActivo, setMesActivo] = useState(
    meses.find((m) => m.active)?.label ?? meses[0]?.label ?? "",
  );

  const pendientes = novedades.filter((n) => n.estado === "pendiente").length;
  const resueltos = novedades.filter((n) => n.estado === "resuelto").length;

  return (
    <div className="mx-auto max-w-7xl">
      <Breadcrumbs items={[{ label: "Control de Novedades" }]} />

      <PageTitle
        eyebrow="Servicio de Urgencias"
        title="Control de Novedades"
        description="Registro, seguimiento y resolución de novedades en facturación."
        actions={
          <>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4" />
              Exportar
            </Button>
            <Button variant="outline" size="sm">
              <Upload className="h-4 w-4" />
              Carga masiva
            </Button>
            <Button size="sm" className="bg-primary hover:bg-primary/90">
              <Plus className="h-4 w-4" />
              Agregar novedad
            </Button>
          </>
        }
      />

      {/* Tabs de meses */}
      <div className="flex items-center gap-1 border-b border-border mb-6 overflow-x-auto">
        {meses.map((m) => (
          <button
            key={m.label}
            onClick={() => setMesActivo(m.label)}
            className={cn(
              "relative flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors -mb-px",
              mesActivo === m.label
                ? "text-primary border-b-2 border-primary"
                : "text-muted-foreground hover:text-foreground border-b-2 border-transparent",
            )}
          >
            {m.label}
            <span
              className={cn(
                "inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-semibold",
                mesActivo === m.label ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
              )}
            >
              {m.count}
            </span>
          </button>
        ))}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <Card className="p-5 border-border bg-card shadow-none">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Total registrados</p>
              <p className="font-display text-3xl font-semibold text-foreground mt-2">{novedades.length}</p>
              <p className="text-xs text-muted-foreground mt-1.5">+3 esta semana</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Calendar className="h-5 w-5" />
            </div>
          </div>
        </Card>
        <Card className="p-5 border-border bg-card shadow-none">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Pendientes</p>
              <p className="font-display text-3xl font-semibold text-foreground mt-2">{pendientes}</p>
              <p className="text-xs text-muted-foreground mt-1.5">Requieren acción</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-warning/15 text-warning-foreground">
              <Clock className="h-5 w-5" />
            </div>
          </div>
        </Card>
        <Card className="p-5 border-border bg-card shadow-none">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Resueltos</p>
              <p className="font-display text-3xl font-semibold text-foreground mt-2">{resueltos}</p>
              <p className="text-xs text-muted-foreground mt-1.5">Cerrados este mes</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-success/10 text-success">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </div>
        </Card>
      </div>

      {/* Filtros */}
      <Card className="p-4 border-border bg-card shadow-none mb-4">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_auto_auto_auto] gap-3 items-center">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Buscar por factura, responsable o descripción…" className="pl-9 bg-background" />
          </div>
          <select className="h-9 rounded-md border border-input bg-background px-3 text-sm">
            <option>Todas las categorías</option>
            <option>Centro de Costo</option>
            <option>Otros</option>
          </select>
          <select className="h-9 rounded-md border border-input bg-background px-3 text-sm">
            <option>Todos los estados</option>
            <option>Pendiente</option>
            <option>Resuelto</option>
          </select>
          <select className="h-9 rounded-md border border-input bg-background px-3 text-sm">
            <option>Todos los responsables</option>
          </select>
          <Button variant="outline" size="sm">
            <Filter className="h-4 w-4" />
            Limpiar
          </Button>
        </div>
      </Card>

      {/* Tabla */}
      <Card className="border-border bg-card shadow-none overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="text-left font-medium px-4 py-3">Factura</th>
                <th className="text-left font-medium px-4 py-3">Creado</th>
                <th className="text-left font-medium px-4 py-3">Categoría</th>
                <th className="text-left font-medium px-4 py-3">Descripción</th>
                <th className="text-left font-medium px-4 py-3">Facturador cierre</th>
                <th className="text-left font-medium px-4 py-3">Estado</th>
                <th className="text-right font-medium px-4 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {novedades.map((n) => (
                <tr key={n.factura} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs font-medium text-foreground">{n.factura}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{n.creado}</td>
                  <td className="px-4 py-3">
                    <StatusBadge tone={n.categoria === "Centro de Costo" ? "info" : "neutral"}>
                      {n.categoria}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs truncate">{n.descripcion}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-secondary/15 text-secondary text-[10px] font-semibold">
                        {n.iniciales ?? "??"}
                      </div>
                      <span className="text-xs text-foreground/80">{n.facturador}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {n.estado === "pendiente" ? (
                      <StatusBadge tone="warning" dot>Pendiente</StatusBadge>
                    ) : (
                      <StatusBadge tone="success" dot>Resuelto</StatusBadge>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button size="icon" variant="ghost" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button size="icon" variant="ghost" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="icon" variant="ghost" className="h-8 w-8 text-muted-foreground hover:text-danger">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
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
