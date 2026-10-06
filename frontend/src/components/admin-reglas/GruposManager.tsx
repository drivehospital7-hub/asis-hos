/** CRUD modal for grupo_error labels (usage counts, rename, unassign).
 *
 * Groups are free-text labels on reglas, not entities: "delete" unassigns
 * (back to auto = rule name) and rename is a bulk update. Sistema groups
 * (custom formatter) are locked with an explanation instead of actions.
 */

import { useState } from "react";
import type { GrupoInfo } from "@/lib/api-reglas";
import { createGrupo, deleteGrupo, renameGrupo, unassignGrupo } from "@/lib/api-reglas";

interface GruposManagerProps {
  items: GrupoInfo[];
  loading: boolean;
  error: string | null;
  onChanged: () => void;
  onClose: () => void;
}

const inputClassName =
  "w-full rounded-lg border px-3 py-1.5 text-sm outline-none focus:border-primary";
const inputStyle = { borderColor: "oklch(0.55 0.04 160 / 0.2)" };

export function tipoBadgeClass(tipo: GrupoInfo["tipo"]): string {
  return tipo === "sistema"
    ? "bg-purple-100 text-purple-700"
    : tipo === "canonico"
      ? "bg-blue-100 text-blue-700"
      : "bg-gray-100 text-gray-600";
}

export function GruposTable({
  items,
  busy,
  onRename,
  onUnassign,
  onDelete,
}: {
  items: GrupoInfo[];
  busy: string | null;
  onRename: (anterior: string, nuevo: string) => void;
  onUnassign: (grupo: string) => void;
  onDelete: (grupo: string) => void;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-muted-foreground">
          <th className="py-2 pr-2">Grupo</th>
          <th className="py-2 pr-2">Tipo</th>
          <th className="py-2 pr-2 text-right">Reglas</th>
          <th className="py-2 pr-2 text-right">Activas</th>
          <th className="py-2 text-right">Acciones</th>
        </tr>
      </thead>
      <tbody>
        {items.map((g) => (
          <tr key={g.nombre} className="border-t">
            <td className="py-2 pr-2 font-medium">
              {editing === g.nombre ? (
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className={inputClassName}
                  style={inputStyle}
                  aria-label={`Nuevo nombre para ${g.nombre}`}
                />
              ) : (
                g.nombre
              )}
            </td>
            <td className="py-2 pr-2">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${tipoBadgeClass(g.tipo)}`}>
                {g.tipo}
              </span>
            </td>
            <td className="py-2 pr-2 text-right">{g.total_reglas}</td>
            <td className="py-2 pr-2 text-right">{g.reglas_activas}</td>
            <td className="py-2 text-right whitespace-nowrap">
              {g.tipo === "sistema" ? (
                <span className="text-xs text-muted-foreground" title="Formato propio: requiere cambio de código">
                  bloqueado
                </span>
              ) : editing === g.nombre ? (
                <>
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => { onRename(g.nombre, draft); setEditing(null); }}
                    className="text-xs underline mr-2"
                  >
                    Guardar
                  </button>
                  <button type="button" onClick={() => setEditing(null)} className="text-xs underline">
                    Cancelar
                  </button>
                </>
              ) : confirming === g.nombre ? (
                g.total_reglas === 0 ? (
                <>
                  <span className="text-xs mr-2">¿Quitar del catálogo?</span>
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => { onDelete(g.nombre); setConfirming(null); }}
                    className="text-xs underline mr-2"
                    style={{ color: "oklch(0.6 0.2 25)" }}
                  >
                    Sí
                  </button>
                  <button type="button" onClick={() => setConfirming(null)} className="text-xs underline">
                    No
                  </button>
                </>
                ) : (
                <>
                  <span className="text-xs mr-2">¿Desasignar de {g.total_reglas} regla(s)?</span>
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => { onUnassign(g.nombre); setConfirming(null); }}
                    className="text-xs underline mr-2"
                    style={{ color: "oklch(0.6 0.2 25)" }}
                  >
                    Sí
                  </button>
                  <button type="button" onClick={() => setConfirming(null)} className="text-xs underline">
                    No
                  </button>
                </>)
              ) : (
                <>
                  <button
                    type="button"
                    disabled={busy !== null}
                    title={g.total_reglas === 0 ? "Renombrar sugerencia sin uso" : "Renombrar en todas las reglas"}
                    onClick={() => { setEditing(g.nombre); setDraft(g.nombre); setConfirming(null); }}
                    className="text-xs underline mr-2 disabled:opacity-40"
                  >
                    Renombrar
                  </button>
                  <button
                    type="button"
                    disabled={busy !== null}
                    title={g.total_reglas === 0 ? "Quitar del catálogo" : "Volver a auto (nombre de regla)"}
                    onClick={() => { setConfirming(g.nombre); setEditing(null); }}
                    className="text-xs underline disabled:opacity-40"
                    style={{ color: "oklch(0.6 0.2 25)" }}
                  >
                    Eliminar
                  </button>
                </>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function GruposManager({ items, loading, error, onChanged, onClose }: GruposManagerProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setBusy("__new__");
    setActionError(null);
    try {
      await createGrupo(newName.trim());
      setNewName("");
      onChanged();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Error al crear");
    } finally {
      setBusy(null);
    }
  };

  const handleRename = async (anterior: string, nuevo: string) => {
    if (!nuevo.trim() || nuevo.trim() === anterior) return;
    setBusy(anterior);
    setActionError(null);
    try {
      await renameGrupo(anterior, nuevo.trim());
      onChanged();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Error al renombrar");
    } finally {
      setBusy(null);
    }
  };

  const handleUnassign = async (grupo: string) => {
    setBusy(grupo);
    setActionError(null);
    try {
      await unassignGrupo(grupo);
      onChanged();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Error al eliminar");
    } finally {
      setBusy(null);
    }
  };

  const handleDelete = async (grupo: string) => {
    setBusy(grupo);
    setActionError(null);
    try {
      await deleteGrupo(grupo);
      onChanged();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Error al quitar del catálogo");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.4)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-label="Gestionar grupos de error"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold" style={{ color: "oklch(0.15 0.02 160)" }}>
            Grupos de error
          </h3>
          <button type="button" onClick={onClose} className="p-1 rounded-md hover:bg-gray-100" aria-label="Cerrar">
            ✕
          </button>
        </div>
        <p className="text-xs text-muted-foreground mb-4">
          Los grupos son etiquetas: renombrar actualiza todas las reglas que la usan y
          eliminar la desasigna (vuelve a auto). Los de sistema tienen formato propio
          y están bloqueados. Crear un grupo nuevo se hace desde el editor de la regla.
        </p>
        {actionError && (
          <p className="text-xs mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{actionError}</p>
        )}
        <div className="flex gap-2 mb-4">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nuevo grupo…"
            aria-label="Nombre del nuevo grupo"
            className={inputClassName}
            style={inputStyle}
          />
          <button
            type="button"
            disabled={busy !== null || !newName.trim()}
            onClick={handleCreate}
            className="px-4 py-2 rounded-lg border text-sm font-medium whitespace-nowrap disabled:opacity-40"
            style={inputStyle}
          >
            Crear
          </button>
        </div>
        {loading ? (
          <p className="text-sm text-muted-foreground">Cargando...</p>
        ) : error ? (
          <p className="text-sm" style={{ color: "oklch(0.6 0.2 25)" }}>{error}</p>
        ) : (
          <GruposTable items={items} busy={busy} onRename={handleRename} onUnassign={handleUnassign} onDelete={handleDelete} />
        )}
      </div>
    </div>
  );
}
