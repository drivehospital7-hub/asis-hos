import { useEffect, useRef, useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { KeyRound, LogOut, UserCircle2 } from "lucide-react";

import { ChangePasswordDialog } from "@/components/change-password-dialog";

interface UserMenuProps {
  initialUsername?: string;
}

interface AuthStatus {
  authed: boolean;
  username: string;
}

declare global {
  interface Window {
    __INITIAL_DATA__?: { username?: string };
    ceAuth?: {
      isAuth: () => boolean;
      setAuth: (value: boolean) => void;
      logout: () => void;
    };
  }
}

// Username injected by Flask (base.html) before the island bundle loads.
function readServerUsername(fallback: string): string {
  if (window.__INITIAL_DATA__?.username) return window.__INITIAL_DATA__.username;
  const mount = document.getElementById("user-menu-root");
  return mount?.getAttribute("data-username") || fallback;
}

// The Jinja table listens for this event (control_errores.html) to enable
// or disable its actions, so the island must emit it on auth transitions.
function emitAuthChange(auth: boolean): void {
  window.dispatchEvent(new CustomEvent("ce-auth-change", { detail: { auth } }));
}

async function fetchAuthStatus(): Promise<AuthStatus> {
  try {
    const res = await fetch("/auth/api/status");
    const data = await res.json();
    return {
      authed: data.data?.authenticated ?? false,
      username: data.data?.username ?? "",
    };
  } catch {
    return { authed: false, username: "" };
  }
}

export function UserMenu({ initialUsername = "" }: UserMenuProps) {
  const [username, setUsername] = useState(initialUsername);
  const [authed, setAuthed] = useState(initialUsername !== "");
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const lastEmittedAuth = useRef<boolean | null>(null);

  useEffect(() => {
    setUsername(readServerUsername(initialUsername));
    let active = true;
    const check = async () => {
      const status = await fetchAuthStatus();
      if (!active) return;
      setAuthed(status.authed);
      if (status.username) setUsername(status.username);
      if (lastEmittedAuth.current !== status.authed) {
        lastEmittedAuth.current = status.authed;
        emitAuthChange(status.authed);
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [initialUsername]);

  const handleLogout = () => {
    // Reuse the canonical Jinja logout flow (clears storage, redirects).
    if (window.ceAuth) {
      window.ceAuth.logout();
      return;
    }
    fetch("/auth/api/logout", { method: "POST" }).finally(() => {
      window.location.href = "/auth/login";
    });
  };

  if (!authed) return null;

  return (
    <div className="flex items-center gap-3">
      <span
        className="hidden sm:inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
        style={{
          backgroundColor: "color-mix(in srgb, var(--success) 15%, transparent)",
          color: "var(--success)",
        }}
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        Sesión iniciada
      </span>

      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button
            className="flex items-center gap-2 text-sm rounded-md px-2 py-1 transition-colors focus:outline-none"
            style={{ color: "var(--foreground)" }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = "var(--muted)")}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
          >
            <UserCircle2 className="size-5 shrink-0" style={{ opacity: 0.8 }} />
            <span className="hidden sm:inline" style={{ opacity: 0.9 }}>
              {username}
            </span>
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            className="z-50 min-w-[200px] rounded-lg border bg-white p-1 shadow-lg"
            style={{ borderColor: "var(--border)" }}
            sideOffset={8}
            align="end"
          >
            <DropdownMenu.Label className="px-3 py-2 text-xs font-medium" style={{ color: "var(--primary)" }}>
              Usuario: {username}
            </DropdownMenu.Label>

            <DropdownMenu.Separator className="mx-2 my-1 h-px" style={{ backgroundColor: "var(--border)" }} />

            <DropdownMenu.Item
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm cursor-pointer outline-none transition-colors data-[highlighted]:bg-gray-100"
              style={{ color: "var(--foreground)" }}
              onSelect={() => setChangePasswordOpen(true)}
            >
              <KeyRound className="size-4" style={{ color: "var(--primary)" }} />
              Cambiar contraseña
            </DropdownMenu.Item>

            <DropdownMenu.Item
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm cursor-pointer outline-none transition-colors data-[highlighted]:bg-gray-100"
              style={{ color: "var(--destructive)" }}
              onSelect={handleLogout}
            >
              <LogOut className="size-4" />
              Cerrar Sesión
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      <ChangePasswordDialog open={changePasswordOpen} onOpenChange={setChangePasswordOpen} />
    </div>
  );
}
