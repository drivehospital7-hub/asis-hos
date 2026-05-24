import { useState, useEffect, type ReactNode } from "react";
import { AppSidebar } from "./app-sidebar";
import { AppHeader } from "./app-header";

interface AppLayoutProps {
  children: ReactNode;
  username?: string;
  permisos?: string[];
}

export function AppLayout({ children, username, permisos }: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("sidebar-collapsed");
    const isMobile = window.innerWidth < 768;
    if (!isMobile && saved !== "true") setCollapsed(false);
    if (isMobile) setCollapsed(true);
  }, []);

  const toggle = () => {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem("sidebar-collapsed", String(next));
      return next;
    });
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--color-background)" }}>
      <AppSidebar username={username} permisos={permisos} collapsed={collapsed} />
      <div style={{ marginLeft: collapsed ? "4rem" : "16rem", transition: "margin-left 0.2s ease" }}>
        <AppHeader username={username} collapsed={collapsed} onToggle={toggle} />
        <main className="pb-8 pt-6">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
