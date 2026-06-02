import {
  LayoutDashboard,
  FileText,
  ClipboardCheck,
  CalendarClock,
  FileSpreadsheet,
  Scale,
  Users,
  Upload,
  BookType,
  LogOut,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  permiso?: string;
  exact?: boolean;
}

const ALL_NAV: NavItem[] = [
  { label: "Panel principal", href: "/dashboard", icon: LayoutDashboard, exact: true },
  { label: "Procesar", href: "/procesar", icon: FileText, permiso: "urgencias" },
  { label: "Control de Novedades", href: "/control-errores", icon: ClipboardCheck, permiso: "control_urgencias" },
  { label: "Abiertas Urgencias", href: "/abiertas-urgencias", icon: CalendarClock, permiso: "facturas_abiertas" },
  { label: "Cronograma Urgencias", href: "/cronograma-urgencias", icon: CalendarClock, permiso: "*" },
  { label: "Cronograma Bacteriólogas", href: "/cronograma-bacteriologas", icon: CalendarClock, permiso: "*" },
  { label: "Ordenado y Facturado", href: "/ordenado-facturado", icon: FileSpreadsheet, permiso: "equipos_basicos" },
  { label: "Derechos", href: "/derechos", icon: Scale, permiso: "derechos" },
  { label: "Usuarios", href: "/auth/usuarios", icon: Users, permiso: "*" },
  { label: "Importar Facturas", href: "/import-facturas", icon: Upload, permiso: "*" },
  { label: "Catálogos", href: "/catalogo", icon: BookType, permiso: "*" },
];

interface AppSidebarProps {
  username?: string;
  permisos?: string[];
  collapsed: boolean;
}

export function AppSidebar({ username = "", permisos = [], collapsed }: AppSidebarProps) {
  const isActive = (href: string, exact?: boolean) => {
    if (exact) return location.pathname === href;
    return location.pathname === href || location.pathname.startsWith(href + "/");
  };

  const isAdmin = permisos.includes("*");

  // Expandir :write → base (ej: control_urgencias:write → control_urgencias)
  const expandedPermisos = new Set(permisos);
  permisos.forEach((p) => {
    if (p.endsWith(":write")) {
      expandedPermisos.add(p.replace(/:write$/, ""));
    }
  });

  const visibleItems = ALL_NAV.filter((item) => {
    if (!item.permiso) return true;
    if (isAdmin) return true;
    return expandedPermisos.has(item.permiso);
  });

  return (
    <aside
      className="fixed left-0 top-0 h-screen z-40 flex flex-col border-r transition-all duration-200"
      style={{
        width: collapsed ? "4rem" : "16rem",
        backgroundColor: "var(--color-sidebar)",
        borderColor: "var(--color-sidebar-border)",
        color: "var(--color-sidebar-foreground)",
      }}
    >
      {/* HO logo */}
      <div className="flex items-center gap-3 min-w-0 px-3 py-4 border-b" style={{ borderColor: "var(--color-sidebar-border)" }}>
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md font-heading font-bold text-sm"
          style={{ backgroundColor: "var(--color-sidebar-primary)", color: "var(--color-sidebar-primary-foreground)" }}
        >
          HO
        </div>
        {!collapsed && (
          <div className="flex flex-col min-w-0">
            <span className="font-heading text-sm font-semibold truncate" style={{ color: "var(--color-sidebar-foreground)" }}>
              Hospital Orito
            </span>
            <span className="text-[11px] uppercase tracking-wider" style={{ color: "var(--color-sidebar-foreground)", opacity: 0.6 }}>
              Facturación
            </span>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {!collapsed && (
          <p className="px-4 pb-1 text-[11px] uppercase tracking-wider font-medium" style={{ color: "var(--color-sidebar-foreground)", opacity: 0.5 }}>
            Áreas de trabajo
          </p>
        )}
        <div className="space-y-0.5 px-2">
          {visibleItems.map((item) => {
            const active = isActive(item.href, item.exact);
            return (
              <a
                key={item.href}
                href={item.href}
                className="flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150"
                style={{
                  backgroundColor: active ? "var(--color-sidebar-primary)" : "transparent",
                  color: active ? "var(--color-sidebar-primary-foreground)" : "var(--color-sidebar-foreground)",
                  opacity: active ? 1 : 0.8,
                }}
                onMouseEnter={(e) => {
                  if (!active) {
                    e.currentTarget.style.backgroundColor = "var(--color-sidebar-accent)";
                    e.currentTarget.style.opacity = "1";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.opacity = "0.8";
                  }
                }}
                title={item.label}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </a>
            );
          })}
        </div>
      </nav>

      {/* Footer: logout */}
      <div className="p-2" style={{ borderTop: "1px solid var(--color-sidebar-border)" }}>
        {username && (
          <a
            href="/auth/logout"
            className="flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150"
            style={{ color: "var(--color-sidebar-foreground)", opacity: 0.7 }}
            onMouseEnter={(e) => { e.currentTarget.style.opacity = "1"; e.currentTarget.style.backgroundColor = "var(--color-sidebar-accent)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.opacity = "0.7"; e.currentTarget.style.backgroundColor = "transparent"; }}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Cerrar sesión</span>}
          </a>
        )}
      </div>
    </aside>
  );
}
