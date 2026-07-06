import { useState, useEffect } from "react";
import {
  Users,
  UserPlus,
  Pencil,
  Trash2,
  X,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";

interface Usuario {
  username: string;
  rol: string;
  permisos: string[];
  primer_nombre: string;
  segundo_nombre: string;
  apellido_1: string;
  apellido_2: string;
}

interface Template {
  nombre: string;
  descripcion: string;
  permisos: string[];
}

interface UsuariosData {
  usuarios: Usuario[];
  session_username: string;
  templates?: Template[];
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
  { value: "equipos_basicos", label: "Ordenado y Facturado" },
  { value: "odontologia_equipos_basicos", label: "Equipos Básicos" },
  { value: "derechos", label: "Derechos" },
  { value: "monitoreo_carpetas", label: "Monitoreo de Carpetas" },
  { value: "monitoreo_carpetas:write", label: "Monitoreo de Carpetas (configurar rutas)" },
];

// Pares mutuamente excluyentes: si se marca uno, se desmarca el otro
const PERMISO_PAIRS: Record<string, string> = {
  "control_urgencias": "control_urgencias:write",
  "control_urgencias:write": "control_urgencias",
  "facturas_abiertas": "facturas_abiertas:write",
  "facturas_abiertas:write": "facturas_abiertas",
  "monitoreo_carpetas": "monitoreo_carpetas:write",
  "monitoreo_carpetas:write": "monitoreo_carpetas",
};

type ModalMode = "edit" | null;

export function UsuariosPage() {
  const [usuarios, _setUsuarios] = useState<Usuario[]>(initialData?.usuarios ?? []);
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [_editUser, setEditUser] = useState<Usuario | null>(null);

  // Form state
  const [formUsername, setFormUsername] = useState("");
  const [formPassword, setFormPassword] = useState("");
  const [formRol, setFormRol] = useState("usuario");
  const [formPermisos, setFormPermisos] = useState<string[]>([]);

  // Person name fields
  const [formPrimerNombre, setFormPrimerNombre] = useState("");
  const [formSegundoNombre, setFormSegundoNombre] = useState("");
  const [formApellido1, setFormApellido1] = useState("");
  const [formApellido2, setFormApellido2] = useState("");

  // Validation errors
  interface FormErrors {
    username?: string;
    password?: string;
    primer_nombre?: string;
    apellido_1?: string;
    permisos?: string;
  }
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const clearError = (field: keyof FormErrors) => {
    setFormErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const validateCreate = (): FormErrors => {
    const errors: FormErrors = {};
    if (!formUsername.trim()) errors.username = "El usuario es obligatorio";
    if (!formPassword.trim()) errors.password = "La contraseña es obligatoria";
    if (!formPrimerNombre.trim()) errors.primer_nombre = "El primer nombre es obligatorio";
    if (!formApellido1.trim()) errors.apellido_1 = "El apellido 1 es obligatorio";
    if (formRol !== "admin" && formPermisos.length === 0) errors.permisos = "Seleccioná al menos un permiso";
    return errors;
  };

  // Template state
  const [templates, setTemplates] = useState<Template[]>(initialData?.templates ?? []);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");

  const openEdit = (user: Usuario) => {
    setModalMode("edit");
    setEditUser(user);
    setFormUsername(user.username);
    setFormPassword("");
    setFormRol(user.rol);
    setFormPrimerNombre(user.primer_nombre ?? "");
    setFormSegundoNombre(user.segundo_nombre ?? "");
    setFormApellido1(user.apellido_1 ?? "");
    setFormApellido2(user.apellido_2 ?? "");
    // Limpiar datos legacy: si vienen ambos del par, dar prioridad al de escritura
    const cleaned = user.permisos.filter((p) => {
      const conflict = PERMISO_PAIRS[p];
      return !(conflict && user.permisos.includes(conflict) && conflict < p);
    });
    setFormPermisos(cleaned);
    setFormErrors({});
  };

  const closeModal = () => {
    setModalMode(null);
    setEditUser(null);
    setFormErrors({});
  };

  // Fetch templates on mount if not already in initial_data
  useEffect(() => {
    if (templates.length === 0) {
      fetch("/auth/api/templates")
        .then((res) => res.json())
        .then((data) => {
          if (data.status === "success") {
            setTemplates(data.data.templates);
          }
        })
        .catch(() => {
          // Silently fail — templates are optional for the UI
        });
    }
  }, [templates.length]);

  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setSelectedTemplate(value);
    if (!value) {
      setFormPermisos([]);
    } else {
      const tmpl = templates.find((t) => t.nombre === value);
      if (tmpl) {
        // Limpiar pares conflictivos (write tiene prioridad sobre read)
        const cleaned = tmpl.permisos.filter((p) => {
          const conflict = PERMISO_PAIRS[p];
          return !(conflict && tmpl.permisos.includes(conflict) && conflict < p);
        });
        setFormPermisos(cleaned);
      }
    }
  };

  const togglePermiso = (value: string) => {
    setFormPermisos((prev) => {
      // Si está desmarcando, solo lo saca
      if (prev.includes(value)) {
        return prev.filter((p) => p !== value);
      }
      // Si está marcando, saca el conflicto si existe
      const conflict = PERMISO_PAIRS[value];
      if (conflict && prev.includes(conflict)) {
        return [...prev.filter((p) => p !== conflict), value];
      }
      return [...prev, value];
    });
  };

  const handleDelete = async (username: string) => {
    if (!(await window.__showConfirm!(`¿Eliminar usuario ${username}? Esta acción no se puede deshacer.`))) return;

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
    setFormErrors({});

    const isEdit = modalMode === "edit";

    // Solo validar en creación
    if (!isEdit) {
      const errors = validateCreate();
      if (Object.keys(errors).length > 0) {
        setFormErrors(errors);
        return;
      }
    }

    const action = isEdit
      ? `/auth/usuarios/${encodeURIComponent(formUsername)}/editar`
      : "/auth/usuarios/crear";

    const form = new FormData();
    form.append("username", formUsername);
    if (formPassword) form.append("password", formPassword);
    form.append("rol", formRol);
    formPermisos.forEach((p) => form.append("permisos", p));
    form.append("primer_nombre", formPrimerNombre);
    form.append("segundo_nombre", formSegundoNombre);
    form.append("apellido_1", formApellido1);
    form.append("apellido_2", formApellido2);

    const res = await fetch(action, { method: "POST", body: form });

    if (res.redirected) {
      window.location.reload();
    }
  };

  return (
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
        </div>

        {/* Create user card */}
        <Card className="p-6 border mb-6 shadow-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
          <h2 className="font-display font-semibold mb-4" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
            Crear nuevo usuario
          </h2>
          <form onSubmit={handleSubmit}>
            <div className="flex gap-4 mb-4">
              <div className="flex-1">
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Usuario
                </label>
                <input
                  type="text"
                  value={formUsername}
                  onChange={(e) => { setFormUsername(e.target.value); clearError("username"); }}
                  className={`w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary ${formErrors.username ? "border-red-500" : ""}`}
                  style={{ borderColor: formErrors.username ? "oklch(0.6 0.2 25)" : "oklch(0.55 0.04 160 / 0.2)" }}
                />
                {formErrors.username && (
                  <p className="text-xs mt-1" style={{ color: "oklch(0.6 0.2 25)" }}>{formErrors.username}</p>
                )}
              </div>
              <div className="flex-1">
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Contraseña
                </label>
                <input
                  type="password"
                  value={formPassword}
                  onChange={(e) => { setFormPassword(e.target.value); clearError("password"); }}
                  className={`w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary ${formErrors.password ? "border-red-500" : ""}`}
                  style={{ borderColor: formErrors.password ? "oklch(0.6 0.2 25)" : "oklch(0.55 0.04 160 / 0.2)" }}
                />
                {formErrors.password && (
                  <p className="text-xs mt-1" style={{ color: "oklch(0.6 0.2 25)" }}>{formErrors.password}</p>
                )}
              </div>
            </div>
            {/* Person name fields */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Primer Nombre
                </label>
                <input
                  type="text"
                  value={formPrimerNombre}
                  onChange={(e) => { setFormPrimerNombre(e.target.value); clearError("primer_nombre"); }}
                  className={`w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary ${formErrors.primer_nombre ? "border-red-500" : ""}`}
                  style={{ borderColor: formErrors.primer_nombre ? "oklch(0.6 0.2 25)" : "oklch(0.55 0.04 160 / 0.2)" }}
                />
                {formErrors.primer_nombre && (
                  <p className="text-xs mt-1" style={{ color: "oklch(0.6 0.2 25)" }}>{formErrors.primer_nombre}</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Segundo Nombre
                </label>
                <input
                  type="text"
                  value={formSegundoNombre}
                  onChange={(e) => setFormSegundoNombre(e.target.value)}
                  className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Apellido 1
                </label>
                <input
                  type="text"
                  value={formApellido1}
                  onChange={(e) => { setFormApellido1(e.target.value); clearError("apellido_1"); }}
                  className={`w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary ${formErrors.apellido_1 ? "border-red-500" : ""}`}
                  style={{ borderColor: formErrors.apellido_1 ? "oklch(0.6 0.2 25)" : "oklch(0.55 0.04 160 / 0.2)" }}
                />
                {formErrors.apellido_1 && (
                  <p className="text-xs mt-1" style={{ color: "oklch(0.6 0.2 25)" }}>{formErrors.apellido_1}</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Apellido 2
                </label>
                <input
                  type="text"
                  value={formApellido2}
                  onChange={(e) => setFormApellido2(e.target.value)}
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
                <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Basado en plantilla
                </label>
                <select
                  value={selectedTemplate}
                  onChange={handleTemplateChange}
                  className="rounded-lg border px-4 py-2.5 text-sm outline-none w-full max-w-xs mb-3"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                >
                  <option value="">-- Seleccionar --</option>
                  {templates.map((t) => (
                    <option key={t.nombre} value={t.nombre}>
                      {t.nombre.charAt(0).toUpperCase() + t.nombre.slice(1)}
                    </option>
                  ))}
                </select>
                <label className="block text-xs font-medium mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Permisos (seleccionar uno o más)
                </label>
                <div className="flex flex-wrap gap-3">
                  {ALL_PERMISOS.map((p) => (
                    <label key={p.value} className="flex items-center gap-1.5 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formPermisos.includes(p.value)}
                        onChange={() => { togglePermiso(p.value); clearError("permisos"); }}
                        className="accent-primary"
                      />
                      {p.label}
                    </label>
                  ))}
                </div>
                {formErrors.permisos && (
                  <p className="text-xs mt-2" style={{ color: "oklch(0.6 0.2 25)" }}>{formErrors.permisos}</p>
                )}
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
                  <th className="py-3 px-4 text-left">Nombre</th>
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
                    <td className="py-3 px-4 text-sm" style={{ color: "oklch(0.55 0.04 160)" }}>
                      {[user.primer_nombre, user.segundo_nombre, user.apellido_1, user.apellido_2]
                        .filter(Boolean).join(" ") || "—"}
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

      {/* Modal */}
      {modalMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                Editar Usuario
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
                readOnly
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)", background: "#f9fafb", cursor: "not-allowed" }}
                required
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Contraseña (dejar vacío para no cambiar)
              </label>
              <input
                type="password"
                value={formPassword}
                onChange={(e) => setFormPassword(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              />

              {/* Person name fields */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                    Primer Nombre
                  </label>
                  <input
                    type="text"
                    value={formPrimerNombre}
                    onChange={(e) => setFormPrimerNombre(e.target.value)}
                    className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                    Segundo Nombre
                  </label>
                  <input
                    type="text"
                    value={formSegundoNombre}
                    onChange={(e) => setFormSegundoNombre(e.target.value)}
                    className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                    Apellido 1
                  </label>
                  <input
                    type="text"
                    value={formApellido1}
                    onChange={(e) => setFormApellido1(e.target.value)}
                    className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                    Apellido 2
                  </label>
                  <input
                    type="text"
                    value={formApellido2}
                    onChange={(e) => setFormApellido2(e.target.value)}
                    className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                  />
                </div>
              </div>

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
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                    Basado en plantilla
                  </label>
                  <select
                    value={selectedTemplate}
                    onChange={handleTemplateChange}
                    className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                  >
                    <option value="">-- Seleccionar --</option>
                    {templates.map((t) => (
                      <option key={t.nombre} value={t.nombre}>
                        {t.nombre.charAt(0).toUpperCase() + t.nombre.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              )}
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
                  Guardar
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
