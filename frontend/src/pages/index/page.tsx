import { useEffect, useState } from "react";
import {
  FileText,
  ClipboardCheck,
  CalendarClock,
  ArrowRight,
  TrendingUp,
  Clock,
  CheckCircle2,
  Inbox,
  Printer,
  type LucideIcon,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { PageTitle } from "@/components/page-title";
import { StatusBadge } from "@/components/status-badge";

interface IndexKpi {
  label: string;
  value: string;
  trend: string;
  icon?: string;
  tone?: string;
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
  month_label?: string;
  kpis: IndexKpi[];
  areas: IndexArea[];
}

const initialData = (window as unknown as { __INITIAL_DATA__?: IndexData }).__INITIAL_DATA__;

const MESES_ES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

function fallbackMonthLabel(): string {
  const now = new Date();
  return `${MESES_ES[now.getMonth()]} ${now.getFullYear()}`;
}

const monthLabel = initialData?.month_label || fallbackMonthLabel();

const kpis: IndexKpi[] = initialData?.kpis ?? [
  { label: "Novedades del mes", value: "0", trend: "Sin datos", icon: "inbox", tone: "info" },
  { label: "Pendientes", value: "0", trend: "Sin datos", icon: "clock", tone: "warning" },
  { label: "Resueltas este mes", value: "0", trend: "Sin datos", icon: "check-circle", tone: "success" },
  { label: "Tasa de resolución", value: "0%", trend: "Sin datos", icon: "trending-up", tone: "primary" },
];

const areas: IndexArea[] = initialData?.areas ?? [];

const kpiIcons: Record<string, LucideIcon> = {
  "inbox": Inbox,
  "clock": Clock,
  "check-circle": CheckCircle2,
  "trending-up": TrendingUp,
};

const kpiToneClasses: Record<string, string> = {
  info: "bg-info/10 text-info",
  warning: "bg-warning/15 text-warning-foreground",
  success: "bg-success/10 text-success",
  primary: "bg-primary/10 text-primary",
};

const kpiBarClasses: Record<string, string> = {
  info: "bg-info",
  warning: "bg-warning",
  success: "bg-success",
  primary: "bg-primary",
};

const areaIcons = [FileText, ClipboardCheck, CalendarClock];

/** Extrae el número líder de un valor ("1,248" → 1248, "87%" → 87). */
function parseLeadingNumber(value: string): number | null {
  const match = value.replace(/,/g, "").match(/[\d.]+/);
  if (!match) return null;
  const n = Number(match[0]);
  return Number.isFinite(n) ? n : null;
}

/** Reconstruye el valor conservando sufijo/prefijo ("%") con el número animado. */
function formatAnimated(value: string, current: number): string {
  const rounded = Math.round(current).toLocaleString("es-CO");
  if (value.trim().endsWith("%")) return `${rounded}%`;
  return rounded;
}

function useCountUp(target: number, duration = 900): number {
  const [current, setCurrent] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setCurrent(target);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min((t - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setCurrent(target * eased);
      if (p < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    // Al imprimir, fijar el valor final para no capturar la animación a medias.
    const onBeforePrint = () => setCurrent(target);
    window.addEventListener("beforeprint", onBeforePrint);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("beforeprint", onBeforePrint);
    };
  }, [target, duration]);
  return current;
}

function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const t = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(t);
  }, []);
  return mounted;
}

function KpiCard({ kpi, index }: { kpi: IndexKpi; index: number }) {
  const Icon = kpiIcons[kpi.icon ?? ""] ?? TrendingUp;
  const tone = kpi.tone ?? "primary";
  const target = parseLeadingNumber(kpi.value);
  const animated = useCountUp(target ?? 0);
  const mounted = useMounted();
  const isRate = kpi.value.trim().endsWith("%");
  const rate = target ?? 0;

  return (
    <Card
      className="animate-fade-up p-5 border-border bg-card shadow-none transition-all duration-300 hover:-translate-y-1 hover:shadow-md hover:border-primary/40"
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            {kpi.label}
          </p>
          <p className="font-display text-3xl font-semibold text-foreground mt-2 tabular-nums">
            {target === null ? kpi.value : formatAnimated(kpi.value, animated)}
          </p>
          <p className="text-xs text-muted-foreground mt-1.5">{kpi.trend}</p>
        </div>
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md ${kpiToneClasses[tone] ?? kpiToneClasses.primary}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {isRate && (
        <div
          className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuenow={Math.round(rate)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={kpi.label}
        >
          <div
            className={`h-full rounded-full transition-[width] duration-1000 ease-out ${kpiBarClasses[tone] ?? kpiBarClasses.primary}`}
            style={{ width: mounted ? `${Math.min(Math.max(rate, 0), 100)}%` : "0%" }}
          />
        </div>
      )}
    </Card>
  );
}

export function IndexPage() {
  // Acota las reglas `@media print` solo al dashboard (ver globals.css).
  useEffect(() => {
    document.body.classList.add("page-dashboard");
    return () => document.body.classList.remove("page-dashboard");
  }, []);

  return (
    <div className="mx-auto max-w-6xl">
      <PageTitle
        eyebrow={monthLabel}
        title="Panel principal"
        description="Control de novedades del mes actual: pendientes, resueltas y tasa de resolución del cierre de facturación."
        actions={
          <button
            type="button"
            onClick={() => window.print()}
            className="no-print inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:border-primary hover:text-primary"
          >
            <Printer className="h-4 w-4" />
            Imprimir
          </button>
        }
      />

      <section id="dashboard-stats" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {kpis.map((k, i) => (
          <KpiCard key={k.label} kpi={k} index={i} />
        ))}
      </section>

      <h2 className="no-print font-display text-lg font-semibold text-foreground mb-3">
        Áreas de trabajo
      </h2>
      <div className="no-print grid grid-cols-1 gap-3">
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
                <ArrowRight className="h-4 w-4 text-muted-foreground group:text-primary group:translate-x-0.5 transition-all" />
              </div>
            </a>
          );
        })}
      </div>

      <footer className="no-print mt-12 pt-6 border-t border-border text-center text-xs text-muted-foreground">
        Mini.local v1.0 — Hospital Orito · Sistema de Control de Facturación
      </footer>
    </div>
  );
}
