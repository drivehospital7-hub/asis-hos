import { ShieldCheck, UserCircle2 } from "lucide-react";
import type { ReactNode } from "react";

export function AppHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-primary/20 bg-primary px-4 text-primary-foreground md:px-6">
      <div className="flex items-center gap-3">
        {children}
        <div className="hidden md:flex items-center gap-2 text-sm">
          <span className="font-display font-semibold tracking-tight">Hospital Orito</span>
          <span className="text-primary-foreground/50">·</span>
          <span className="text-primary-foreground/80">Sistema de Control de Facturación</span>
        </div>
        <div className="md:hidden font-display font-semibold text-sm">Hospital Orito</div>
      </div>

      <div className="flex items-center gap-3">
        <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-success/20 px-2.5 py-1 text-xs font-medium text-success-foreground ring-1 ring-success/40">
          <ShieldCheck className="h-3.5 w-3.5" />
          Sesión iniciada
        </span>
        <div className="flex items-center gap-2 text-sm">
          <UserCircle2 className="h-5 w-5 text-primary-foreground/80" />
          <span className="hidden sm:inline text-primary-foreground/90">urgencias</span>
        </div>
      </div>
    </header>
  );
}
