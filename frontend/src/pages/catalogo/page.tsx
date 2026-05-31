import { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  X,
  Eye,
  Loader2,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageTitle } from "@/components/status-badge";
import {
  type EpsContratado,
  type ProcedimientoSqlite,
  type EpsProcedimientosChain,
  type NotaHoja,
  fetchEps,
  fetchProcSqlite,
  fetchProcedimientosPorEps,
  fetchNotasHoja,
  createEps,
  updateEps,
  deleteEps,
  createProcSqlite,
  updateProcSqlite,
  deleteProcSqlite,
  createNotaHoja,
  updateNotaHoja,
  deleteNotaHoja,
  fetchNotaHojaDependencias,
  type VinculacionesNota,
  fetchVinculacionesNota,
  vincularProcedimientoANota,
  vincularEpsANota,
  deleteEpsNota,
  updateNotasTecnicas,
  deleteNotasTecnicas,
} from "@/lib/api-catalogo";

// ─── Types ──────────────────────────────────────────────────────────

type TabId = "eps" | "procedimientos" | "notas-hoja";

interface Tab {
  id: TabId;
  label: string;
}

const TABS: Tab[] = [
  { id: "eps", label: "EPS Contratadas" },
  { id: "procedimientos", label: "Procedimientos CUPS" },
  { id: "notas-hoja", label: "Notas Hoja" },
];

// ─── Modal helpers ──────────────────────────────────────────────────

interface ModalState<T> {
  open: boolean;
  mode: "create" | "edit";
  item: T | null;
}

function initialModal<T>(): ModalState<T> {
  return { open: false, mode: "create", item: null };
}

// ─── Main component ─────────────────────────────────────────────────

