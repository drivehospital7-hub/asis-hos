import { useState, useEffect, useCallback } from "react";
import {
  Building2,
  Stethoscope,
  DollarSign,
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
  type ProcedimientoPg,
  type EpsProcedimientosChain,
  fetchEps,
  fetchProcSqlite,
  fetchProcPg,
  fetchEpsDisponibles,
  fetchProcedimientosPorEps,
  createEps,
  updateEps,
  deleteEps,
  createProcSqlite,
  updateProcSqlite,
  deleteProcSqlite,
  createProcPg,
  updateProcPg,
  deleteProcPg,
} from "@/lib/api-catalogo";

// ─── Types ──────────────────────────────────────────────────────────

type TabId = "eps" | "procedimientos" | "tarifas";

interface Tab {
  id: TabId;
  label: string;
  source: string;
}

const TABS: Tab[] = [
  { id: "eps", label: "EPS Contratadas", source: "SQLite" },
  { id: "procedimientos", label: "Procedimientos CUPS", source: "SQLite" },
  { id: "tarifas", label: "Tarifas Procedimientos", source: "PostgreSQL" },
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
        description="Gestión de EPS contratadas, procedimientos CUPS y tarifas."
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
            {tab.label} <span className="text-xs opacity-60">({tab.source})</span>
          </button>
        ))}
      </div>

      {/* Tab panels */}
      {activeTab === "eps" && <EpsTab />}
      {activeTab === "procedimientos" && <ProcedimientosTab />}
      {activeTab === "tarifas" && <TarifasTab />}
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
  const [chainLoading, setChainLoading] = useState(false);

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
    setChainLoading(true);
    setChainView(null);
    try {
      const data = await fetchProcedimientosPorEps(item.id);
      setChainView(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar procedimientos");
    } finally {
      setChainLoading(false);
    }
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
            EPS Contratadas (SQLite)
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
             onClick={(e) => { if (e.target === e.currentTarget) setChainView(null); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                Procedimientos vinculados — {chainView.eps.eps}
              </h2>
              <button onClick={() => setChainView(null)} className="p-1 rounded-md hover:bg-gray-100">
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
              <Button variant="secondary" onClick={() => setChainView(null)}>Cerrar</Button>
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
          Procedimientos CUPS (SQLite)
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

// ─── Tarifas PostgreSQL Tab ──────────────────────────────────────────

function TarifasTab() {
  const [epsList, setEpsList] = useState<string[]>([]);
  const [selectedEps, setSelectedEps] = useState("");
  const [items, setItems] = useState<ProcedimientoPg[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState<ProcedimientoPg>>(initialModal);

  const [formCodigoCups, setFormCodigoCups] = useState("");
  const [formDescripcion, setFormDescripcion] = useState("");
  const [formTarifa, setFormTarifa] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  // Load EPS list on mount
  useEffect(() => {
    fetchEpsDisponibles()
      .then(setEpsList)
      .catch(() => { /* silent */ });
  }, []);

  const loadProcedimientos = useCallback(async (eps: string) => {
    if (!eps) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProcPg(eps);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar tarifas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedEps) {
      loadProcedimientos(selectedEps);
    } else {
      setItems([]);
    }
  }, [selectedEps, loadProcedimientos]);

  const openCreate = () => {
    if (!selectedEps) return;
    setModal({ open: true, mode: "create", item: null });
    setFormCodigoCups("");
    setFormDescripcion("");
    setFormTarifa("");
    setFormError(null);
  };

  const openEdit = (item: ProcedimientoPg) => {
    setModal({ open: true, mode: "edit", item });
    setFormCodigoCups(item.codigo_cups);
    setFormDescripcion(item.descripcion ?? "");
    setFormTarifa(item.tarifa?.toString() ?? "");
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
        await createProcPg({
          eps: selectedEps,
          codigo_cups: formCodigoCups,
          descripcion: formDescripcion || null,
          tarifa: formTarifa ? Number(formTarifa) : null,
        });
      } else if (modal.item) {
        await updateProcPg(modal.item.id, {
          eps: selectedEps,
          codigo_cups: formCodigoCups,
          descripcion: formDescripcion || null,
          tarifa: formTarifa ? Number(formTarifa) : null,
        });
      }
      closeModal();
      await loadProcedimientos(selectedEps);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error al guardar");
    }
  };

  const handleDelete = async (item: ProcedimientoPg) => {
    if (!window.__showConfirm) return;
    const ok = await window.__showConfirm(`¿Eliminar tarifa ${item.codigo_cups}?`);
    if (!ok) return;
    try {
      await deleteProcPg(Number(item.id));
      await loadProcedimientos(selectedEps);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    }
  };

  return (
    <Card className="p-6 border shadow-none" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
          Tarifas Procedimientos (PostgreSQL)
        </h2>
        {selectedEps && (
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-3.5 w-3.5" />
            Nueva Tarifa
          </Button>
        )}
      </div>

      {/* EPS selector */}
      <div className="mb-4">
        <label className="block text-xs font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
          EPS (PostgreSQL)
        </label>
        <select
          value={selectedEps}
          onChange={(e) => setSelectedEps(e.target.value)}
          className="rounded-lg border px-4 py-2.5 text-sm outline-none w-full max-w-xs"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
        >
          <option value="">-- Seleccionar EPS --</option>
          {epsList.map((eps) => (
            <option key={eps} value={eps}>{eps}</option>
          ))}
        </select>
      </div>

      {!selectedEps ? (
        <p className="text-sm text-muted-foreground py-8 text-center">
          Seleccioná una EPS para ver sus tarifas
        </p>
      ) : loading ? (
        <div className="py-8 flex items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          <span className="text-sm text-muted-foreground">Cargando tarifas...</span>
        </div>
      ) : error ? (
        <div>
          <p className="text-sm text-danger mb-2">{error}</p>
          <Button size="sm" onClick={() => loadProcedimientos(selectedEps)}>Reintentar</Button>
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center">No hay tarifas para esta EPS</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                <th className="py-3 px-4 text-left">ID</th>
                <th className="py-3 px-4 text-left">Código CUPS</th>
                <th className="py-3 px-4 text-left">Descripción</th>
                <th className="py-3 px-4 text-left">Tarifa</th>
                <th className="py-3 px-4 text-left">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                  <td className="py-3 px-4" style={{ color: "oklch(0.55 0.04 160)" }}>{item.id}</td>
                  <td className="py-3 px-4 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{item.codigo_cups}</td>
                  <td className="py-3 px-4" style={{ color: "oklch(0.55 0.04 160)" }}>{item.descripcion ?? "—"}</td>
                  <td className="py-3 px-4" style={{ color: "oklch(0.15 0.02 160)" }}>
                    {item.tarifa != null ? `$${item.tarifa.toLocaleString("es-CO")}` : "—"}
                  </td>
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
      )}

      {/* Create/Edit Modal */}
      {modal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                {modal.mode === "create" ? "Nueva Tarifa" : "Editar Tarifa"}
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
                EPS
              </label>
              <input
                type="text"
                value={selectedEps}
                readOnly
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)", background: "#f9fafb", cursor: "not-allowed" }}
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Código CUPS
              </label>
              <input
                type="text"
                value={formCodigoCups}
                onChange={(e) => setFormCodigoCups(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                required
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Descripción
              </label>
              <input
                type="text"
                value={formDescripcion}
                onChange={(e) => setFormDescripcion(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-4 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Tarifa
              </label>
              <input
                type="number"
                step="0.01"
                value={formTarifa}
                onChange={(e) => setFormTarifa(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-6 outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
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
