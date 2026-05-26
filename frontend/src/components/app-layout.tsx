import { useState, useEffect, useRef, type ReactNode } from "react";
import { AppSidebar } from "./app-sidebar";
import { AppHeader } from "./app-header";
import { ConfirmDialog, type ConfirmDialogHandle } from "./ConfirmDialog";

interface AppLayoutProps {
  children: ReactNode;
  username?: string;
  permisos?: string[];
}

export function AppLayout({ children, username, permisos }: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState(true);
  const confirmRef = useRef<ConfirmDialogHandle>(null);

  useEffect(() => {
    const saved = localStorage.getItem("sidebar-collapsed");
    const isMobile = window.innerWidth < 768;
    if (!isMobile && saved !== "true") setCollapsed(false);
    if (isMobile) setCollapsed(true);
  }, []);

  useEffect(() => {
    // Expose a global helper so all React pages can show a confirm dialog
    // without each page needing its own ConfirmDialog instance.
    (window as unknown as Record<string, unknown>).__showConfirm =
      (msg: string) => confirmRef.current?.show(msg) ?? Promise.resolve(false);
    return () => {
      delete (window as unknown as Record<string, unknown>).__showConfirm;
    };
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
      <ConfirmDialog ref={confirmRef} />
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
