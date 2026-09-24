import { useState, useEffect, useCallback, useMemo, useRef } from "react";

declare global {
  interface Window {
    Modal?: {
      confirm: (msg: string) => Promise<boolean>;
    };
    __showConfirm?: (msg: string) => Promise<boolean>;
  }
}
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
  Play,
  RefreshCw,
  Ban,
  Pencil,
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
  type CatalogoListItem,
  type ReglaRef,
  fetchReglas,
  fetchRegla,
  createRegla,
  updateRegla,
  deleteRegla,
  duplicarRegla,
  desactivarTodasReglas,
  fetchExcepciones,
  createExcepcion,
  queryEvidencias,
  queryAuditoria,
  simulateReglas,
  fetchCatalogos,
  createCatalogo,
  updateCatalogo,
  deleteCatalogo,
  fetchCatalogoReglas,
} from "@/lib/api-reglas";
import { ConditionTreeEditor, validateConditionTree } from "@/components/admin-reglas/ConditionTreeEditor";
import { GroupingFields } from "@/components/admin-reglas/GroupingFields";
import { ResultadosProcesar } from "@/components/procesar/ResultadosProcesar";
import { Toast } from "@/components/procesar/Toast";
import { useBulkActivacion } from "@/hooks/useBulkActivacion";
import { useEnvioControl } from "@/hooks/useEnvioControl";
import { hasControlWrite, norm } from "@/pages/procesar/utils";

// ─── Types ──────────────────────────────────────────────────────────

type TabId = "lista" | "evidencias" | "simulador" | "catalogos";

interface Tab {
  id: TabId;
  label: string;
  disabled?: boolean;
}

const TABS: Tab[] = [
  { id: "lista", label: "Reglas" },
  // TODO: reactivar Evidencias cuando tenga funcionalidad
  { id: "evidencias", label: "Evidencias", disabled: true },
  { id: "simulador", label: "Simulador" },
  { id: "catalogos", label: "Catálogos" },
];

/** Canonical dominio order — mirror of backend REGLA_DOMINIOS_VALIDOS
 *  (app/constants/base.py). Single shared definition for every view below. */
const DOMINIOS = ["urgencias", "hospitalizacion", "odontologia", "equipos_basicos", "transversal", "farmacia", "intramural", "ambulatoria"];
const DOMINIO_TRANSVERSAL = "transversal";

/** Minimal scope shape shared by Regla and ReglaRef. */
interface RuleScope {
  dominio?: string | null;
  dominios?: string[];
}

/** Scoped dominios for a rule. Falls back to the legacy `dominio` mirror,
 *  then to `[]` when the scope is absent (old payloads). */
export function getRuleDominios(rule: RuleScope): string[] {
  if (Array.isArray(rule.dominios)) return rule.dominios;
  return rule.dominio ? [rule.dominio] : [];
}

/** Single-select filter match: the rule applies when the selected dominio
 *  belongs to its scope. Transversal rules apply everywhere, so they stay
 *  visible under every filter (mirrors the backend list ∈ semantics). */
export function ruleMatchesDominio(rule: RuleScope, filtro: string): boolean {
  if (!filtro) return true;
  const scope = getRuleDominios(rule);
  return scope.includes(filtro) || scope.includes(DOMINIO_TRANSVERSAL);
}

/** Scope payload for create/update: canonical sorted array plus the legacy
 *  single-value mirror (first sorted value) for old readers. */
export function buildDominiosPayload(selected: string[]): { dominios: string[]; dominio: string } {
  const dominios = [...selected].sort();
  return { dominios, dominio: dominios[0] };
}

const SEVERIDADES = ["error", "warning", "info"];

// ─── Badge helpers ──────────────────────────────────────────────────

interface EstadoBadgeProps {
  estado: string;
  activo?: boolean;
}

function EstadoBadge({ estado, activo }: EstadoBadgeProps) {
  if (estado === "active" && activo === false) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
        inactiva
      </span>
    );
  }
  const colors: Record<string, string> = {
    active: "bg-green-100 text-green-800",
    retired: "bg-gray-100 text-gray-500",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[estado] ?? "bg-gray-100 text-gray-600"}`}>
      {estado}
    </span>
  );
}

const DOMINIO_COLORS: Record<string, string> = {
  odontologia: "bg-emerald-100 text-emerald-700",
  urgencias: "bg-red-100 text-red-700",
  equipos_basicos: "bg-purple-100 text-purple-700",
  transversal: "bg-amber-100 text-amber-700",
  farmacia: "bg-cyan-100 text-cyan-700",
  intramural: "bg-indigo-100 text-indigo-700",
  hospitalizacion: "bg-pink-100 text-pink-700",
  ambulatoria: "bg-orange-100 text-orange-700",
};

/** Stacked badges for every scoped dominio. Stored values outside the known
 *  list render as-is (plain gray badge) and are never hidden or dropped. */
export function DominiosBadges({ dominios }: { dominios: string[] }) {
  if (dominios.length === 0) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {dominios.map((d) => (
        <span
          key={d}
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${DOMINIO_COLORS[d] ?? "bg-gray-100 text-gray-600"}`}
        >
          {d}
        </span>
      ))}
    </span>
  );
}

interface DominioScopeEditorProps {
  selected: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
}

/** Checkbox group over the shared DOMINIOS order. Stored values outside the
 *  option list render as checked custom badges so they survive save untouched. */
