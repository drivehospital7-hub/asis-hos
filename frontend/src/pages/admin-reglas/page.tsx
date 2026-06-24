import { useState, useEffect, useCallback, useRef } from "react";
import {
  Plus,
  Trash2,
  X,
  Eye,
  Loader2,
  Search,
  Upload,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  GitBranch,
  History,
  Play,
  RefreshCw,
  Ban,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageTitle } from "@/components/status-badge";
import {
  type Regla,
  type CondicionTree,
  type Excepcion,
  type EvidenciaResult,
  type AuditResult,
  type SimulateResult,
  type EvidenciaItem,
  type AuditItem,
  fetchReglas,
  fetchRegla,
  createRegla,
  updateRegla,
  deleteRegla,
  fetchVersiones,
  versionarRegla,
  fetchExcepciones,
  createExcepcion,
  queryEvidencias,
  queryAuditoria,
  simulateReglas,
  clearEvidencias,
} from "@/lib/api-reglas";

// ─── Types ──────────────────────────────────────────────────────────

type TabId = "lista" | "evidencias" | "simulador";

interface Tab {
  id: TabId;
  label: string;
}

const TABS: Tab[] = [
  { id: "lista", label: "Reglas" },
  { id: "evidencias", label: "Evidencias" },
  { id: "simulador", label: "Simulador" },
];

const DOMINIOS = ["odontologia", "urgencias", "equipos_basicos", "transversal", "farmacia", "intramural", "hospitalizacion", "ambulatoria"];
const ESTADOS = ["draft", "active", "deprecated", "retired"];
const SEVERIDADES = ["error", "warning", "info"];
const OPERADORES_COMPOSITE = ["AND", "OR", "NOT"];
const OPERADORES_ATOMICOS = ["eq", "gt", "gte", "lt", "lte", "in", "contains", "regex"];
const FUENTES_DATOS = [
  "invoice.vlr_subsidiado",
  "invoice.vlr_procedimiento",
  "invoice.convenio_facturado",
  "invoice.codigo",
  "invoice.cantidad",
  "invoice.numero_factura",
  "invoice.tipo_procedimiento",
  "invoice.centro_costo",
  "invoice.identificacion",
  "invoice.edad",
  "invoice.tipo_identificacion",
  "invoice.entidad_cobrar",
  "invoice.factura_count",
  "invoice.tipo_usuario",
  "invoice.codigo_entidad_cobrar",
  "invoice.vlr_copago",
  "invoice.ide_contrato",
  "invoice.tarifario",
  "invoice.fec_nacimiento",
  "invoice.fec_factura",
  "invoice.laboratorio",
  "invoice.tipo_factura_descripcion",
  "invoice.codigo_equiv",
  "invoice.codigo_tipo_procedimiento",
  "invoice.entidad_afiliacion",
  "invoice.responsable_cierra",
  "invoice.profesional_atiende",
  "date.edad",
  "date.horas",
  "invoice.distinct_count_tipo_procedimiento",
  "invoice.sum_cantidad",
];

// ─── Badge helpers ──────────────────────────────────────────────────

function EstadoBadge({ estado }: { estado: string }) {
  const colors: Record<string, string> = {
    draft: "bg-yellow-100 text-yellow-800",
    active: "bg-green-100 text-green-800",
    deprecated: "bg-orange-100 text-orange-800",
    retired: "bg-gray-100 text-gray-500",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[estado] ?? "bg-gray-100 text-gray-600"}`}>
      {estado}
    </span>
  );
}

function SeveridadBadge({ severidad }: { severidad: string }) {
  const colors: Record<string, string> = {
    error: "bg-red-100 text-red-700",
    warning: "bg-yellow-100 text-yellow-700",
    info: "bg-blue-100 text-blue-700",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[severidad] ?? "bg-gray-100"}`}>
      {severidad}
    </span>
  );
}

// ─── Main component ─────────────────────────────────────────────────

