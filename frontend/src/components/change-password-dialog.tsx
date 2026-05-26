import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Eye, EyeOff, KeyRound, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChangePasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface FieldVisibility {
  old: boolean;
  new: boolean;
  confirm: boolean;
}

export function ChangePasswordDialog({ open, onOpenChange }: ChangePasswordDialogProps) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState<FieldVisibility>({
    old: false,
    new: false,
    confirm: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const toggleVisibility = (field: keyof FieldVisibility) => {
    setShowPassword((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const resetForm = () => {
    setOldPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setShowPassword({ old: false, new: false, confirm: false });
    setError("");
    setSuccess("");
    setLoading(false);
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) resetForm();
    onOpenChange(open);
  };

  const validate = (): string | null => {
    if (!oldPassword.trim() || !newPassword.trim() || !confirmPassword.trim()) {
      return "Todos los campos son requeridos";
    }
    if (newPassword.length < 6) {
      return "La contraseña debe tener al menos 6 caracteres";
    }
    if (newPassword !== confirmPassword) {
      return "Las contraseñas nuevas no coinciden";
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/auth/api/cambiar-contrasena", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      const data = await res.json();

      if (data.status === "success") {
        setSuccess("Contraseña cambiada exitosamente");
        setTimeout(() => {
          handleOpenChange(false);
        }, 1200);
      } else {
        setError(data.errors?.[0] || "Error al cambiar la contraseña");
      }
    } catch {
      setError("Error de conexión al servidor");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={handleOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in data-[state=closed]:animate-out" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-lg data-[state=open]:animate-in data-[state=closed]:animate-out">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              <Dialog.Title className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                Cambiar Contraseña
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button className="p-1 rounded-md hover:bg-gray-100 transition-colors">
                <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              </button>
            </Dialog.Close>
          </div>

          {success && (
            <div className="mb-4 rounded-lg border px-4 py-3 text-sm"
                 style={{ borderColor: "oklch(0.5 0.15 145 / 0.3)", background: "oklch(0.9 0.1 145 / 0.2)", color: "oklch(0.4 0.15 145)" }}>
              {success}
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-lg border px-4 py-3 text-sm"
                 style={{ borderColor: "oklch(0.6 0.2 25 / 0.3)", background: "oklch(0.9 0.1 25 / 0.2)", color: "oklch(0.5 0.2 25)" }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="space-y-4 mb-6">
              {/* Old password */}
              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Contraseña actual
                </label>
                <div className="relative">
                  <input
                    type={showPassword.old ? "text" : "password"}
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    className="w-full rounded-lg border px-4 py-2.5 pr-10 text-sm outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                    disabled={loading}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => toggleVisibility("old")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md hover:bg-gray-100 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword.old ? <EyeOff className="h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} /> : <Eye className="h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} />}
                  </button>
                </div>
              </div>

              {/* New password */}
              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Nueva contraseña
                </label>
                <div className="relative">
                  <input
                    type={showPassword.new ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full rounded-lg border px-4 py-2.5 pr-10 text-sm outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                    disabled={loading}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => toggleVisibility("new")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md hover:bg-gray-100 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword.new ? <EyeOff className="h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} /> : <Eye className="h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} />}
                  </button>
                </div>
              </div>

              {/* Confirm password */}
              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Confirmar nueva contraseña
                </label>
                <div className="relative">
                  <input
                    type={showPassword.confirm ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full rounded-lg border px-4 py-2.5 pr-10 text-sm outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                    disabled={loading}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => toggleVisibility("confirm")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md hover:bg-gray-100 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword.confirm ? <EyeOff className="h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} /> : <Eye className="h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} />}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <Dialog.Close asChild>
                <Button type="button" variant="secondary" disabled={loading}>
                  Cancelar
                </Button>
              </Dialog.Close>
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Cambiando...
                  </>
                ) : (
                  "Cambiar"
                )}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