export function DominioScopeEditor({ selected, onChange, disabled }: DominioScopeEditorProps) {
  const unknown = selected.filter((d) => !DOMINIOS.includes(d));
  const toggle = (dominio: string) => {
    onChange(
      selected.includes(dominio)
        ? selected.filter((d) => d !== dominio)
        : [...selected, dominio],
    );
  };
  return (
    <fieldset>
      <div className="flex flex-wrap gap-2">
        {DOMINIOS.map((d) => (
          <label
            key={d}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border cursor-pointer"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
          >
            <input
              type="checkbox"
              checked={selected.includes(d)}
              onChange={() => toggle(d)}
              disabled={disabled}
              aria-label={`Dominio ${d}`}
              className="h-3.5 w-3.5"
              style={{ accentColor: "oklch(0.55 0.04 160)" }}
            />
            {d}
          </label>
        ))}
        {unknown.map((d) => (
          <label
            key={d}
            title="Valor guardado fuera de la lista actual — se conserva al guardar"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border border-dashed bg-gray-50 text-gray-600 cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.includes(d)}
              onChange={() => toggle(d)}
              disabled={disabled}
              aria-label={`Dominio personalizado ${d}`}
              className="h-3.5 w-3.5"
            />
            {d}
          </label>
        ))}
      </div>
    </fieldset>
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
    <div className="w-full max-w-none mx-auto">
      <PageTitle
        title="Admin Reglas"
        description="Gestión del motor de reglas de auditoría."
      />

      {/* Tab selector */}
      <div className="mb-6 flex gap-1 border-b border-border" role="tablist">
        {TABS.map((tab) =>
          tab.disabled ? (
            <button
              key={tab.id}
              role="tab"
              aria-selected={false}
              aria-disabled="true"
              disabled
              title="Próximamente — en construcción"
              className="px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px opacity-50 cursor-not-allowed text-gray-400"
              style={{ borderColor: "transparent" }}
            >
              {tab.label}
            </button>
          ) : (
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
          )
        )}
      </div>

      {/* Tab panels */}
      {activeTab === "lista" && <RulesListView />}
      {activeTab === "evidencias" && <EvidenceDashboard />}
      {activeTab === "simulador" && <SimulatorView />}
      {activeTab === "catalogos" && <CatalogosListView />}
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
  const [filterActivo, setFilterActivo] = useState("");
  const [filterGrupo, setFilterGrupo] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRule, setSelectedRule] = useState<Regla | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "detail">("list");
  const [exceptionsModal, setExceptionsModal] = useState(false);
  const [exceptions, setExceptions] = useState<Excepcion[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createFormNombre, setCreateFormNombre] = useState("");
  const [createFormDesc, setCreateFormDesc] = useState("");
  const [createFormDominios, setCreateFormDominios] = useState<string[]>(["odontologia"]);
  const [createFormSev, setCreateFormSev] = useState("baja");
  const [createFormPrio, setCreateFormPrio] = useState("50");
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSaving, setCreateSaving] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const {
    selectedIds,
    running: bulkRunning,
    done: bulkDone,
    total: bulkTotal,
    failures: bulkFailures,
    toggleId: toggleSelectId,
    toggleAll: toggleSelectAll,
    clear: clearSelection,
    prune: pruneSelection,
    retainOnly: retainOnlySelection,
    runBulk,
  } = useBulkActivacion({ runOne: (id, activo) => updateRegla(id, { activo }) });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const isRetiredView = filterActivo === "retired";
      const data = await fetchReglas({
        dominio: filterDominio || undefined,
        ...(isRetiredView
          ? { estado: "retired" }
          : { estado: "active", activo: filterActivo || undefined }),
      });
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar reglas");
    } finally {
      setLoading(false);
    }
  }, [filterDominio, filterActivo]);

  useEffect(() => { load(); }, [load]);

  const isRetiredView = filterActivo === "retired";

  useEffect(() => {
    if (isRetiredView) clearSelection();
  }, [isRetiredView, clearSelection]);

  useEffect(() => {
    pruneSelection(items.map((r) => r.id));
  }, [items, pruneSelection]);

  const grupoOptions = Array.from(
    new Set(
      items
        .map((r) => r.grupo_error?.trim())
        .filter((g): g is string => !!g)
    )
  ).sort((a, b) => a.localeCompare(b));

  const filteredItems = items
    .filter(
      (r) =>
        (!searchTerm ||
          r.nombre.toLowerCase().includes(searchTerm.toLowerCase())) &&
        (!filterGrupo || r.grupo_error === filterGrupo)
    )
    .sort((a, b) => b.id - a.id);

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
    const ok = await window.__showConfirm(`¿Retirar regla "${item.nombre}"?`);
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

  const handleDuplicate = async (item: Regla) => {
    try {
      const duplicated = await duplicarRegla(item.id);
      setSelectedRule(duplicated);
      setViewMode("detail");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al duplicar");
    }
  };

  const activeCount = items.filter((r) => r.activo && r.estado === "active").length;

  const handleDeactivateAll = async () => {
    if (!window.__showConfirm) return;
    const ok = await window.__showConfirm(
      `¿Desactivar las ${activeCount} reglas activas? /procesar quedará sin validaciones.`
    );
    if (!ok) return;
    setDeactivating(true);
    try {
      await desactivarTodasReglas();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al desactivar reglas");
    } finally {
      setDeactivating(false);
    }
  };

  const handleBulk = async (activo: boolean) => {
    const failures = await runBulk(activo);
    await load();
    if (failures.length === 0) {
      clearSelection();
    } else {
      retainOnlySelection(failures.map((f) => f.id));
    }
  };

  const filteredIds = filteredItems.map((r) => r.id);
  const allFilteredSelected =
    filteredIds.length > 0 && filteredIds.every((id) => selectedIds.includes(id));

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
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="destructive"
            onClick={handleDeactivateAll}
            disabled={loading || deactivating || activeCount === 0 || isRetiredView}
          >
            {deactivating
              ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
              : <Ban className="h-3.5 w-3.5 mr-1" />}
            Desactivar todas
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            Nueva Regla
          </Button>
        </div>
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
          value={filterActivo}
          onChange={(e) => setFilterActivo(e.target.value)}
          aria-label="Filtrar por activación"
          className="rounded-lg border px-3 py-1.5 text-sm outline-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
        >
          <option value="">Todas</option>
          <option value="true">Activas</option>
          <option value="false">Inactivas</option>
          <option value="retired">Retiradas</option>
        </select>
        <select
          value={filterGrupo}
          onChange={(e) => setFilterGrupo(e.target.value)}
          aria-label="Filtrar por grupo de error"
          className="rounded-lg border px-3 py-1.5 text-sm outline-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
        >
          <option value="">Todos los grupos</option>
          {grupoOptions.map((g) => <option key={g} value={g}>{g}</option>)}
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

      {/* Bulk activation bar — disabled in Retiradas view (read-only) */}
      {selectedIds.length > 0 && !isRetiredView && (
        <div className="flex flex-wrap items-center gap-3 mb-4 p-3 rounded-lg border"
             style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)", background: "oklch(0.55 0.04 160 / 0.04)" }}>
          <span className="text-sm font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>
            {selectedIds.length} seleccionada{selectedIds.length === 1 ? "" : "s"}
          </span>
          <Button size="sm" onClick={() => handleBulk(true)} disabled={bulkRunning}>
            {bulkRunning
              ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
              : <CheckCircle2 className="h-3.5 w-3.5 mr-1" />}
            Activar
          </Button>
          <Button size="sm" variant="secondary" onClick={() => handleBulk(false)} disabled={bulkRunning}>
            {bulkRunning
              ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
              : <XCircle className="h-3.5 w-3.5 mr-1" />}
            Desactivar
          </Button>
          <Button size="sm" variant="secondary" onClick={clearSelection} disabled={bulkRunning}>
            Limpiar
          </Button>
          {bulkRunning && bulkTotal > 0 && (
            <span className="text-xs text-muted-foreground">
              Procesando {bulkDone}/{bulkTotal}...
            </span>
          )}
          {!bulkRunning && bulkFailures.length > 0 && (
            <span className="text-xs" style={{ color: "oklch(0.6 0.2 25)" }}>
              {bulkFailures.length} error{bulkFailures.length === 1 ? "" : "es"}:{" "}
              {bulkFailures.slice(0, 3).map((f) => `#${f.id} (${f.message})`).join(", ")}
              {bulkFailures.length > 3 ? ` y ${bulkFailures.length - 3} más` : ""}. Quedan seleccionadas para reintentar.
            </span>
          )}
        </div>
      )}

      {filteredItems.length === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center">No hay reglas</p>
      ) : (
        <div className="rounded-lg border w-full" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
          <table className="w-full text-sm table-fixed">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                <th className="py-2 px-2 text-left w-[3%]">
                  <input
                    type="checkbox"
                    checked={allFilteredSelected}
                    onChange={() => toggleSelectAll(filteredIds)}
                    aria-label="Seleccionar reglas filtradas"
                    disabled={isRetiredView}
                    className="rounded border-gray-300 disabled:opacity-40"
                    style={{ accentColor: "oklch(0.55 0.04 160)" }}
                  />
                </th>
                <th className="py-2 px-2 text-left w-[4%]">#</th>
                <th className="py-2 px-2 text-left w-[20%]">Nombre</th>
                <th className="py-2 px-2 text-left w-[20%]">Descripción</th>
                <th className="py-2 px-2 text-left w-[9%]">Grupo error</th>
                <th className="py-2 px-2 text-left w-[8%]">Dominio</th>
                <th className="py-2 px-2 text-left w-[8%]">Estado</th>
                <th className="py-2 px-2 text-left w-[6%]">Prioridad</th>
                <th className="py-2 px-2 text-left w-[8%]">Severidad</th>
                <th className="py-2 px-2 text-left w-[14%]">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => (
                <tr key={item.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                  <td className="py-2 px-2">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(item.id)}
                      onChange={() => toggleSelectId(item.id)}
                      aria-label={`Seleccionar regla ${item.nombre}`}
                      disabled={isRetiredView}
                      className="rounded border-gray-300 disabled:opacity-40"
                      style={{ accentColor: "oklch(0.55 0.04 160)" }}
                    />
                  </td>
                  <td className="py-2 px-2 text-xs text-muted-foreground font-mono break-all align-top" style={{ color: "oklch(0.55 0.04 160)" }}>{item.id}</td>
                  <td className="py-2 px-2 font-medium cursor-pointer whitespace-normal break-words align-top" style={{ color: "oklch(0.15 0.02 160)" }}
                      title={item.nombre}
                      onClick={() => handleViewDetail(item)}>
                    {item.nombre}
                  </td>
                  <td className="py-2 px-2 whitespace-normal break-words text-muted-foreground align-top"
                      title={item.descripcion ?? ""}>
                    {item.descripcion ?? "—"}
                  </td>
                  <td className="py-2 px-2 whitespace-normal break-words align-top" style={{ color: "oklch(0.55 0.04 160)" }}
                      title={item.grupo_error ?? ""}>
                    {item.grupo_error ?? "—"}
                  </td>
                  <td className="py-2 px-2 whitespace-normal break-words align-top" style={{ color: "oklch(0.55 0.04 160)" }}><DominiosBadges dominios={getRuleDominios(item)} /></td>
                  <td className="py-2 px-2 align-top"><EstadoBadge estado={item.estado} activo={item.activo} /></td>
                  <td className="py-2 px-2 align-top">{item.prioridad}</td>
                  <td className="py-2 px-2 align-top"><SeveridadBadge severidad={item.severidad} /></td>
                  <td className="py-2 px-2 align-top">
                    <div className="flex flex-wrap gap-1">
                      <Button size="sm" variant="default" onClick={() => handleViewDetail(item)}>
                        <Eye className="h-3.5 w-3.5" />
                        Ver
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => handleDuplicate(item)}>
                        Duplicar
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
              if (createFormDominios.length === 0) { setCreateError("Seleccioná al menos un dominio"); return; }
              setCreateSaving(true);
              try {
                await createRegla({
                  nombre: createFormNombre.trim(),
                  descripcion: createFormDesc.trim() || null,
                  ...buildDominiosPayload(createFormDominios),
                  severidad: createFormSev,
                  prioridad: Number(createFormPrio),
                });
                setShowCreate(false);
                setCreateFormNombre("");
                setCreateFormDesc("");
                setCreateFormDominios(["odontologia"]);
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
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>Dominios</label>
                  <DominioScopeEditor selected={createFormDominios} onChange={setCreateFormDominios} />
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
  const [dominios, setDominios] = useState<string[]>(() => getRuleDominios(rule));
  const [severidad, setSeveridad] = useState(rule.severidad);
  const [prioridad, setPrioridad] = useState(String(rule.prioridad));
  const [grupoError, setGrupoError] = useState(rule.grupo_error ?? "");
  const [detalleACampo, setDetalleACampo] = useState(rule.detalle_a_campo ?? "");
  const [detalleBCampo, setDetalleBCampo] = useState(rule.detalle_b_campo ?? "");
  const [descripcionTemplate, setDescripcionTemplate] = useState(
    rule.descripcion_template ?? ""
  );
  const handleGroupingChange = (field: string, value: string) => {
    if (field === "grupo_error") setGrupoError(value);
    else if (field === "detalle_a_campo") setDetalleACampo(value);
    else if (field === "detalle_b_campo") setDetalleBCampo(value);
    else if (field === "descripcion_template") setDescripcionTemplate(value);
  };
  const [parametros, setParametros] = useState(
    rule.parametros ? JSON.stringify(rule.parametros, null, 2) : ""
  );
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [catalogOptions, setCatalogOptions] = useState<string[]>([]);

  useEffect(() => {
    fetchCatalogos()
      .then((catalogos) => setCatalogOptions(catalogos.map((catalogo) => catalogo.key)))
      .catch(() => setCatalogOptions([]));
  }, []);

  // Editable condition tree state
  const [tree, setTree] = useState<CondicionTree[]>(() => {
    if (rule.condiciones && rule.condiciones.length > 0) {
      return JSON.parse(JSON.stringify(rule.condiciones));
    }
    // Default: empty root AND composite
    return [{ id: 1, tipo: "composite", operador: "AND", fuente_datos: null, valor_esperado: null, condiciones: [], regla_id: 0, padre_id: null, orden: 0 }];
  });

  const isReadOnly = rule.estado === "retired";
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre.trim()) {
      setFormError("El nombre no puede estar vacío");
      return;
    }
    if (dominios.length === 0) {
      setFormError("Seleccioná al menos un dominio");
      return;
    }
    const conditionError = validateConditionTree(tree);
    if (conditionError) {
      setFormError(conditionError);
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
        ...buildDominiosPayload(dominios),
        severidad,
        prioridad: Number(prioridad),
          grupo_error: grupoError.trim() || null,
          detalle_a_campo: detalleACampo.trim() || null,
          detalle_b_campo: detalleBCampo.trim() || null,
          descripcion_template: descripcionTemplate.trim() || null,
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
      <Card className="p-6 border shadow-none overflow-visible" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Button size="sm" variant="secondary" onClick={onBack}>
              ← Volver
            </Button>
            <h2 className="font-display font-semibold" style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}>
              {rule.nombre} <span className="text-xs font-mono text-muted-foreground">(#{rule.id})</span>
            </h2>
            <EstadoBadge estado={rule.estado} />
          </div>
          <div className="flex gap-2">
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
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
                Dominios
              </label>
              <DominioScopeEditor selected={dominios} onChange={setDominios} disabled={isReadOnly} />
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

          <GroupingFields
            grupoError={grupoError}
            detalleACampo={detalleACampo}
            detalleBCampo={detalleBCampo}
            descripcionTemplate={descripcionTemplate}
            disabled={isReadOnly}
            onChange={handleGroupingChange}
          />

          <div className="flex items-center gap-2 mb-4">
            <span className="text-sm font-medium" style={{ color: "oklch(0.55 0.04 160)" }}>
              Activación: {rule.activo ? "Activa" : "Inactiva"} (se gestiona desde el listado)
            </span>
          </div>

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
            <ConditionTreeEditor
              tree={tree}
              onChange={setTree}
              readOnly={isReadOnly}
              catalogOptions={catalogOptions}
            />
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

    </>
  );
}

