import { useState } from "react";
import {
  Users,
  UserPlus,
  Pencil,
  Trash2,
  ArrowLeft,
  X,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";

interface Usuario {
  username: string;
  rol: string;
  permisos: string[];
}

interface UsuariosData {
  usuarios: Usuario[];
  session_username: string;
}

const initialData = (window as unknown as { __INITIAL_DATA__?: UsuariosData }).__INITIAL_DATA__;

const ALL_PERMISOS = [
  { value: "odontologia", label: "Odontología" },
  { value: "urgencias", label: "Urgencias" },
  { value: "control_urgencias", label: "Control de Urgencias (lectura)" },
  { value: "control_urgencias:write", label: "Control de Urgencias (modificar)" },
  { value: "facturas_abiertas", label: "Facturas Abiertas (lectura)" },
  { value: "facturas_abiertas:write", label: "Facturas Abiertas (modificar)" },
  { value: "cruce_facturas", label: "Cruce de Reportes" },
  { value: "equipos_basicos", label: "Equipos Básicos" },
  { value: "derechos", label: "Derechos" },
];

type ModalMode = "create" | "edit" | null;

export function UsuariosPage() {
  const [usuarios, _setUsuarios] = useState<Usuario[]>(initialData?.usuarios ?? []);
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [_editUser, setEditUser] = useState<Usuario | null>(null);

  // Form state
  const [formUsername, setFormUsername] = useState("");
  const [formPassword, setFormPassword] = useState("");
  const [formRol, setFormRol] = useState("usuario");
  const [formPermisos, setFormPermisos] = useState<string[]>([]);

  const openCreate = () => {
    setModalMode("create");
    setFormUsername("");
    setFormPassword("");
    setFormRol("usuario");
    setFormPermisos([]);
    setEditUser(null);
  };

  const openEdit = (user: Usuario) => {
    setModalMode("edit");
    setEditUser(user);
    setFormUsername(user.username);
    setFormPassword("");
    setFormRol(user.rol);
    setFormPermisos(user.permisos);
  };

  const closeModal = () => {
    setModalMode(null);
    setEditUser(null);
  };

  const togglePermiso = (value: string) => {
    setFormPermisos((prev) =>
      prev.includes(value) ? prev.filter((p) => p !== value) : [...prev, value],
    );
  };

  const handleDelete = async (username: string) => {
    if (!confirm(`¿Eliminar usuario ${username}? Esta acción no se puede deshacer.`)) return;

    const form = new FormData();
    const res = await fetch(`/auth/usuarios/${encodeURIComponent(username)}/eliminar`, {
      method: "POST",
      body: form,
    });

    if (res.redirected) {
      window.location.reload();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const isEdit = modalMode === "edit";
    const action = isEdit
      ? `/auth/usuarios/${encodeURIComponent(formUsername)}/editar`
      : "/auth/usuarios/crear";

    const form = new FormData();
    form.append("username", formUsername);
    if (formPassword) form.append("password", formPassword);
    form.append("rol", formRol);
    formPermisos.forEach((p) => form.append("permisos", p));

    const res = await fetch(action, { method: "POST", body: form });

    if (res.redirected) {
      window.location.reload();
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "oklch(0.96 0.01 80)" }}>
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold font-heading tracking-tight" style={{ color: "oklch(0.15 0.02 160)" }}>
                Usuarios del Sistema
              </h1>
              <p className="text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>
                Administración de usuarios del sistema
              </p>
            </div>
          </div>
          <a
            href="/dashboard"
            className="flex items-center gap-1 text-xs font-medium transition-colors"
            style={{ color: "oklch(0.25 0.06 160)" }}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Volver al inicio
          </a>
        </div>

        {/* Create user card */}
        <Card className="p-6 border mb-6 shadow-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
          <h2 className="font-display font-semibold mb-4" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
            Crear nuevo usuario
          </h2>
          <form onSubmit={(e) => { e.preventDefault(); openCreate(); }}>
            <div className="flex gap-4 mb-4">
              <div className="flex-1">
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Usuario
                </label>
                <input
                  type="text"
                  value={formUsername}
                  onChange={(e) => setFormUsername(e.target.value)}
                  className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Contraseña
                </label>
                <input
                  type="password"
                  value={formPassword}
                  onChange={(e) => setFormPassword(e.target.value)}
                  className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                />
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Rol
              </label>
              <select
                value={formRol}
                onChange={(e) => setFormRol(e.target.value)}
                className="rounded-lg border px-4 py-2.5 text-sm outline-none w-full max-w-xs"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              >
                <option value="usuario">Usuario</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            {formRol !== "admin" && (
              <div className="mb-4">
                <label className="block text-xs font-medium mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Permisos (seleccionar uno o más)
                </label>
                <div className="flex flex-wrap gap-3">
                  {ALL_PERMISOS.map((p) => (
                    <label key={p.value} className="flex items-center gap-1.5 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formPermisos.includes(p.value)}
                        onChange={() => togglePermiso(p.value)}
                        className="accent-primary"
                      />
                      {p.label}
                    </label>
                  ))}
                </div>
              </div>
            )}
            <Button type="submit">
              <UserPlus className="h-4 w-4" />
              Crear usuario
            </Button>
          </form>
        </Card>

        {/* User list */}
        <Card className="p-6 border shadow-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
          <h2 className="font-display font-semibold mb-4" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
            Usuarios existentes
          </h2>
          <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider"
                    style={{ color: "oklch(0.55 0.04 160)" }}>
                  <th className="py-3 px-4 text-left">Usuario</th>
                  <th className="py-3 px-4 text-left">Rol</th>
                  <th className="py-3 px-4 text-left">Permisos</th>
                  <th className="py-3 px-4 text-left">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((user) => (
                  <tr key={user.username} className="border-b"
                      style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                    <td className="py-3 px-4 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>
                      {user.username}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge tone={user.rol === "admin" ? "success" : "info"}>
                        {user.rol}
                      </StatusBadge>
                    </td>
                    <td className="py-3 px-4">
                      {user.rol === "admin" ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                          TODOS
                        </span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {user.permisos.map((perm) => (
                            <span key={perm}
                                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                                  style={{ background: "oklch(0.55 0.04 160 / 0.1)", color: "oklch(0.55 0.04 160)" }}>
                              {perm}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <Button size="sm" variant="default" onClick={() => openEdit(user)}>
                          <Pencil className="h-3.5 w-3.5" />
                          Editar
                        </Button>
                        {user.username === "admin" ? (
                          <Button size="sm" variant="destructive" disabled
                                  title="No se puede eliminar el usuario admin">
                            <Trash2 className="h-3.5 w-3.5" />
                            Eliminar
                          </Button>
                        ) : (
                          <Button size="sm" variant="destructive"
                                  onClick={() => handleDelete(user.username)}>
                            <Trash2 className="h-3.5 w-3.5" />
                            Eliminar
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Modal */}
      {modalMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                {modalMode === "create" ? "Crear Usuario" : "Editar Usuario"}
              </h2>
              <button onClick={closeModal} className="p-1 rounded-md hover:bg-gray-100 transition-colors">
                <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Usuario
              </label>
              <input
                type="text"
                value={formUsername}
                onChange={(e) => setFormUsername(e.target.value)}
                readOnly={modalMode === "edit"}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)", ...(modalMode === "edit" ? { background: "#f9fafb", cursor: "not-allowed" } : {}) }}
                required
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Contraseña{modalMode === "edit" && " (dejar vacío para no cambiar)"}
              </label>
              <input
                type="password"
                value={formPassword}
                onChange={(e) => setFormPassword(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Rol
              </label>
              <select
                value={formRol}
                onChange={(e) => setFormRol(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              >
                <option value="usuario">Usuario</option>
                <option value="admin">Admin</option>
              </select>

              {formRol !== "admin" && (
                <fieldset className="mb-4">
                  <legend className="text-sm font-medium mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>
                    Permisos
                  </legend>
                  <div className="flex flex-wrap gap-3">
                    {ALL_PERMISOS.map((p) => (
                      <label key={p.value} className="flex items-center gap-1.5 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formPermisos.includes(p.value)}
                          onChange={() => togglePermiso(p.value)}
                          className="accent-primary"
                        />
                        {p.label}
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}

              <div className="flex gap-2 justify-end">
                <Button type="submit">
                  {modalMode === "create" ? "Crear" : "Guardar"}
                </Button>
                <Button type="button" variant="secondary" onClick={closeModal}>
                  Cancelar
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
