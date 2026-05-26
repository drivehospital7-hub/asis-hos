import { useEffect, useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { UserCircle2, PanelLeftClose, PanelLeftOpen, KeyRound, LogOut } from "lucide-react";

import { ChangePasswordDialog } from "@/components/change-password-dialog";

interface AppHeaderProps {
  username?: string;
  collapsed: boolean;
  onToggle: () => void;
}

export function AppHeader({ username = "", collapsed, onToggle }: AppHeaderProps) {
  const [authed, setAuthed] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch("/auth/api/status");
        const data = await res.json();
        setAuthed(data.data?.authenticated ?? false);
      } catch {
        setAuthed(false);
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = async () => {
    await fetch("/auth/api/logout", { method: "POST" });
    window.location.href = "/auth/login";
  };

  return (
    <header
      className="sticky top-0 z-30 flex h-14 items-center justify-between px-4 md:px-6"
      style={{ backgroundColor: "var(--color-primary)", color: "var(--color-primary-foreground)" }}
    >
      <div className="flex items-center gap-3">
        {/* Sidebar toggle — siempre visible */}
        <button
          onClick={onToggle}
          className="flex items-center justify-center p-1 rounded-md hover:bg-white/10 transition-colors flex-shrink-0"
          title={collapsed ? "Expandir menú" : "Colapsar menú"}
        >
          {collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
        </button>

        <div className="hidden md:flex items-center gap-2 text-sm">
          <span className="font-display font-semibold tracking-tight">Hospital Orito</span>
          <span style={{ opacity: 0.5 }}>·</span>
          <span style={{ opacity: 0.8 }}>Sistema de Control de Facturación</span>
        </div>
        <div className="md:hidden font-display font-semibold text-sm">Hospital Orito</div>
      </div>

      <div className="flex items-center gap-3">
        {authed && (
          <>
            <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium text-white ring-1 ring-inset"
                  style={{ backgroundColor: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.3)" }}>
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              Sesión iniciada
            </span>

            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <button className="flex items-center gap-2 text-sm rounded-md hover:bg-white/10 transition-colors px-2 py-1 focus:outline-none">
                  <UserCircle2 className="h-5 w-5 shrink-0" style={{ opacity: 0.8 }} />
                  <span className="hidden sm:inline" style={{ opacity: 0.9 }}>{username}</span>
                </button>
              </DropdownMenu.Trigger>

              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  className="z-50 min-w-[200px] rounded-lg border bg-white p-1 shadow-lg"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                  sideOffset={8}
                  align="end"
                >
                  <DropdownMenu.Label className="px-3 py-2 text-xs font-medium" style={{ color: "oklch(0.55 0.04 160)" }}>
                    Usuario: {username}
                  </DropdownMenu.Label>

                  <DropdownMenu.Separator className="mx-2 my-1 h-px" style={{ backgroundColor: "oklch(0.55 0.04 160 / 0.1)" }} />

                  <DropdownMenu.Item
                    className="flex items-center gap-2 rounded-md px-3 py-2 text-sm cursor-pointer outline-none transition-colors data-[highlighted]:bg-gray-100"
                    style={{ color: "oklch(0.15 0.02 160)" }}
                    onSelect={() => setChangePasswordOpen(true)}
                  >
                    <KeyRound className="h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} />
                    Cambiar contraseña
                  </DropdownMenu.Item>

                  <DropdownMenu.Item
                    className="flex items-center gap-2 rounded-md px-3 py-2 text-sm cursor-pointer outline-none transition-colors data-[highlighted]:bg-gray-100"
                    style={{ color: "oklch(0.4 0.15 25)" }}
                    onSelect={handleLogout}
                  >
                    <LogOut className="h-4 w-4" />
                    Cerrar Sesión
                  </DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          </>
        )}
      </div>

      <ChangePasswordDialog open={changePasswordOpen} onOpenChange={setChangePasswordOpen} />
    </header>
  );
}