// ═════════════════════════════════════════════════════════════════════
// CATALOGOS LIST VIEW
// ═════════════════════════════════════════════════════════════════════

function DominioBadge({ dominio }: { dominio: string | null }) {
  if (!dominio) return <span className="text-xs text-muted-foreground">—</span>;
  const color = DOMINIO_COLORS[dominio] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {dominio}
    </span>
  );
}

function CountBadge({ count, variant }: { count: number; variant: "rules" | "items" }) {
  const colors = variant === "rules"
    ? "bg-blue-100 text-blue-700"
    : "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors}`}>
      {count}
    </span>
  );
}

function CatalogosListView() {
  const [items, setItems] = useState<CatalogoListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [editItem, setEditItem] = useState<CatalogoListItem | null>(null);
  const [deleteItem, setDeleteItem] = useState<CatalogoListItem | null>(null);
  const [reglasItem, setReglasItem] = useState<CatalogoListItem | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCatalogos();
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar catálogos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filteredItems = (searchTerm
    ? items.filter((c) =>
        c.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.descripcion ?? "").toLowerCase().includes(searchTerm.toLowerCase())
      )
    : items
  ).sort((a, b) => a.key.localeCompare(b.key));

  if (loading) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        <span className="text-sm text-muted-foreground">Cargando catálogos...</span>
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
            Catálogos ({filteredItems.length})
          </h2>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            Nuevo Catálogo
          </Button>
        </div>

        <div className="flex flex-wrap gap-3 mb-4">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "oklch(0.55 0.04 160)" }} />
            <input
              type="text"
              placeholder="Buscar por key o descripción..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-lg border pl-9 pr-4 py-1.5 text-sm outline-none"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
            />
          </div>
        </div>

        {filteredItems.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">No hay catálogos</p>
        ) : (
          <div className="rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
            <table className="w-full text-sm table-fixed">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                  <th className="py-3 px-4 text-left">Key</th>
                  <th className="py-3 px-4 text-left">Descripción</th>
                  <th className="py-3 px-4 text-left w-28">Dominio</th>
                  <th className="py-3 px-4 text-left w-28">Valores</th>
                  <th className="py-3 px-4 text-left w-20">#</th>
                  <th className="py-3 px-4 text-left w-20">Reglas</th>
                  <th className="py-3 px-4 text-left w-64">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.key} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                    <td className="py-3 px-4 font-medium font-mono text-xs" style={{ color: "oklch(0.15 0.02 160)" }}>
                      {item.key}
                    </td>
                    <td className="py-3 px-4 truncate max-w-[200px]" style={{ color: "oklch(0.55 0.04 160)" }} title={item.descripcion ?? ""}>
                      {item.descripcion ?? "—"}
                    </td>
                    <td className="py-3 px-4"><DominioBadge dominio={item.dominio} /></td>
                    <td className="py-3 px-4 truncate max-w-[150px] text-xs font-mono" style={{ color: "oklch(0.55 0.04 160)" }} title={JSON.stringify(item.value)}>
                      {item.value && item.value.length > 0
                        ? item.value.slice(0, 3).join(", ") + (item.value.length > 3 ? "..." : "")
                        : "—"}
                    </td>
                    <td className="py-3 px-4"><CountBadge count={item.value_count} variant="items" /></td>
                    <td className="py-3 px-4"><CountBadge count={item.regla_count} variant="rules" /></td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <Button size="sm" variant="secondary" onClick={() => setEditItem(item)} title="Editar">
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setReglasItem(item)} title="Ver reglas vinculadas">
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => setDeleteItem(item)} title="Eliminar">
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

      {showCreate && (
        <CatalogoDialog
          mode="create"
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); load(); }}
        />
      )}

      {editItem && (
        <CatalogoDialog
          mode="edit"
          catalogKey={editItem.key}
          initialData={{
            value: editItem.value ?? [],
            descripcion: editItem.descripcion ?? "",
            dominio: editItem.dominio ?? "",
          }}
          onClose={() => setEditItem(null)}
          onSaved={() => { setEditItem(null); load(); }}
        />
      )}

      {deleteItem && (
        <DeleteConfirmDialog
          catalogKey={deleteItem.key}
          reglaCount={deleteItem.regla_count}
          onClose={() => setDeleteItem(null)}
          onDeleted={() => { setDeleteItem(null); load(); }}
        />
      )}

      {reglasItem && (
        <ReglasVinculadas
          catalogKey={reglasItem.key}
          onClose={() => setReglasItem(null)}
        />
      )}
    </>
  );
}