export function AdminReglasPage() {
  const [activeTab, setActiveTab] = useState<TabId>("lista");

  return (
    <div className="mx-auto max-w-7xl">
      <PageTitle
        title="Admin Reglas"
        description="Gestión del motor de reglas de auditoría."
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
      {activeTab === "lista" && <RulesListView />}
      {activeTab === "evidencias" && <EvidenceDashboard />}
      {activeTab === "simulador" && <SimulatorView />}
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════
// RULES LIST VIEW
// ═════════════════════════════════════════════════════════════════════

function RulesListView() {
  const [items, setItems] = useState<Regla[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterDominio, setFilterDominio] = useState("");
  const [filterEstado, setFilterEstado] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRule, setSelectedRule] = useState<Regla | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "detail">("list");
  const [exceptionsModal, setExceptionsModal] = useState(false);
  const [exceptions, setExceptions] = useState<Excepcion[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createFormNombre, setCreateFormNombre] = useState("");
  const [createFormDesc, setCreateFormDesc] = useState("");
  const [createFormDominio, setCreateFormDominio] = useState("odontologia");
  const [createFormSev, setCreateFormSev] = useState("baja");
  const [createFormPrio, setCreateFormPrio] = useState("50");
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSaving, setCreateSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReglas({
        dominio: filterDominio || undefined,
        estado: filterEstado || undefined,
      });
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar reglas");
    } finally {
      setLoading(false);
    }
  }, [filterDominio, filterEstado]);

  useEffect(() => { load(); }, [load]);

  const filteredItems = (searchTerm
    ? items.filter((r) => r.nombre.toLowerCase().includes(searchTerm.toLowerCase()))
    : items
  ).sort((a, b) => b.id - a.id);

  const handleViewDetail = async (item: Regla) => {
    try {
      const full = await fetchRegla(item.id);
      setSelectedRule(full);
      setViewMode("detail");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar detalle");
    }
  };

  const handleDelete = async (item: Regla) => {
    if (!window.__showConfirm) return;
    const ok = await window.__showConfirm(`¿Desactivar regla "${item.nombre}" (v${item.version})?`);
    if (!ok) return;
    try {
      await deleteRegla(item.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al eliminar");
    }
  };

  const handleViewExceptions = async (item: Regla) => {
    try {
      const data = await fetchExcepciones(item.id);
      setExceptions(data);
      setExceptionsModal(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar excepciones");
    }
  };

  const handleVersionar = async (item: Regla) => {
    try {
      await versionarRegla(item.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al versionar");
    }
  };

  if (viewMode === "detail" && selectedRule) {
    return (
      <RuleDetailForm
        rule={selectedRule}
        onBack={() => { setViewMode("list"); setSelectedRule(null); }}
        onSaved={() => { setViewMode("list"); setSelectedRule(null); load(); }}
      />
    );
  }

  if (loading) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        <span className="text-sm text-muted-foreground">Cargando reglas...</span>
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
    <Card className="p-6 border shadow-none" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
          Reglas de Auditoría
        </h2>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="h-3.5 w-3.5 mr-1" />
          Nueva Regla
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={filterDominio}
          onChange={(e) => setFilterDominio(e.target.value)}
          className="rounded-lg border px-3 py-1.5 text-sm outline-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
        >
          <option value="">Todos los dominios</option>
          {DOMINIOS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select
          value={filterEstado}
          onChange={(e) => setFilterEstado(e.target.value)}
          className="rounded-lg border px-3 py-1.5 text-sm outline-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
        >
          <option value="">Todos los estados</option>
          {ESTADOS.map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} />
          <input
            type="text"
            placeholder="Buscar por nombre..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border pl-9 pr-4 py-1.5 text-sm outline-none"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
          />
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center">No hay reglas</p>
      ) : (
        <div className="rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
          <table className="w-full text-sm table-fixed">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                <th className="py-3 px-4 text-left w-14">#</th>
                <th className="py-3 px-4 text-left">Nombre</th>
                <th className="py-3 px-4 text-left w-28">Dominio</th>
                <th className="py-3 px-4 text-left w-24">Estado</th>
                <th className="py-3 px-4 text-left w-16">Versión</th>
                <th className="py-3 px-4 text-left w-20">Prioridad</th>
                <th className="py-3 px-4 text-left w-24">Severidad</th>
                <th className="py-3 px-4 text-left w-72">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => (
                <tr key={item.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                  <td className="py-3 px-4 text-xs text-muted-foreground font-mono" style={{ color: "oklch(0.55 0.04 160)" }}>{item.id}</td>
                  <td className="py-3 px-4 font-medium truncate cursor-pointer" style={{ color: "oklch(0.15 0.02 160)" }}
                      title={item.nombre}
                      onClick={() => handleViewDetail(item)}>
                    {item.nombre}
                  </td>
                  <td className="py-3 px-4" style={{ color: "oklch(0.55 0.04 160)" }}>{item.dominio}</td>
                  <td className="py-3 px-4"><EstadoBadge estado={item.estado} /></td>
                  <td className="py-3 px-4">v{item.version}</td>
                  <td className="py-3 px-4">{item.prioridad}</td>
                  <td className="py-3 px-4"><SeveridadBadge severidad={item.severidad} /></td>
                  <td className="py-3 px-4">
                    <div className="flex gap-2">
                      <Button size="sm" variant="default" onClick={() => handleViewDetail(item)}>
                        <Eye className="h-3.5 w-3.5" />
                        Ver
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => handleVersionar(item)}>
                        <GitBranch className="h-3.5 w-3.5" />
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => handleViewExceptions(item)}>
                        <Ban className="h-3.5 w-3.5" />
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

      {/* Exceptions Modal */}
      {exceptionsModal && (
        <ExceptionsPanel
          reglaId={exceptions.length > 0 ? exceptions[0].regla_id : 0}
          onClose={() => setExceptionsModal(false)}
        />
      )}

      {/* Create New Rule Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={(e) => { if (e.target === e.currentTarget) setShowCreate(false); }}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                Nueva Regla
              </h2>
              <button onClick={() => setShowCreate(false)} className="p-1 rounded-md hover:bg-gray-100">
                <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              </button>
            </div>
            <form onSubmit={async (e) => {
              e.preventDefault();
              setCreateError(null);
              if (!createFormNombre.trim()) { setCreateError("El nombre es obligatorio"); return; }
              setCreateSaving(true);
              try {
                await createRegla({
                  nombre: createFormNombre.trim(),
                  descripcion: createFormDesc.trim() || null,
                  dominio: createFormDominio,
                  severidad: createFormSev,
                  prioridad: Number(createFormPrio),
                });
                setShowCreate(false);
                setCreateFormNombre("");
                setCreateFormDesc("");
                await load();
              } catch (err) {
                setCreateError(err instanceof Error ? err.message : "Error al crear");
              } finally {
                setCreateSaving(false);
              }
            }}>
              {createError && <p className="text-xs mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{createError}</p>}
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Nombre</label>
              <input type="text" value={createFormNombre} onChange={(e) => setCreateFormNombre(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-3 outline-none"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} required />

              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Descripción</label>
              <textarea value={createFormDesc} onChange={(e) => setCreateFormDesc(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm mb-3 outline-none" rows={2}
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Dominio</label>
                  <select value={createFormDominio} onChange={(e) => setCreateFormDominio(e.target.value)}
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
                    {DOMINIOS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Severidad</label>
                  <select value={createFormSev} onChange={(e) => setCreateFormSev(e.target.value)}
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
                    {SEVERIDADES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Prioridad</label>
                  <input type="number" value={createFormPrio} onChange={(e) => setCreateFormPrio(e.target.value)}
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />
                </div>
              </div>

              <div className="flex gap-2 justify-end">
                <Button type="submit" disabled={createSaving}>
                  {createSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                  Crear Regla
                </Button>
                <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancelar</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Card>
  );
}

// ═════════════════════════════════════════════════════════════════════
// RULE DETAIL / EDIT FORM
// ═════════════════════════════════════════════════════════════════════

interface RuleDetailFormProps {
  rule: Regla;
  onBack: () => void;
  onSaved: () => void;
}

function RuleDetailForm({ rule, onBack, onSaved }: RuleDetailFormProps) {
  const [nombre, setNombre] = useState(rule.nombre);
  const [descripcion, setDescripcion] = useState(rule.descripcion ?? "");
  const [dominio, setDominio] = useState(rule.dominio);
  const [severidad, setSeveridad] = useState(rule.severidad);
  const [prioridad, setPrioridad] = useState(String(rule.prioridad));
  const [activo, setActivo] = useState(rule.activo);
  const [parametros, setParametros] = useState(
    rule.parametros ? JSON.stringify(rule.parametros, null, 2) : ""
  );
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [versions, setVersions] = useState<Regla[]>([]);

  // Editable condition tree state
  const [tree, setTree] = useState<CondicionTree[]>(() => {
    if (rule.condiciones && rule.condiciones.length > 0) {
      return JSON.parse(JSON.stringify(rule.condiciones));
    }
    // Default: empty root AND composite
    return [{ id: 1, tipo: "composite", operador: "AND", fuente_datos: null, valor_esperado: null, condiciones: [], regla_id: 0, padre_id: null, orden: 0 }];
  });

  const isReadOnly = rule.estado !== "active" && rule.estado !== "draft";

  // ── Tree mutation callbacks ──

  const handleNodeUpdate = useCallback((nodeId: number, field: string, value: unknown) => {
    setTree((prev) => {
      const copy: CondicionTree[] = JSON.parse(JSON.stringify(prev));
      updateNodeInTree(copy, nodeId, field, value);
      return copy;
    });
  }, []);

  const handleAddChild = useCallback((parentId: number) => {
    setTree((prev) => {
      const copy: CondicionTree[] = JSON.parse(JSON.stringify(prev));
      addChildToNode(copy, parentId);
      return copy;
    });
  }, []);

  const handleRemoveNode = useCallback((nodeId: number) => {
    setTree((prev) => {
      const copy: CondicionTree[] = JSON.parse(JSON.stringify(prev));
      removeNodeFromTree(copy, nodeId);
      return copy;
    });
  }, []);

  const handleLoadVersions = async () => {
    try {
      const data = await fetchVersiones(rule.id);
      setVersions(data);
      setVersionsOpen(true);
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Error al cargar versiones");
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre.trim()) {
      setFormError("El nombre no puede estar vacío");
      return;
    }
    // Validate parametros JSON if present
    if (parametros.trim()) {
      try {
        JSON.parse(parametros);
      } catch {
        setFormError("El campo Parámetros tiene JSON inválido");
        setSaving(false);
        return;
      }
    }
    setSaving(true);
    setFormError(null);
    try {
      await updateRegla(rule.id, {
        nombre: nombre.trim(),
        descripcion: descripcion.trim() || null,
        dominio,
        severidad,
        prioridad: Number(prioridad),
        activo,
        condiciones: tree,
        parametros: parametros.trim() ? JSON.parse(parametros) : null,
      });
      onSaved();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Card className="p-6 border shadow-none" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Button size="sm" variant="secondary" onClick={onBack}>
              ← Volver
            </Button>
            <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
              {rule.nombre} <span className="text-xs font-mono text-muted-foreground">(#{rule.id})</span> <span className="text-sm font-normal text-muted-foreground">v{rule.version}</span>
            </h2>
            <EstadoBadge estado={rule.estado} />
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={handleLoadVersions}>
              <History className="h-3.5 w-3.5 mr-1" />
              Versiones
            </Button>
            <Button size="sm" variant="default" onClick={() => versionarRegla(rule.id)}>
              <GitBranch className="h-3.5 w-3.5 mr-1" />
              Versionar
            </Button>
          </div>
        </div>

        <form onSubmit={handleSave}>
          {formError && (
            <p className="text-xs mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{formError}</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Nombre
              </label>
              <input
                type="text"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                disabled={isReadOnly}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Dominio
              </label>
              <select
                value={dominio}
                onChange={(e) => setDominio(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                disabled={isReadOnly}
              >
                {DOMINIOS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Severidad
              </label>
              <select
                value={severidad}
                onChange={(e) => setSeveridad(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                disabled={isReadOnly}
              >
                {SEVERIDADES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Prioridad
              </label>
              <input
                type="number"
                value={prioridad}
                onChange={(e) => setPrioridad(e.target.value)}
                className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
                disabled={isReadOnly}
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
              Descripción
            </label>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              className="w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              rows={3}
              disabled={isReadOnly}
            />
          </div>

          {!isReadOnly && (
            <div className="flex items-center gap-3 mb-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={activo}
                  onChange={(e) => setActivo(e.target.checked)}
                  className="rounded border-gray-300"
                  style={{ accentColor: "oklch(0.55 0.04 160)" }}
                />
                <span className="text-sm font-medium" style={{ color: "oklch(0.55 0.04 160)" }}>
                  Activa
                </span>
              </label>
              <span className="text-xs text-muted-foreground">
                {activo ? "La regla se evalúa en los procesos" : "La regla está desactivada, no se evalúa"}
              </span>
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
              Parámetros JSON <span className="text-xs text-muted-foreground font-normal">(opcional — umbrales configurables para reglas paramétricas)</span>
            </label>
            <textarea
              value={parametros}
              onChange={(e) => setParametros(e.target.value)}
              className="w-full rounded-lg border px-4 py-2.5 text-sm font-mono outline-none focus:border-primary"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              rows={3}
              disabled={isReadOnly}
              placeholder='[{"umbral": 3}, {"umbral": 5}]'
            />
          </div>

          {/* Condition Tree */}
          <div className="mb-4">
            <h3 className="text-sm font-semibold mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>
              Árbol de Condiciones
              {!isReadOnly && <span className="text-xs font-normal text-muted-foreground ml-2">(clic para editar)</span>}
            </h3>
            {tree.length > 0 ? (
              <div className="rounded-lg border p-4" style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
                {tree.map((node) => (
                  <ConditionCondicionTree
                    key={node.id}
                    node={node}
                    depth={0}
                    readOnly={isReadOnly}
                    onUpdate={handleNodeUpdate}
                    onAddChild={handleAddChild}
                    onRemove={handleRemoveNode}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Sin condiciones</p>
            )}
          </div>

          {!isReadOnly && (
            <div className="flex gap-2 justify-end">
              <Button type="submit" disabled={saving}>
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                Guardar Cambios
              </Button>
            </div>
          )}
        </form>
      </Card>

      {/* Versions Timeline */}
      {versionsOpen && (
        <VersionTimeline
          versions={versions}
          onClose={() => setVersionsOpen(false)}
          onVersionar={async (id) => {
            await versionarRegla(id);
            handleLoadVersions();
          }}
        />
      )}
    </>
  );
}

// ═════════════════════════════════════════════════════════════════════
// CONDITION TREE NODE — editable when readOnly=false
// ═════════════════════════════════════════════════════════════════════

interface ConditionCondicionTreeProps {
  node: CondicionTree;
  depth: number;
  readOnly?: boolean;
  onUpdate?: (nodeId: number, field: string, value: unknown) => void;
  onAddChild?: (parentId: number) => void;
  onRemove?: (nodeId: number) => void;
}

function ConditionCondicionTree({ node, depth, readOnly, onUpdate, onAddChild, onRemove }: ConditionCondicionTreeProps) {
  const isComposite = node.tipo === "composite" || node.tipo === "AND" || node.tipo === "OR" || node.tipo === "NOT";
  const indent = depth * 20;
  const children = node.condiciones ?? [];

  return (
    <div className="mb-2" style={{ marginLeft: `${indent}px` }}>
      <div
        className="flex items-center gap-2 p-2 rounded-md text-sm"
        style={{
          background: isComposite ? "oklch(0.55 0.04 160 / 0.06)" : "white",
          borderLeft: isComposite ? "3px solid oklch(0.55 0.04 160)" : "3px solid oklch(0.6 0.2 25 / 0.3)",
        }}
      >
        {readOnly ? (
          // ── READ-ONLY DISPLAY ──
          isComposite ? (
            <span className="font-semibold text-xs uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
              {node.operador ?? node.tipo}
            </span>
          ) : (
            <>
              <span className="font-medium text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>
                {node.fuente_datos ?? "?"}
              </span>
              <span className="text-xs text-muted-foreground">{node.operador}</span>
              <span className="text-xs font-mono" style={{ color: "oklch(0.15 0.02 160)" }}>
                {String(node.valor_esperado ?? "")}
              </span>
            </>
          )
        ) : (
          // ── EDIT MODE ──
          isComposite ? (
            <>
              <select
                value={node.operador ?? "AND"}
                onChange={(e) => onUpdate?.(node.id, "operador", e.target.value)}
                className="text-xs font-semibold uppercase border rounded px-2 py-1 outline-none"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.3)" }}
              >
                {OPERADORES_COMPOSITE.map((op) => <option key={op} value={op}>{op}</option>)}
              </select>
              <button
                type="button"
                onClick={() => onAddChild?.(node.id)}
                className="ml-auto px-2 py-1 text-xs rounded hover:bg-gray-100"
                style={{ color: "oklch(0.55 0.04 160)" }}
                title="Agregar hijo"
              >
                + Agregar
              </button>
            </>
          ) : (
            <>
              <select
                value={node.fuente_datos ?? ""}
                onChange={(e) => onUpdate?.(node.id, "fuente_datos", e.target.value)}
                className="text-xs border rounded px-2 py-1 outline-none min-w-[180px]"
                style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
              >
                <option value="">-- fuente --</option>
                {FUENTES_DATOS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
              <select
                value={node.operador ?? ""}
                onChange={(e) => onUpdate?.(node.id, "operador", e.target.value)}
                className="text-xs border rounded px-2 py-1 outline-none"
                style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
              >
                <option value="">-- op --</option>
                {OPERADORES_ATOMICOS.map((op) => <option key={op} value={op}>{op}</option>)}
              </select>
              <input
                type="text"
                value={String(node.valor_esperado ?? "")}
                onChange={(e) => onUpdate?.(node.id, "valor_esperado", e.target.value)}
                className="text-xs font-mono border rounded px-2 py-1 outline-none flex-1 min-w-[100px]"
                style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
                placeholder="valor"
              />
              <button
                type="button"
                onClick={() => onRemove?.(node.id)}
                className="p-1 rounded hover:bg-red-50"
                title="Eliminar"
                style={{ color: "oklch(0.6 0.2 25)" }}
              >
                <X className="h-3 w-3" />
              </button>
            </>
          )
        )}
      </div>

      {/* Children (only for composite nodes) */}
      {isComposite && children.length > 0 && (
        <div className="ml-2 mt-1">
          {children.map((child) => (
            <ConditionCondicionTree
              key={child.id}
              node={child}
              depth={depth + 1}
              readOnly={readOnly}
              onUpdate={onUpdate}
              onAddChild={onAddChild}
              onRemove={onRemove}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Counter for temp IDs when adding new nodes
let _tempNodeId = 1000;
function nextNodeId(): number {
  _tempNodeId++;
  return _tempNodeId;
}

// ── Tree manipulation helpers ──

function updateNodeInTree(nodes: CondicionTree[], nodeId: number, field: string, value: unknown): boolean {
  for (const n of nodes) {
    if (n.id === nodeId) {
      (n as Record<string, unknown>)[field] = value;
      return true;
    }
    if (n.condiciones && updateNodeInTree(n.condiciones, nodeId, field, value)) return true;
  }
  return false;
}

function removeNodeFromTree(nodes: CondicionTree[], nodeId: number): boolean {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i].id === nodeId) {
      nodes.splice(i, 1);
      return true;
    }
    if (nodes[i].condiciones && removeNodeFromTree(nodes[i].condiciones!, nodeId)) return true;
  }
  return false;
}

function addChildToNode(nodes: CondicionTree[], parentId: number): boolean {
  for (const n of nodes) {
    if (n.id === parentId) {
      if (!n.condiciones) n.condiciones = [];
      n.condiciones.push({
        id: nextNodeId(),
        tipo: "atomic",
        operador: "eq",
        fuente_datos: "",
        valor_esperado: "",
        regla_id: 0,
        padre_id: parentId,
        orden: n.condiciones.length,
      });
      return true;
    }
    if (n.condiciones && addChildToNode(n.condiciones, parentId)) return true;
  }
  return false;
}

// ═════════════════════════════════════════════════════════════════════
// EXCEPTIONS PANEL
// ═════════════════════════════════════════════════════════════════════

interface ExceptionsPanelProps {
  reglaId: number;
  onClose: () => void;
}

function ExceptionsPanel({ reglaId, onClose }: ExceptionsPanelProps) {
  const [items, setItems] = useState<Excepcion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [formTipo, setFormTipo] = useState("skip");
  const [formCondicion, setFormCondicion] = useState("{}");
  const [formActivo, setFormActivo] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchExcepciones(reglaId);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar excepciones");
    } finally {
      setLoading(false);
    }
  }, [reglaId]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      let condicionJson: Record<string, unknown>;
      try {
        condicionJson = JSON.parse(formCondicion);
      } catch {
        setFormError("JSON inválido en condición");
        return;
      }
      await createExcepcion(reglaId, {
        tipo_efecto: formTipo,
        condicion_json: condicionJson,
        activo: formActivo,
      });
      setShowCreate(false);
      setFormCondicion("{}");
      setFormTipo("skip");
      setFormActivo(true);
      await load();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Error al crear");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
            Excepciones — Regla #{reglaId}
          </h2>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-gray-100">
            <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : error ? (
          <p className="text-sm text-danger">{error}</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">Sin excepciones</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border mb-4" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                  <th className="py-2 px-3 text-left">Tipo</th>
                  <th className="py-2 px-3 text-left">Condición</th>
                  <th className="py-2 px-3 text-left">Activo</th>
                </tr>
              </thead>
              <tbody>
                {items.map((exc) => (
                  <tr key={exc.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                    <td className="py-2 px-3">{exc.tipo_efecto}</td>
                    <td className="py-2 px-3 text-xs font-mono max-w-[200px] truncate">{JSON.stringify(exc.condicion_json)}</td>
                    <td className="py-2 px-3">
                      {exc.activo ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      ) : (
                        <XCircle className="h-4 w-4 text-gray-400" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex gap-2">
          <Button size="sm" onClick={() => setShowCreate(!showCreate)}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            Nueva Excepción
          </Button>
        </div>

        {showCreate && (
          <form onSubmit={handleCreate} className="mt-4 p-4 rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
            {formError && <p className="text-xs mb-2" style={{ color: "oklch(0.6 0.2 25)" }}>{formError}</p>}
            <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Tipo Efecto</label>
            <select value={formTipo} onChange={(e) => setFormTipo(e.target.value)}
              className="w-full rounded-lg border px-3 py-1.5 text-sm mb-3 outline-none"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
              <option value="skip">Skip</option>
              <option value="downgrade">Downgrade</option>
              <option value="override">Override</option>
            </select>
            <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Condición (JSON)</label>
            <textarea value={formCondicion} onChange={(e) => setFormCondicion(e.target.value)}
              className="w-full rounded-lg border px-3 py-1.5 text-sm mb-3 outline-none font-mono"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} rows={3} />
            <label className="flex items-center gap-2 text-sm mb-4">
              <input type="checkbox" checked={formActivo} onChange={(e) => setFormActivo(e.target.checked)} />
              Activo
            </label>
            <div className="flex gap-2 justify-end">
              <Button type="submit" size="sm">Crear</Button>
              <Button type="button" size="sm" variant="secondary" onClick={() => setShowCreate(false)}>Cancelar</Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════
// VERSION TIMELINE
// ═════════════════════════════════════════════════════════════════════

interface VersionTimelineProps {
  versions: Regla[];
  onClose: () => void;
  onVersionar: (id: number) => Promise<void>;
}

function VersionTimeline({ versions, onClose, onVersionar }: VersionTimelineProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-xl mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
            Historial de Versiones
          </h2>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-gray-100">
            <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
          </button>
        </div>

        {versions.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">Sin versiones</p>
        ) : (
          <div className="space-y-3">
            {versions.map((v) => (
              <div key={v.id} className="flex items-center justify-between p-3 rounded-lg border"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-sm" style={{ color: "oklch(0.15 0.02 160)" }}>
                    v{v.version}
                  </span>
                  <EstadoBadge estado={v.estado} />
                  {v.creado_en && (
                    <span className="text-xs text-muted-foreground">
                      {new Date(v.creado_en).toLocaleDateString("es-CO")}
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {v.estado === "active" && (
                    <Button size="sm" variant="default" onClick={() => onVersionar(v.id)}>
                      <GitBranch className="h-3 w-3 mr-1" />
                      Versionar
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════
// EVIDENCE DASHBOARD
// ═════════════════════════════════════════════════════════════════════

function EvidenceDashboard() {
  const [tab, setTab] = useState<"evidencias" | "auditoria">("evidencias");
  const [factura, setFactura] = useState("");
  const [reglaId, setReglaId] = useState("");
  const [dominio, setDominio] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [resultado, setResultado] = useState("");
  const [results, setResults] = useState<EvidenciaResult | AuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const handleSearch = async (newOffset = 0) => {
    setLoading(true);
    setError(null);
    setOffset(newOffset);
    try {
      if (tab === "evidencias") {
        const data = await queryEvidencias({
          factura: factura || undefined,
          regla_id: reglaId ? Number(reglaId) : undefined,
          dominio: dominio || undefined,
          outcome: resultado || undefined,
          desde: desde || undefined,
          hasta: hasta || undefined,
          limit,
          offset: newOffset,
        });
        setResults(data);
      } else {
        const data = await queryAuditoria({
          factura: factura || undefined,
          regla_id: reglaId ? Number(reglaId) : undefined,
          resultado: resultado || undefined,
          desde: desde || undefined,
          hasta: hasta || undefined,
          limit,
          offset: newOffset,
        });
        setResults(data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al buscar");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setFactura("");
    setReglaId("");
    setDominio("");
    setDesde("");
    setHasta("");
    setResultado("");
    setResults(null);
    setOffset(0);
    setError(null);
  };

  const totalPages = results ? Math.ceil(results.total / limit) : 0;
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <Card className="p-6 border shadow-none" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
          Evidencias y Auditoría
        </h2>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 mb-4">
        <button onClick={() => { setTab("evidencias"); setResults(null); }}
          className="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
          style={{
            background: tab === "evidencias" ? "oklch(0.55 0.04 160 / 0.1)" : "transparent",
            color: tab === "evidencias" ? "var(--color-primary)" : "var(--color-muted-foreground)",
          }}>
          Evidencias
        </button>
        <button onClick={() => { setTab("auditoria"); setResults(null); }}
          className="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
          style={{
            background: tab === "auditoria" ? "oklch(0.55 0.04 160 / 0.1)" : "transparent",
            color: tab === "auditoria" ? "var(--color-primary)" : "var(--color-muted-foreground)",
          }}>
          Auditoría
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input type="text" placeholder="Factura" value={factura} onChange={(e) => setFactura(e.target.value)}
          className="rounded-lg border px-3 py-1.5 text-sm outline-none w-32"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />
        <input type="number" placeholder="Regla ID" value={reglaId} onChange={(e) => setReglaId(e.target.value)}
          className="rounded-lg border px-3 py-1.5 text-sm outline-none w-24"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />
        <select value={dominio} onChange={(e) => setDominio(e.target.value)}
          className="rounded-lg border px-3 py-1.5 text-sm outline-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
          <option value="">Todos los dominios</option>
          {DOMINIOS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        {tab === "auditoria" && (
          <select value={resultado} onChange={(e) => setResultado(e.target.value)}
            className="rounded-lg border px-3 py-1.5 text-sm outline-none"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
            <option value="">Todos</option>
            <option value="FAIL">FAIL</option>
            <option value="PASS">PASS</option>
            <option value="ERROR">ERROR</option>
          </select>
        )}
        {tab === "evidencias" && (
          <select value={resultado} onChange={(e) => setResultado(e.target.value)}
            className="rounded-lg border px-3 py-1.5 text-sm outline-none"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}>
            <option value="">Todos</option>
            <option value="MATCH">MATCH</option>
            <option value="NO_MATCH">NO_MATCH</option>
            <option value="ERROR">ERROR</option>
          </select>
        )}
        <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)}
          className="rounded-lg border px-3 py-1.5 text-sm outline-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />
        <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)}
          className="rounded-lg border px-3 py-1.5 text-sm outline-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }} />
        <Button size="sm" onClick={() => handleSearch(0)}>
          <Search className="h-3.5 w-3.5 mr-1" />
          Buscar
        </Button>
        <Button size="sm" variant="secondary" onClick={handleClear}>
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Limpiar
        </Button>
        <Button size="sm" variant="destructive" onClick={async () => {
          if (!window.__showConfirm) return;
          const ok = await window.__showConfirm(
            "ESTA ACCION ES PARA PRUEBAS.\n\nSe van a eliminar TODOS los registros de evidencia y auditoría.\n¿Estás seguro?"
          );
          if (!ok) return;
          try {
            await clearEvidencias();
            setResults(null);
            setError("Datos de evidencia y auditoría eliminados (solo para pruebas)");
          } catch (e) {
            setError(e instanceof Error ? e.message : "Error al limpiar");
          }
        }}>
          <Trash2 className="h-3.5 w-3.5 mr-1" />
          Limpiar datos
        </Button>
      </div>

      {error && <p className="text-sm text-danger mb-3">{error}</p>}

          {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : results ? (
        <>
          <p className="text-xs text-muted-foreground mb-2">Total: {results.total} resultados</p>
          {results.items.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">Sin resultados</p>
          ) : tab === "evidencias" ? (
            <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                    <th className="py-2 px-3 text-left">Factura</th>
                    <th className="py-2 px-3 text-left">Regla</th>
                    <th className="py-2 px-3 text-left">Outcome</th>
                    <th className="py-2 px-3 text-left">Dominio</th>
                    <th className="py-2 px-3 text-left">Traza</th>
                  </tr>
                </thead>
                <tbody>
                  {(results.items as EvidenciaItem[]).map((item) => (
                    <tr key={item.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                      <td className="py-2 px-3 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{item.factura}</td>
                      <td className="py-2 px-3">#{item.regla_id}</td>
                      <td className="py-2 px-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            background: item.outcome === "MATCH" ? "oklch(0.6 0.2 145 / 0.1)" : "oklch(0.6 0.2 25 / 0.1)",
                            color: item.outcome === "MATCH" ? "oklch(0.4 0.2 145)" : "oklch(0.6 0.2 25)",
                          }}>
                          {item.outcome}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-xs">{item.dominio}</td>
                      <td className="py-2 px-3">
                        <span className="text-xs font-mono text-muted-foreground truncate block max-w-[200px]"
                          title={JSON.stringify(item.arbol_evaluado)}>
                          {JSON.stringify(item.arbol_evaluado).slice(0, 60)}...
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                    <th className="py-2 px-3 text-left">Factura</th>
                    <th className="py-2 px-3 text-left">Regla</th>
                    <th className="py-2 px-3 text-left">Resultado</th>
                    <th className="py-2 px-3 text-left">Severidad</th>
                    <th className="py-2 px-3 text-left">Mensaje</th>
                    <th className="py-2 px-3 text-left">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {(results.items as AuditItem[]).map((item) => (
                    <tr key={item.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                      <td className="py-2 px-3 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{item.factura}</td>
                      <td className="py-2 px-3">#{item.regla_id}</td>
                      <td className="py-2 px-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            background: item.resultado === "FAIL" ? "oklch(0.6 0.2 145 / 0.1)" : item.resultado === "PASS" ? "oklch(0.6 0.2 160 / 0.1)" : "oklch(0.5 0.2 55 / 0.1)",
                            color: item.resultado === "FAIL" ? "oklch(0.4 0.2 145)" : item.resultado === "PASS" ? "oklch(0.4 0.2 160)" : "oklch(0.5 0.2 55)",
                          }}>
                          {item.resultado}
                        </span>
                      </td>
                      <td className="py-2 px-3"><SeveridadBadge severidad={item.severidad} /></td>
                      <td className="py-2 px-3 text-xs text-muted-foreground truncate max-w-[250px]">{item.mensaje ?? "—"}</td>
                      <td className="py-2 px-3 text-xs text-muted-foreground">{item.creado_en ? String(item.creado_en).slice(0, 10) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-muted-foreground">
                Página {currentPage} de {totalPages}
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" disabled={offset === 0}
                  onClick={() => handleSearch(Math.max(0, offset - limit))}>
                  Anterior
                </Button>
                <Button size="sm" variant="secondary" disabled={offset + limit >= results.total}
                  onClick={() => handleSearch(offset + limit)}>
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </>
      ) : null}
    </Card>
  );
}

// ═════════════════════════════════════════════════════════════════════
// SIMULATOR VIEW
// ═════════════════════════════════════════════════════════════════════

function SimulatorView() {
  const [file, setFile] = useState<File | null>(null);
  const [ruleName, setRuleName] = useState("");
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isExcel = (f: File) => f.name.endsWith(".xlsx") || f.name.endsWith(".xls");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) { setFile(null); return; }
    if (!isExcel(f)) {
      setError("Formato no válido. Seleccioná un archivo Excel.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(f);
    setResult(null);
  };

  const handleSimulate = async () => {
    if (!file) {
      setError("Seleccioná un archivo Excel primero");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await simulateReglas(file, ruleName || undefined);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al simular");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6 border shadow-none" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
          Simulador de Reglas
        </h2>
      </div>

      <p className="text-sm text-muted-foreground mb-4">
        Subí un archivo Excel para comparar los resultados del motor de reglas (DB) contra los detectores legacy (Python).
        Se procesarán hasta 100 filas.
      </p>

      {/* File upload */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg border cursor-pointer hover:bg-gray-50 transition-colors"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} />
          <span className="text-sm">{file ? file.name : "Seleccionar Excel"}</span>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={handleFileChange}
          className="hidden"
        />
        <input
          type="text"
          placeholder="Nombre de regla (opcional)"
          value={ruleName}
          onChange={(e) => setRuleName(e.target.value)}
          className="rounded-lg border px-3 py-2 text-sm outline-none flex-1 max-w-xs"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
        />
        <Button size="sm" onClick={handleSimulate} disabled={loading || !file}>
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Play className="h-3.5 w-3.5 mr-1" />}
          Simular
        </Button>
      </div>

      {file && file.name.endsWith(".xls") && (
        <div className="flex items-center gap-2 p-2 mb-4 rounded-md text-xs"
          style={{ background: "oklch(0.6 0.2 55 / 0.1)", color: "oklch(0.6 0.2 55)" }}>
          <AlertTriangle className="h-3.5 w-3.5" />
          Solo se procesarán las primeras 100 filas.
        </div>
      )}

      {error && (
        <p className="text-sm mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{error}</p>
      )}

      {result && (
        <div className="space-y-4">
          {/* Diff summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg border text-center" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
              <p className="text-2xl font-bold" style={{ color: "oklch(0.4 0.2 145)" }}>{result.diff.matched_count}</p>
              <p className="text-xs text-muted-foreground">Coincidencias</p>
            </div>
            <div className="p-3 rounded-lg border text-center" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
              <p className="text-2xl font-bold" style={{ color: "oklch(0.6 0.2 55)" }}>{result.diff.engine_only_count}</p>
              <p className="text-xs text-muted-foreground">Solo Engine</p>
            </div>
            <div className="p-3 rounded-lg border text-center" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
              <p className="text-2xl font-bold" style={{ color: "oklch(0.6 0.2 25)" }}>{result.diff.legacy_only_count}</p>
              <p className="text-xs text-muted-foreground">Solo Legacy</p>
            </div>
            <div className="p-3 rounded-lg border text-center" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
              <p className="text-2xl font-bold" style={{ color: "oklch(0.15 0.02 160)" }}>{result.total_rows}</p>
              <p className="text-xs text-muted-foreground">Filas procesadas</p>
            </div>
          </div>

          {/* Side-by-side results */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>
                Engine Results ({result.engine_results.length})
              </h3>
              {result.engine_results.length === 0 ? (
                <p className="text-xs text-muted-foreground">Sin resultados</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border max-h-60 overflow-y-auto" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50 font-semibold" style={{ color: "oklch(0.55 0.04 160)" }}>
                        {Object.keys(result.engine_results[0]).map((k) => (
                          <th key={k} className="py-1.5 px-2 text-left">{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.engine_results.map((r, i) => (
                        <tr key={i} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                          {Object.values(r).map((v, j) => (
                            <td key={j} className="py-1.5 px-2">{String(v ?? "")}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>
                Legacy Results ({result.legacy_results.length})
              </h3>
              {result.legacy_results.length === 0 ? (
                <p className="text-xs text-muted-foreground">Sin resultados</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border max-h-60 overflow-y-auto" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50 font-semibold" style={{ color: "oklch(0.55 0.04 160)" }}>
                        {Object.keys(result.legacy_results[0]).map((k) => (
                          <th key={k} className="py-1.5 px-2 text-left">{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.legacy_results.map((r, i) => (
                        <tr key={i} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                          {Object.values(r).map((v, j) => (
                            <td key={j} className="py-1.5 px-2">{String(v ?? "")}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {result.truncated && (
            <p className="text-xs text-muted-foreground">
              ⚠️ El archivo original tiene {result.total_rows} filas. Solo se procesaron las primeras {result.rows_processed}.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
