import {
  FileText,
  ClipboardCheck,
  CalendarClock,
  ArrowRight,
  TrendingUp,
  Clock,
  CheckCircle2,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";

interface IndexKpi {
  label: string;
  value: string;
  trend: string;
}

interface IndexArea {
  title: string;
  description: string;
  href: string;
  pending: number;
  pending_label: string;
  tone: "danger" | "warning" | "success" | "info" | "neutral";
}

interface IndexData {
  can_write: boolean;
  username: string;
  kpis: IndexKpi[];
  areas: IndexArea[];
}

const initialData = (window as unknown as { __INITIAL_DATA__?: IndexData }).__INITIAL_DATA__;

const kpis: IndexKpi[] = initialData?.kpis ?? [
  { label: "Facturas del mes", value: "1,248", trend: "+12% vs abril" },
  { label: "Pendientes de revisión", value: "40", trend: "9 novedades · 31 errores" },
  { label: "Resueltas este mes", value: "1,208", trend: "Cierre al día 24" },
];

const areas: IndexArea[] = initialData?.areas ?? [
  {
    title: "Urgencias",
    description: "Procesamiento y validación de facturas del servicio de urgencias.",
    href: "/urgencias/react",
    pending: 31,
    pending_label: "errores",
    tone: "danger",
  },
  {
    title: "Control de Novedades",
    description: "Registro y seguimiento de novedades en facturación.",
    href: "/control-errores/react",
    pending: 9,
    pending_label: "pendientes",
    tone: "warning",
  },
  {
    title: "Facturas Abiertas",
    description: "Gestión de horarios y responsables del servicio de urgencias.",
    href: "/abiertas-urgencias/react",
    pending: 0,
    pending_label: "sin horario",
    tone: "info",
  },
];

const kpiIcons = [TrendingUp, Clock, CheckCircle2];
const areaIcons = [FileText, ClipboardCheck, CalendarClock];

const kpiToneClasses = [
  "bg-primary/10 text-primary",
  "bg-warning/15 text-warning-foreground",
  "bg-success/10 text-success",
];

export function IndexPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle
        eyebrow="Mayo 2026"
        title="Panel principal"
        description="Selecciona el área de trabajo. Las cifras reflejan el estado actual del cierre de facturación."
      />

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {kpis.map((k, i) => {
          const Icon = kpiIcons[i] ?? TrendingUp;
          return (
            <Card key={k.label} className="p-5 border-border bg-card shadow-none">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                    {k.label}
                  </p>
                  <p className="font-display text-3xl font-semibold text-foreground mt-2">
                    {k.value}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1.5">{k.trend}</p>
                </div>
                <div className={`flex h-10 w-10 items-center justify-center rounded-md ${kpiToneClasses[i] ?? kpiToneClasses[0]}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
            </Card>
          );
        })}
      </section>

      <h2 className="font-display text-lg font-semibold text-foreground mb-3">
        Áreas de trabajo
      </h2>
      <div className="grid grid-cols-1 gap-3">
        {areas.map((area, i) => {
          const Icon = areaIcons[i] ?? FileText;
          return (
            <a
              key={area.href}
              href={area.href}
              className="group block rounded-lg border border-border bg-card p-5 transition-all hover:border-primary hover:shadow-sm"
            >
              <div className="flex items-center gap-5">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-display font-semibold text-foreground">{area.title}</h3>
                    {area.pending > 0 && (
                      <StatusBadge tone={area.tone} dot>
                        {area.pending} {area.pending_label}
                      </StatusBadge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mt-0.5">{area.description}</p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
              </div>
            </a>
          );
        })}
      </div>

      <footer className="mt-12 pt-6 border-t border-border text-center text-xs text-muted-foreground">
        Mini.local v1.0 — Hospital Orito · Sistema de Control de Facturación
      </footer>
    </div>
  );
}