export function CatalogoPage() {
  const [activeTab, setActiveTab] = useState<TabId>("eps");

  return (
    <div className="mx-auto max-w-7xl">
      <PageTitle
        title="Catálogos"
        description="Gestión de EPS contratadas, procedimientos CUPS y notas hoja."
      />

      {/* Tab selector */}
      <div className="mb-6 flex gap-1 border-b border-border" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px"
            style={{
              borderColor: activeTab === tab.id ? "var(--color-primary)" : "transparent",
              color: activeTab === tab.id ? "var(--color-primary)" : "var(--color-muted-foreground)",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      {activeTab === "eps" && <EpsTab />}
      {activeTab === "procedimientos" && <ProcedimientosTab />}
      {activeTab === "notas-hoja" && <NotaHojaTab />}
    </div>
  );
}

// ─── EPS Tab ────────────────────────────────────────────────────────

function EpsTab() {
  const [items, setItems] = useState<EpsContratado[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState<EpsContratado>>(initialModal);
  const [chainView, setChainView] = useState<EpsProcedimientosChain | null>(null);

  // Form state
  const [formCodContrato, setFormCodContrato] = useState("");
  const [formEps, setFormEps] = useState("");
  const [formRegimen, setFormRegimen] = useState("SUBSIDIADO");
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEps();
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar EPS");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setModal({ open: true, mode: "create", item: null });
    setFormCodContrato("");
    setFormEps("");
    setFormRegimen("SUBSIDIADO");
    setFormError(null);
  };

  const openEdit = (item: EpsContratado) => {
    setModal({ open: true, mode: "edit", item });
    setFormCodContrato(item.cod_contrato);
    setFormEps(item.eps);
    setFormRegimen(item.regimen);
    setFormError(null);
  };

  const closeModal = () => {
    setModal(initialModal);
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      if (modal.mode === "create") {
        await createEps({ cod_contrato: formCodContrato, eps: formEps, regimen: formRegimen });
      } else if (modal.item) {
        await updateEps(modal.item.id, {
          cod_contrato: formCodContrato,
          eps: formEps,
          regimen: formRegimen,
        });
      }
      closeModal();
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error al guardar");
    }
  };

  const handleDelete = async (item: EpsContratado) => {
    if (!window.__showConfirm) return;
    const ok = await window.__showConfirm(`¿Eliminar EPS ${item.eps} (${item.cod_contrato})?`);
    if (!ok) return;
    try {
      await deleteEps(item.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    }
  };

  const handleViewProcedimientos = async (item: EpsContratado) => {
    setChainView(null);
    try {
      const data = await fetchProcedimientosPorEps(item.id);
      setChainView(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar datos");
    }
  };

  const closeChainView = () => {
    setChainView(null);
  };

  if (loading) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        <span className="text-sm text-muted-foreground">Cargando EPS contratadas...</span>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <p className="text-sm text-danger mb-2">{error}</p>
        <Button size="sm" onClick={load}>Reintentar</Button>
      </Card>
    );
  }

  return (
    <>
      <Card className="p-6 border shadow-none" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
            EPS Contratadas
          </h2>
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-3.5 w-3.5" />
            Nueva EPS
          </Button>
        </div>

        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">No hay EPS contratadas</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                  <th className="py-3 px-4 text-left">Cód. Contrato</th>
                  <th className="py-3 px-4 text-left">EPS</th>
                  <th className="py-3 px-4 text-left">Régimen</th>
                  <th className="py-3 px-4 text-left">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                    <td className="py-3 px-4 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{item.cod_contrato}</td>
                    <td className="py-3 px-4" style={{ color: "oklch(0.55 0.04 160)" }}>{item.eps}</td>
                    <td className="py-3 px-4">{item.regimen}</td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <Button size="sm" variant="default" onClick={() => openEdit(item)}>
                          <Pencil className="h-3.5 w-3.5" />
                          Editar
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => handleViewProcedimientos(item)}>
                          <Eye className="h-3.5 w-3.5" />
                          Ver Procedimientos
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(item)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Chain view overlay */}
      {chainView && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={(e) => { if (e.target === e.currentTarget) closeChainView(); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                Procedimientos vinculados — {chainView.eps.eps}
              </h2>
              <button onClick={closeChainView} className="p-1 rounded-md hover:bg-gray-100">
                <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              </button>
            </div>

            {chainView.procedimientos.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">Sin procedimientos vinculados</p>
            ) : (
              <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                      <th className="py-3 px-4 text-left">CUPS</th>
                      <th className="py-3 px-4 text-left">Procedimiento</th>
                      <th className="py-3 px-4 text-left">Tarifa</th>
                    </tr>
                  </thead>
                  <tbody>
                    {chainView.procedimientos.map((p, i) => (
                      <tr key={i} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                        <td className="py-3 px-4 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{p.cups}</td>
                        <td className="py-3 px-4" style={{ color: "oklch(0.55 0.04 160)" }}>{p.procedimiento}</td>
                        <td className="py-3 px-4">${p.tarifa.toLocaleString("es-CO")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end mt-4">
              <Button variant="secondary" onClick={closeChainView}>Cerrar</Button>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {modal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                {modal.mode === "create" ? "Nueva EPS" : "Editar EPS"}
              </h2>
              <button onClick={closeModal} className="p-1 rounded-md hover:bg-gray-100">
                <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              {formError && (
                <p className="text-xs mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{formError}</p>
              )}
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Código Contrato
              </label>
              <input
                type="text"
                value={formCodContrato}
                onChange={(e) => setFormCodContrato(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                required
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                EPS
              </label>
              <input
                type="text"
                value={formEps}
                onChange={(e) => setFormEps(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                required
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Régimen
              </label>
              <select
                value={formRegimen}
                onChange={(e) => setFormRegimen(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-6 outline-none"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              >
                <option value="SUBSIDIADO">Subsidiado</option>
                <option value="CONTRIBUTIVO">Contributivo</option>
              </select>

              <div className="flex gap-2 justify-end">
                <Button type="submit">{modal.mode === "create" ? "Crear" : "Guardar"}</Button>
                <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

// ─── Procedimientos CUPS Tab ─────────────────────────────────────────

function ProcedimientosTab() {
  const [items, setItems] = useState<ProcedimientoSqlite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState<ProcedimientoSqlite>>(initialModal);

  const [formCups, setFormCups] = useState("");
  const [formProcedimiento, setFormProcedimiento] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProcSqlite();
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar procedimientos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setModal({ open: true, mode: "create", item: null });
    setFormCups("");
    setFormProcedimiento("");
    setFormError(null);
  };

  const openEdit = (item: ProcedimientoSqlite) => {
    setModal({ open: true, mode: "edit", item });
    setFormCups(item.cups);
    setFormProcedimiento(item.procedimiento);
    setFormError(null);
  };

  const closeModal = () => {
    setModal(initialModal);
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      if (modal.mode === "create") {
        await createProcSqlite({ cups: formCups, procedimiento: formProcedimiento });
      } else if (modal.item) {
        await updateProcSqlite(modal.item.id, { cups: formCups, procedimiento: formProcedimiento });
      }
      closeModal();
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error al guardar");
    }
  };

  const handleDelete = async (item: ProcedimientoSqlite) => {
    if (!window.__showConfirm) return;
    const ok = await window.__showConfirm(`¿Eliminar procedimiento ${item.cups}?`);
    if (!ok) return;
    try {
      await deleteProcSqlite(item.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    }
  };

  if (loading) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        <span className="text-sm text-muted-foreground">Cargando procedimientos CUPS...</span>
      </Card>
    );
  }

  return (
    <Card className="p-6 border shadow-none" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
          Procedimientos CUPS
        </h2>
        <Button size="sm" onClick={openCreate}>
          <Plus className="h-3.5 w-3.5" />
          Nuevo Procedimiento
        </Button>
      </div>

      {error && (
        <div className="mb-4">
          <p className="text-sm text-danger mb-2">{error}</p>
          <Button size="sm" onClick={load}>Reintentar</Button>
        </div>
      )}

      {!error && items.length === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center">No hay procedimientos CUPS</p>
      ) : !error ? (
        <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                <th className="py-3 px-4 text-left">ID</th>
                <th className="py-3 px-4 text-left">CUPS</th>
                <th className="py-3 px-4 text-left">Procedimiento</th>
                <th className="py-3 px-4 text-left">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                  <td className="py-3 px-4" style={{ color: "oklch(0.55 0.04 160)" }}>{item.id}</td>
                  <td className="py-3 px-4 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{item.cups}</td>
                  <td className="py-3 px-4" style={{ color: "oklch(0.55 0.04 160)" }}>{item.procedimiento}</td>
                  <td className="py-3 px-4">
                    <div className="flex gap-2">
                      <Button size="sm" variant="default" onClick={() => openEdit(item)}>
                        <Pencil className="h-3.5 w-3.5" />
                        Editar
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleDelete(item)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* Create/Edit Modal */}
      {modal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                {modal.mode === "create" ? "Nuevo Procedimiento CUPS" : "Editar Procedimiento CUPS"}
              </h2>
              <button onClick={closeModal} className="p-1 rounded-md hover:bg-gray-100">
                <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              {formError && (
                <p className="text-xs mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{formError}</p>
              )}
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                CUPS
              </label>
              <input
                type="text"
                value={formCups}
                onChange={(e) => setFormCups(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                required
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Procedimiento
              </label>
              <input
                type="text"
                value={formProcedimiento}
                onChange={(e) => setFormProcedimiento(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-6 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                required
              />

              <div className="flex gap-2 justify-end">
                <Button type="submit">{modal.mode === "create" ? "Crear" : "Guardar"}</Button>
                <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Card>
  );
}

// ─── Notas Hoja Tab ──────────────────────────────────────────────────

function NotaHojaTab() {
  const [items, setItems] = useState<NotaHoja[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState<NotaHoja>>(initialModal);

  const [formNota, setFormNota] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  // Vinculaciones state
  const [vinculaciones, setVinculaciones] = useState<VinculacionesNota | null>(null);
  const [vincEpsList, setVincEpsList] = useState<EpsContratado[]>([]);
  const [vincProcList, setVincProcList] = useState<ProcedimientoSqlite[]>([]);
  const [vincFormProc, setVincFormProc] = useState("");
  const [vincSearchProc, setVincSearchProc] = useState("");
  const [vincFormEps, setVincFormEps] = useState("");
  const [vincFormTarifa, setVincFormTarifa] = useState("");
  const [vincFormError, setVincFormError] = useState<string | null>(null);
  const [vincFormLoading, setVincFormLoading] = useState(false);

  // Edit tarifa
  const [editandoTarifa, setEditandoTarifa] = useState<{ nt_id: number; tarifa: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchNotasHoja();
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar notas hoja");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setModal({ open: true, mode: "create", item: null });
    setFormNota("");
    setFormError(null);
  };

  const openEdit = (item: NotaHoja) => {
    setModal({ open: true, mode: "edit", item });
    setFormNota(item.nota);
    setFormError(null);
  };

  const closeModal = () => {
    setModal(initialModal);
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!formNota.trim()) {
      setFormError("La nota no puede estar vacía");
      return;
    }
    try {
      if (modal.mode === "create") {
        await createNotaHoja({ nota: formNota.trim() });
      } else if (modal.item) {
        await updateNotaHoja(modal.item.id, { nota: formNota.trim() });
      }
      closeModal();
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error al guardar");
    }
  };

  const handleDelete = async (item: NotaHoja) => {
    if (!window.__showConfirm) return;
    let mensaje = `¿Eliminar nota hoja "${item.nota}"?`;
    try {
      const deps = await fetchNotaHojaDependencias(item.id);
      const partes: string[] = [];
      if (deps.eps_nota_count > 0) {
        const epsNombres = deps.eps_vinculadas.map(e => e.eps).join(", ");
        partes.push(`${deps.eps_nota_count} EPS vinculada(s): ${epsNombres}`);
      }
      if (deps.notas_tecnicas_count > 0) {
        const procCups = deps.procedimientos_vinculados.map(p => p.cups).join(", ");
        partes.push(`${deps.notas_tecnicas_count} procedimiento(s): ${procCups}`);
      }
      if (partes.length > 0) {
        mensaje += `\n\n⚠️ Se eliminarán también:\n${partes.join("\n")}`;
      }
    } catch {
      mensaje += `\n\n(No se pudieron consultar dependencias)`;
    }
    const ok = await window.__showConfirm(mensaje);
    if (!ok) return;
    try {
      await deleteNotaHoja(item.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    }
  };

  // ─── Vinculaciones ────────────────────────────────────────────────

  const handleVerVinculaciones = async (item: NotaHoja) => {
    setVinculaciones(null);
    setVincFormError(null);
    try {
      const [data, epsItems, procItems] = await Promise.all([
        fetchVinculacionesNota(item.id),
        fetchEps(),
        fetchProcSqlite(),
      ]);
      setVinculaciones(data);
      setVincEpsList(epsItems);
      setVincProcList(procItems);
      setVincFormProc("");
      setVincFormEps("");
      setVincFormTarifa("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar vinculaciones");
    }
  };

  const handleVincular = async (e: React.FormEvent) => {
    e.preventDefault();
    setVincFormError(null);
    if (!vinculaciones) return;
    if (!vincFormProc) {
      setVincFormError("Seleccioná un procedimiento");
      return;
    }
    setVincFormLoading(true);
    try {
      await vincularProcedimientoANota(vinculaciones.nota.id, {
        id_procedimiento: Number(vincFormProc),
        tarifa: vincFormTarifa ? Number(vincFormTarifa) : undefined,
      });
      await handleVerVinculaciones(vinculaciones.nota);
    } catch (err) {
      setVincFormError(err instanceof Error ? err.message : "Error al vincular");
    } finally {
      setVincFormLoading(false);
    }
  };

  const handleVincularEps = async () => {
    if (!vinculaciones || !vincFormEps) return;
    try {
      await vincularEpsANota(vinculaciones.nota.id, { id_eps_contratado: Number(vincFormEps) });
      setVincFormEps("");
      await handleVerVinculaciones(vinculaciones.nota);
    } catch (err) {
      setVincFormError(err instanceof Error ? err.message : "Error al vincular EPS");
    }
  };

  const handleEliminarEpsVinculacion = async (epsNotaId: number | undefined, epsNombre: string) => {
    if (!window.__showConfirm || !vinculaciones || !epsNotaId) return;
    const ok = await window.__showConfirm(`¿Desvincular EPS ${epsNombre} de "${vinculaciones.nota.nota}"?`);
    if (!ok) return;
    try {
      await deleteEpsNota(epsNotaId);
      await handleVerVinculaciones(vinculaciones.nota);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar vinculación");
    }
  };

  const handleEditarTarifa = async (nt_id: number) => {
    if (!editandoTarifa || !vinculaciones) return;
    try {
      await updateNotasTecnicas(nt_id, { tariff: Number(editandoTarifa.tarifa) });
      setEditandoTarifa(null);
      await handleVerVinculaciones(vinculaciones.nota);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al actualizar tarifa");
    }
  };

  const handleEliminarVinculacion = async (nt_id: number, cups: string) => {
    if (!window.__showConfirm || !vinculaciones) return;
    const ok = await window.__showConfirm(`¿Desvincular procedimiento ${cups} de "${vinculaciones.nota.nota}"?`);
    if (!ok) return;
    try {
      await deleteNotasTecnicas(nt_id);
      await handleVerVinculaciones(vinculaciones.nota);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar vinculación");
    }
  };

  if (loading) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        <span className="text-sm text-muted-foreground">Cargando notas hoja...</span>
      </Card>
    );
  }

  return (
    <>
      <Card className="p-6 border shadow-none" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
            Notas Hoja
          </h2>
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-3.5 w-3.5" />
            Nueva Nota Hoja
          </Button>
        </div>

        {error && (
          <div className="mb-4">
            <p className="text-sm text-danger mb-2">{error}</p>
            <Button size="sm" onClick={load}>Reintentar</Button>
          </div>
        )}

        {!error && items.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">No hay notas hoja</p>
        ) : !error ? (
          <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                  <th className="py-3 px-4 text-left">ID</th>
                  <th className="py-3 px-4 text-left">Nota</th>
                  <th className="py-3 px-4 text-left">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                    <td className="py-3 px-4" style={{ color: "oklch(0.55 0.04 160)" }}>{item.id}</td>
                    <td className="py-3 px-4 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{item.nota}</td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <Button size="sm" variant="default" onClick={() => openEdit(item)}>
                          <Pencil className="h-3.5 w-3.5" />
                          Editar
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => handleVerVinculaciones(item)}>
                          <Eye className="h-3.5 w-3.5" />
                          Ver Vinculaciones
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(item)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {/* Create/Edit Modal */}
        {modal.open && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
               onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
            <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                  {modal.mode === "create" ? "Nueva Nota Hoja" : "Editar Nota Hoja"}
                </h2>
                <button onClick={closeModal} className="p-1 rounded-md hover:bg-gray-100">
                  <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
                </button>
              </div>
              <form onSubmit={handleSubmit}>
                {formError && (<p className="text-xs mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{formError}</p>)}
                <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Nota</label>
                <input type="text" value={formNota} onChange={(e) => setFormNota(e.target.value)}
                  className="w-full rounded-lg border px-4 py-2.5 text-sm mb-6 outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} required />
                <div className="flex gap-2 justify-end">
                  <Button type="submit">{modal.mode === "create" ? "Crear" : "Guardar"}</Button>
                  <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </Card>

      {/* Vinculaciones Modal */}
      {vinculaciones && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={(e) => { if (e.target === e.currentTarget) setVinculaciones(null); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-3xl mx-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                Vinculaciones — {vinculaciones.nota.nota}
              </h2>
              <button onClick={() => setVinculaciones(null)} className="p-1 rounded-md hover:bg-gray-100">
                <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              </button>
            </div>

            {/* EPS vinculadas */}
            <div className="mb-4">
              <h3 className="text-sm font-semibold mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>
                EPS Vinculadas ({vinculaciones.eps_vinculadas.length})
              </h3>
              {vinculaciones.eps_vinculadas.length === 0 ? (
                <p className="text-xs text-muted-foreground">Sin EPS vinculadas</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {vinculaciones.eps_vinculadas.map((e) => (
                    <span key={e.id} className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full"
                      style={{ background: "oklch(0.55 0.04 160 / 0.08)", color: "oklch(0.55 0.04 160)" }}>
                      {e.eps} ({e.cod_contrato})
                      <button onClick={() => handleEliminarEpsVinculacion(e.eps_nota_id, e.eps)}
                        className="ml-1 hover:text-danger" title="Desvincular">×</button>
                    </span>
                  ))}
                </div>
              )}
              {/* Vincular EPS */}
              <div className="flex gap-2 mt-2">
                <select value={vincFormEps}
                  onChange={(e) => setVincFormEps(e.target.value)}
                  className="rounded-lg border px-3 py-1.5 text-xs outline-none"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
                  <option value="">-- Vincular EPS --</option>
                  {vincEpsList.map((e) => (
                    <option key={e.id} value={e.id}>{e.eps} ({e.cod_contrato})</option>
                  ))}
                </select>
                <Button size="sm" onClick={handleVincularEps} disabled={!vincFormEps}>
                  <Plus className="h-3 w-3" />
                </Button>
              </div>
            </div>

            {/* Procedimientos vinculados */}
            <h3 className="text-sm font-semibold mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>
              Procedimientos ({vinculaciones.procedimientos.length})
            </h3>
            {vinculaciones.procedimientos.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">Sin procedimientos vinculados</p>
            ) : (
              <div className="overflow-x-auto rounded-lg border mb-4" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                      <th className="py-2 px-3 text-left">CUPS</th>
                      <th className="py-2 px-3 text-left">Procedimiento</th>
                      <th className="py-2 px-3 text-left">Tarifa</th>
                      <th className="py-2 px-3 text-left">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vinculaciones.procedimientos.map((p) => (
                      <tr key={p.nt_id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                        <td className="py-2 px-3 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{p.cups}</td>
                        <td className="py-2 px-3" style={{ color: "oklch(0.55 0.04 160)" }}>{p.procedimiento}</td>
                        <td className="py-2 px-3">
                          {editandoTarifa?.nt_id === p.nt_id ? (
                            <div className="flex gap-1">
                              <input type="number" step="0.01" value={editandoTarifa.tarifa}
                                onChange={(e) => setEditandoTarifa({ nt_id: p.nt_id, tarifa: e.target.value })}
                                className="w-24 rounded border px-2 py-1 text-xs outline-none"
                                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />
                              <Button size="sm" onClick={() => handleEditarTarifa(p.nt_id)}>OK</Button>
                              <Button size="sm" variant="secondary" onClick={() => setEditandoTarifa(null)}>X</Button>
                            </div>
                          ) : (
                            <span>${p.tarifa?.toLocaleString("es-CO") ?? "—"}</span>
                          )}
                        </td>
                        <td className="py-2 px-3">
                          <div className="flex gap-1">
                            <Button size="sm" variant="default"
                              onClick={() => setEditandoTarifa({ nt_id: p.nt_id, tarifa: p.tarifa?.toString() ?? "" })}>
                              Editar
                            </Button>
                            <Button size="sm" variant="destructive"
                              onClick={() => handleEliminarVinculacion(p.nt_id, p.cups)}>
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Vincular nuevo procedimiento */}
            <div className="border-t pt-4" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
              <h3 className="text-sm font-semibold mb-3" style={{ color: "oklch(0.55 0.04 160)" }}>
                Vincular nuevo procedimiento
              </h3>
              <form onSubmit={handleVincular} className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {vincFormError && (
                  <p className="col-span-full text-xs" style={{ color: "oklch(0.6 0.2 25)" }}>{vincFormError}</p>
                )}
                <div>
                  <label className="block text-xs mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Procedimiento</label>
                  <input type="text" placeholder="Buscar por CUPS o nombre..."
                    value={vincSearchProc}
                    onChange={(e) => { setVincSearchProc(e.target.value); setVincFormProc(""); }}
                    className="w-full rounded-lg border px-3 py-2 text-sm mb-1 outline-none"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />
                  <select value={vincFormProc}
                    onChange={(e) => setVincFormProc(e.target.value)}
                    size={5}
                    className="w-full rounded-lg border px-2 py-1 text-sm outline-none"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
                    <option value="">-- Seleccionar --</option>
                    {vincProcList
                      .filter((p) =>
                        !vincSearchProc ||
                        p.cups.toLowerCase().includes(vincSearchProc.toLowerCase()) ||
                        (p.procedimiento ?? "").toLowerCase().includes(vincSearchProc.toLowerCase())
                      )
                      .map((p) => (
                        <option key={p.id} value={p.id}>{p.cups} — {p.procedimiento}</option>
                      ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Tarifa</label>
                  <input type="number" step="0.01" value={vincFormTarifa}
                    onChange={(e) => setVincFormTarifa(e.target.value)}
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />
                </div>
                <div className="flex items-end">
                  <Button type="submit" disabled={vincFormLoading}>
                    {vincFormLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Plus className="h-3 w-3 mr-1" />}
                    Vincular
                  </Button>
                </div>
              </form>
            </div>

            <div className="flex justify-end mt-4">
              <Button variant="secondary" onClick={() => setVinculaciones(null)}>Cerrar</Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
