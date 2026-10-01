import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  FileText,
  ClipboardCheck,
  CalendarClock,
  FileSpreadsheet,
  Scale,
  FolderSearch,
  Users,
  Upload,
  BookType,
  LogOut,
  FlaskConical,
  Search,
  FileSearch,
  ArrowRightLeft,
  ArrowLeftRight,
  Settings,
} from "lucide-react";

type IconComponent = React.ComponentType<{ className?: string }>;

// Mapa estatico nombre-lucide → componente para los iconos que usa el
// sidebar hoy. La API devuelve solo el nombre; el filtrado por permisos
// ya lo hizo el servidor (GET /api/nav).
const ICONS: Record<string, IconComponent> = {
  LayoutDashboard,
  FileText,
  ClipboardCheck,
  CalendarClock,
  FileSpreadsheet,
  Scale,
  FolderSearch,
  Users,
  Upload,
  BookType,
  FlaskConical,
  Search,
  FileSearch,
  ArrowRightLeft,
  ArrowLeftRight,
  Settings,
};

// Fallback generico (componente ya importado): un modulo nuevo con un
// icono desconocido nunca rompe el sidebar.
const FALLBACK_ICON: IconComponent = LayoutDashboard;

// Lookup insensible a mayusculas (la API puede traer "upload" o "Upload").
const ICON_LOOKUP: Record<string, IconComponent> = Object.fromEntries(
  Object.entries(ICONS).map(([name, component]) => [name.toLowerCase(), component]),
);

function resolveIcon(name: unknown): IconComponent {
  if (typeof name !== "string") return FALLBACK_ICON;
  return ICON_LOOKUP[name.toLowerCase()] ?? FALLBACK_ICON;
}

interface ApiNavItem {
  label: string;
  href: string;
  icon: string;
}

interface NavItem {
  label: string;
  href: string;
  Icon: IconComponent;
  exact?: boolean;
}

interface AppSidebarProps {
  username?: string;
  permisos?: string[];
  collapsed: boolean;
}

export function AppSidebar({ username = "", collapsed }: AppSidebarProps) {
  // null = cargando (GET /api/nav en vuelo); [] = error o sin modulos.
  const [items, setItems] = useState<NavItem[] | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/api/nav", { headers: { Accept: "application/json" } })
      .then((res) => {
        if (!res.ok) throw new Error(`GET /api/nav: HTTP ${res.status}`);
        return res.json();
      })
      .then((body: { data?: { modulos?: ApiNavItem[] } }) => {
        if (!alive) return;
        const modulos = body?.data?.modulos;
        if (!Array.isArray(modulos)) {
          setItems([]);
          return;
        }
        setItems(
          modulos
            .filter(
              (m): m is ApiNavItem =>
                typeof m?.label === "string" && typeof m?.href === "string",
            )
            .map((m) => ({
              label: m.label,
              href: m.href,
              Icon: resolveIcon(m.icon),
              exact: m.href === "/dashboard",
            })),
        );
      })
      .catch(() => {
        // Error de red o respuesta invalida: sidebar vacio, sin crashear.
        if (alive) setItems([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return location.pathname === href;
    return location.pathname === href || location.pathname.startsWith(href + "/");
  };

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
        {items === null ? (
          <div className="space-y-0.5 px-2" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-md animate-pulse">
                <div className="h-4 w-4 shrink-0 rounded" style={{ backgroundColor: "var(--color-sidebar-accent)" }} />
                {!collapsed && (
                  <div className="h-4 flex-1 rounded" style={{ backgroundColor: "var(--color-sidebar-accent)" }} />
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-0.5 px-2">
            {items.map((item) => {
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
                  <item.Icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </a>
              );
            })}
          </div>
        )}
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