// ═════════════════════════════════════════════════════════════════════
// CATALOGO DIALOG (Create / Edit)
// ═════════════════════════════════════════════════════════════════════

interface CatalogoDialogProps {
  mode: "create" | "edit";
  catalogKey?: string;
  initialData?: {
    value: string[];
    descripcion: string | null;
    dominio: string | null;
  };
  onClose: () => void;
  onSaved: () => void;
}

function CatalogoDialog({ mode, catalogKey, initialData, onClose, onSaved }: CatalogoDialogProps) {
  const isEdit = mode === "edit";

  const [key, setKey] = useState(catalogKey ?? "");
  const [descripcion, setDescripcion] = useState(initialData?.descripcion ?? "");
  const [dominio, setDominio] = useState(initialData?.dominio ?? "");
  const [tags, setTags] = useState<string[]>(initialData?.value ?? []);
  const [tagInput, setTagInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleAddTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
    }
    setTagInput("");
  };

  const handleRemoveTag = (index: number) => {
    setTags(tags.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!isEdit && !key.trim()) {
      setFormError("El key es obligatorio");
      return;
    }

    setSaving(true);
    try {
      if (isEdit && catalogKey) {
        await updateCatalogo(catalogKey, {
          value: tags,
          descripcion: descripcion.trim() || undefined,
          dominio: dominio.trim() || undefined,
        });
      } else {
        await createCatalogo({
          key: key.trim(),
          value: tags,
          descripcion: descripcion.trim() || undefined,
          dominio: dominio.trim() || undefined,
        });
      }
      onSaved();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
            {isEdit ? "Editar Catálogo" : "Nuevo Catálogo"}
          </h2>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-gray-100">
            <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {formError && (
            <p className="text-xs mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{formError}</p>
          )}

          <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
            Key
          </label>
          <input
            type="text"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            className="w-full rounded-lg border px-4 py-2.5 text-sm mb-3 outline-none"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
            disabled={isEdit}
            required={!isEdit}
            placeholder={isEdit ? "Key no modificable" : "ej: profesiones_medicas"}
          />
          {isEdit && (
            <p className="text-xs text-muted-foreground -mt-2 mb-3">El key no se puede modificar después de crear el catálogo.</p>
          )}

          <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
            Descripción
          </label>
          <input
            type="text"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            className="w-full rounded-lg border px-4 py-2.5 text-sm mb-3 outline-none"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
            placeholder="Descripción opcional"
          />

          <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
            Dominio
          </label>
          <select
            value={dominio}
            onChange={(e) => setDominio(e.target.value)}
            className="w-full rounded-lg border px-4 py-2.5 text-sm mb-3 outline-none"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
          >
            <option value="">Sin dominio</option>
            <option value="odontologia">Odontología</option>
            <option value="urgencias">Urgencias</option>
            <option value="equipos_basicos">Equipos Básicos</option>
            <option value="transversal">Transversal</option>
            <option value="farmacia">Farmacia</option>
            <option value="intramural">Intramural</option>
            <option value="hospitalizacion">Hospitalización</option>
            <option value="ambulatoria">Ambulatoria</option>
          </select>

          <label className="block text-sm font-medium mb-1" style={{ color: "oklch(0.55 0.04 160)" }}>
            Valores (tag array)
          </label>
          <div className="flex items-center gap-2 mb-2">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 rounded-lg border px-4 py-2 text-sm outline-none"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
              placeholder="Escribí un valor y presioná Enter"
            />
            <Button type="button" size="sm" variant="secondary" onClick={handleAddTag}>
              +
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 mb-4 p-3 rounded-lg border min-h-[48px]" style={{ borderColor: "oklch(0.55 0.04 160 / 0.15)" }}>
            {tags.length === 0 ? (
              <span className="text-xs text-muted-foreground">Sin valores — agregá elementos con el campo de arriba</span>
            ) : (
              tags.map((tag, i) => (
                <span key={i}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                  {tag}
                  <button type="button" onClick={() => handleRemoveTag(i)} className="hover:text-red-500">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))
            )}
          </div>

          <div className="flex gap-2 justify-end mt-4">
            <Button type="submit" disabled={saving}>
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
              {isEdit ? "Guardar Cambios" : "Crear Catálogo"}
            </Button>
            <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════
// DELETE CONFIRM DIALOG
// ═════════════════════════════════════════════════════════════════════

interface DeleteConfirmDialogProps {
  catalogKey: string;
  reglaCount: number;
  onClose: () => void;
  onDeleted: () => void;
}

function DeleteConfirmDialog({ catalogKey, reglaCount, onClose, onDeleted }: DeleteConfirmDialogProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blockingRules, setBlockingRules] = useState<Array<{ regla_id: number; nombre: string; estado: string }> | null>(null);

  const handleDelete = async () => {
    setDeleting(true);
    setError(null);
    try {
      await deleteCatalogo(catalogKey);
      onDeleted();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al eliminar";
      if (msg.includes("No se puede eliminar")) {
        try {
          const reglas = await fetchCatalogoReglas(catalogKey);
          setBlockingRules(
            reglas
              .filter((r) => r.estado === "active")
              .map((r) => ({ regla_id: r.id, nombre: r.nombre, estado: r.estado }))
          );
        } catch {
          // ignore secondary error
        }
      }
      setError(msg);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
         onClick={(e) => { if (e.target === e.currentTarget && !deleting) onClose(); }}>
      <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-md mx-4">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="h-6 w-6 text-amber-500" />
          <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
            Eliminar Catálogo
          </h2>
        </div>

        <p className="text-sm mb-2">
          ¿Estás seguro de eliminar el catálogo <strong>{catalogKey}</strong>?
        </p>

        {reglaCount > 0 && (
          <div className="p-3 rounded-lg mb-4 text-sm" style={{ backgroundColor: "oklch(0.6 0.2 45 / 0.08)", color: "oklch(0.5 0.2 45)" }}>
            <AlertTriangle className="h-4 w-4 inline mr-1" />
            {reglaCount} regla(s) referencian este catálogo. Se permitirá la eliminación solo si no hay reglas activas.
          </div>
        )}

        {blockingRules && blockingRules.length > 0 && (
          <div className="p-3 rounded-lg mb-4 border border-red-200" style={{ backgroundColor: "oklch(0.6 0.2 25 / 0.08)" }}>
            <p className="text-xs font-semibold text-red-700 mb-2">Reglas activas que bloquean la eliminación:</p>
            <ul className="text-xs space-y-1">
              {blockingRules.map((r) => (
                <li key={r.regla_id} className="text-red-600">
                  #{r.regla_id} — {r.nombre}
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && !blockingRules && (
          <p className="text-xs mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>{error}</p>
        )}

        <div className="flex gap-2 justify-end">
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={deleting || (blockingRules !== null && blockingRules.length > 0)}
          >
            {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
            Eliminar
          </Button>
          <Button size="sm" variant="secondary" onClick={onClose} disabled={deleting}>Cancelar</Button>
        </div>
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════
// REGLAS VINCULADAS MODAL
// ═════════════════════════════════════════════════════════════════════

interface ReglasVinculadasProps {
  catalogKey: string;
  onClose: () => void;
}

function ReglasVinculadas({ catalogKey, onClose }: ReglasVinculadasProps) {
  const [items, setItems] = useState<ReglaRef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await fetchCatalogoReglas(catalogKey);
        setItems(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error al cargar reglas");
      } finally {
        setLoading(false);
      }
    })();
  }, [catalogKey]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-xl mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
            Reglas que referencian <span className="font-mono text-sm">{catalogKey}</span>
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
          <p className="text-sm text-muted-foreground py-8 text-center">Ninguna regla referencia este catálogo.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
                  <th className="py-2 px-3 text-left">#</th>
                  <th className="py-2 px-3 text-left">Nombre</th>
                  <th className="py-2 px-3 text-left">Dominio</th>
                  <th className="py-2 px-3 text-left">Estado</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id} className="border-b" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}>
                    <td className="py-2 px-3 font-mono text-xs text-muted-foreground">{r.id}</td>
                    <td className="py-2 px-3 font-medium" style={{ color: "oklch(0.15 0.02 160)" }}>{r.nombre}</td>
                    <td className="py-2 px-3"><DominiosBadges dominios={getRuleDominios(r)} /></td>
                    <td className="py-2 px-3"><EstadoBadge estado={r.estado} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
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
  const [detailItem, setDetailItem] = useState<EvidenciaItem | AuditItem | null>(null);
  const [detailType, setDetailType] = useState<"evidencia" | "auditoria">("evidencia");
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
        <Button size="sm" variant="destructive" onClick={async () => {
          if (!window.Modal) return;
          const ok = await window.Modal.confirm("ACCION DE PRUEBA - Se borraran TODOS los registros de evidencia y auditoria.\n\nSeguro?");
          if (!ok) return;
          try {
            const resp = await fetch("/api/evidencias", { method: "DELETE" });
            const json = await resp.json();
            if (json.status !== "success") throw new Error(json.errors?.[0] || "Error");
            setResults(null);
            setError("Datos eliminados (solo para pruebas)");
          } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Error al limpiar");
          }
        }}>
          <Trash2 className="h-3.5 w-3.5 mr-1" />
          Limpiar datos
        </Button>
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
                    <tr key={item.id} className="border-b cursor-pointer hover:bg-gray-50" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}
                        onClick={() => { setDetailItem(item); setDetailType("evidencia"); }}>
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
                    <tr key={item.id} className="border-b cursor-pointer hover:bg-gray-50" style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}
                        onClick={() => { setDetailItem(item); setDetailType("auditoria"); }}>
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

      {/* Detail overlay */}
      {detailItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
             onClick={() => setDetailItem(null)}>
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto"
               onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-semibold text-lg" style={{ color: "oklch(0.15 0.02 160)" }}>
                {detailType === "evidencia" ? "Evidencia" : "Auditoría"} — #{detailItem.id}
              </h2>
              <button onClick={() => setDetailItem(null)} className="p-1 rounded-md hover:bg-gray-100">
                <X className="h-5 w-5" style={{ color: "oklch(0.55 0.04 160)" }} />
              </button>
            </div>

            {/* Basic info */}
            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
              <div><span className="font-medium">Factura:</span> {(detailItem as any).factura}</div>
              <div><span className="font-medium">Regla ID:</span> #{(detailItem as any).regla_id}</div>
              <div><span className="font-medium">Creado:</span> {(detailItem as any).creado_en?.slice(0, 19) ?? "—"}</div>
              {detailType === "evidencia" && (
                <>
                  <div><span className="font-medium">Outcome:</span> {(detailItem as EvidenciaItem).outcome}</div>
                  <div><span className="font-medium">Dominio:</span> {(detailItem as EvidenciaItem).dominio}</div>
                </>
              )}
              {detailType === "auditoria" && (
                <>
                  <div><span className="font-medium">Resultado:</span> {(detailItem as AuditItem).resultado}</div>
                  <div><span className="font-medium">Severidad:</span> {(detailItem as AuditItem).severidad}</div>
                  <div className="col-span-2"><span className="font-medium">Mensaje:</span> {(detailItem as AuditItem).mensaje ?? "—"}</div>
                </>
              )}
            </div>

            {/* Trace / Details */}
            {detailType === "evidencia" && (detailItem as EvidenciaItem).arbol_evaluado && (
              <div className="mb-3">
                <h3 className="text-sm font-semibold mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>Árbol evaluado (traza)</h3>
                <pre className="text-xs font-mono bg-gray-50 p-3 rounded-lg overflow-x-auto max-h-48"
                     style={{ border: "1px solid oklch(0.55 0.04 160 / 0.1)" }}>
                  {JSON.stringify((detailItem as EvidenciaItem).arbol_evaluado, null, 2)}
                </pre>
              </div>
            )}

            {detailType === "auditoria" && (detailItem as AuditItem).detalles && (
              <div className="mb-3">
                <h3 className="text-sm font-semibold mb-2" style={{ color: "oklch(0.55 0.04 160)" }}>Detalles adicionales</h3>
                <pre className="text-xs font-mono bg-gray-50 p-3 rounded-lg overflow-x-auto max-h-48"
                     style={{ border: "1px solid oklch(0.55 0.04 160 / 0.1)" }}>
                  {JSON.stringify((detailItem as AuditItem).detalles, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex justify-end mt-4">
              <Button size="sm" variant="secondary" onClick={() => setDetailItem(null)}>Cerrar</Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

// ═════════════════════════════════════════════════════════════════════
// SIMULATOR VIEW
// ═════════════════════════════════════════════════════════════════════

function SimulatorView() {
  // Solo admin llega acá (@admin_requerido). can_write/canControl se derivan
  // de los permisos igual que en /procesar (admin trae "*").
  const initialData = (
    window as unknown as {
      __INITIAL_DATA__?: { permisos?: string[] };
    }
  ).__INITIAL_DATA__;
  const permisos = initialData?.permisos ?? [];
  const canControl = hasControlWrite(permisos);
  const can_write = permisos.includes("*");

  const [rules, setRules] = useState<Regla[]>([]);
  const [rulesLoading, setRulesLoading] = useState(true);
  const [rulesError, setRulesError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [dominioFilter, setDominioFilter] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [exportId, setExportId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Todas las reglas (activas preseleccionadas). Las inactivas también se
  // pueden simular: el scope del simulador las evalúa sin activarlas.
  useEffect(() => {
    fetchReglas()
      .then((items) => {
        setRules(items);
        setSelected(new Set(items.filter((r) => r.activo).map((r) => r.id)));
      })
      .catch((e) =>
        setRulesError(e instanceof Error ? e.message : "Error cargando reglas"),
      )
      .finally(() => setRulesLoading(false));
  }, []);

  const filteredRules = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rules.filter((r) => {
      if (!showInactive && !r.activo) return false;
      if (dominioFilter && !ruleMatchesDominio(r, dominioFilter)) return false;
      if (!q) return true;
      return (
        r.nombre.toLowerCase().includes(q) ||
        (r.descripcion ?? "").toLowerCase().includes(q)
      );
    });
  }, [rules, search, dominioFilter, showInactive]);

  const toggleRule = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () =>
    setSelected(new Set(rules.filter((r) => r.activo).map((r) => r.id)));
  const selectNone = () => setSelected(new Set());
  const selectVisible = () =>
    setSelected((prev) => {
      const next = new Set(prev);
      for (const r of filteredRules) next.add(r.id);
      return next;
    });

  // ── Envío a Control (mismo hook que /procesar) ──
  const markEnviada = useCallback((factura: string) => {
    setResult((prev) =>
      prev
        ? {
            ...prev,
            errores: prev.errores.map((fg) => ({
              ...fg,
              tipos: fg.tipos.map((tg) => ({
                ...tg,
                facturas: tg.facturas.map((x) =>
                  norm(x.factura) === norm(factura)
                    ? { ...x, _enviada: true }
                    : x,
                ),
              })),
            })),
          }
        : prev,
    );
  }, []);

  const {
    showEnvio,
    envioExistentes,
    envioEnviadas,
    envioVersion,
    toastMessage,
    setToastMessage,
    handleSendToControl,
  } = useEnvioControl({ can_write, canControl, onEnviada: markEnviada });

  const isExcel = (f: File) =>
    f.name.endsWith(".xlsx") || f.name.endsWith(".xls") || f.name.endsWith(".xlsm");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) {
      setFile(null);
      return;
    }
    if (!isExcel(f)) {
      setError("Formato no válido. Seleccioná un archivo Excel (.xlsx, .xls, .xlsm).");
      setFile(null);
      return;
    }
    setError(null);
    setFile(f);
    setResult(null);
    setExportId(null);
  };

  const handleSimulate = async () => {
    if (!file) {
      setError("Seleccioná un archivo Excel primero");
      return;
    }
    if (selected.size === 0) {
      setError("Elegí al menos una regla para probar");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await simulateReglas(file, [...selected]);
      setResult(data);
      setExportId(data.export_id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al simular");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {toastMessage && (
        <Toast message={toastMessage} onDone={() => setToastMessage(null)} />
      )}
      <Card
        className="p-6 border shadow-none"
        style={{
          borderColor: "oklch(0.55 0.04 160 / 0.1)",
          background: "white",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2
            className="font-display font-semibold"
            style={{ color: "oklch(0.15 0.02 160)", fontSize: "1rem" }}
          >
            Simulador de Reglas
          </h2>
        </div>

        <p className="text-sm text-muted-foreground mb-4">
          Corre el pipeline real de /procesar sobre todo el archivo (sin límite
          de filas) pero solo con las reglas que selecciones. No guarda
          evidencia ni envía nada solo: el envío a Control es por fila, igual
          que en /procesar.
        </p>

        {/* File upload */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
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
            accept=".xlsx,.xls,.xlsm"
            onChange={handleFileChange}
            className="hidden"
          />
          <Button size="sm" onClick={handleSimulate} disabled={loading || !file || selected.size === 0}>
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
            ) : (
              <Play className="h-3.5 w-3.5 mr-1" />
            )}
            Simular ({selected.size} {selected.size === 1 ? "regla" : "reglas"})
          </Button>
        </div>

        {error && (
          <p className="text-sm mb-3" style={{ color: "oklch(0.6 0.2 25)" }}>
            {error}
          </p>
        )}

        {/* Rule selector */}
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-52">
            <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Buscar regla por nombre o descripción…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border pl-8 pr-3 py-2 text-sm outline-none"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
            />
          </div>
          <select
            value={dominioFilter}
            onChange={(e) => setDominioFilter(e.target.value)}
            className="rounded-lg border px-3 py-2 text-sm outline-none bg-white"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
          >
            <option value="">Todos los dominios</option>
            {DOMINIOS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="h-3.5 w-3.5 accent-emerald-700"
            />
            Mostrar inactivas
          </label>
          <Button size="sm" variant="outline" onClick={selectAll}>
            Todas
          </Button>
          <Button size="sm" variant="outline" onClick={selectVisible}>
            Visibles
          </Button>
          <Button size="sm" variant="outline" onClick={selectNone}>
            Ninguna
          </Button>
        </div>

        <p className="text-xs text-muted-foreground mb-2">
          {selected.size} de {rules.length} reglas seleccionadas
          {result && result.reglas_aplicadas.length > 0 && (
            <> · última simulación: {result.reglas_aplicadas.length} reglas</>
          )}
        </p>

        {rulesLoading ? (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Cargando reglas…
          </div>
        ) : rulesError ? (
          <p className="text-sm py-4" style={{ color: "oklch(0.6 0.2 25)" }}>
            {rulesError}
          </p>
        ) : (
          <div
            className="overflow-y-auto rounded-lg border max-h-72"
            style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)" }}
          >
            {filteredRules.length === 0 ? (
              <p className="text-xs text-muted-foreground p-4">
                Sin reglas para este filtro.
              </p>
            ) : (
              filteredRules.map((r) => (
                <label
                  key={r.id}
                  className="flex items-center gap-3 px-3 py-2 border-b cursor-pointer hover:bg-gray-50"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.05)" }}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(r.id)}
                    onChange={() => toggleRule(r.id)}
                    className="h-4 w-4 accent-emerald-700"
                  />
                  <span className="font-mono text-xs font-medium flex-1 truncate" title={r.descripcion ?? r.nombre}>
                    {r.nombre}
                  </span>
                  {!r.activo && <EstadoBadge estado={r.estado} activo={r.activo} />}
                  <DominiosBadges dominios={getRuleDominios(r)} />
                  <span className="text-[11px] text-muted-foreground shrink-0">
                    #{r.id} · v{r.version}
                  </span>
                </label>
              ))
            )}
          </div>
        )}
      </Card>

      {/* Results — same component as /procesar */}
      {result && result.total_errores > 0 && (
        <ResultadosProcesar
          errores={result.errores}
          totalErrores={result.total_errores}
          exportHref={exportId ? `/procesar/export?id=${exportId}` : null}
          showEnvio={showEnvio}
          envioExistentes={envioExistentes}
          envioEnviadas={envioEnviadas}
          envioVersion={envioVersion}
          onSendToControl={handleSendToControl}
        />
      )}

      {result && result.total_errores === 0 && (
        <Card
          className="p-6 border shadow-none text-center"
          style={{
            borderColor: "oklch(0.55 0.04 160 / 0.1)",
            background: "white",
          }}
        >
          <p className="text-sm font-medium" style={{ color: "oklch(0.4 0.2 145)" }}>
            Sin errores para las reglas seleccionadas ✅
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Tipos procesados: {result.tipos_procesados.join(", ") || "—"}
          </p>
        </Card>
      )}
    </div>
  );
}
