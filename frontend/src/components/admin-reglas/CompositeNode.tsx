import { ChevronDown, ChevronRight, Plus, X } from "lucide-react";
import type { CondicionTree } from "@/lib/api-reglas";
import { OPERADORES_COMPOSITE } from "./operators";
import { AtomicNode } from "./AtomicNode";

// ─── Props ─────────────────────────────────────────────────────────

interface CompositeNodeProps {
  node: CondicionTree & { _collapsed?: boolean };
  depth: number;
  catalogOptions?: string[];
  readOnly?: boolean;
  onUpdate: (nodeId: number, field: string, value: unknown) => void;
  onAddChild: (parentId: number, tipo: "atomic" | "composite") => void;
  onRemove: (nodeId: number) => void;
  onToggleCollapse: (nodeId: number) => void;
}

// ─── Component ──────────────────────────────────────────────────────

export function CompositeNode({
  node,
  depth,
  catalogOptions,
  readOnly,
  onUpdate,
  onAddChild,
  onRemove,
  onToggleCollapse,
}: CompositeNodeProps) {
  const collapsed = node._collapsed ?? false;
  const children = node.condiciones ?? [];
  const indent = depth * 20;

  if (readOnly) {
    return (
      <div className="mb-2" style={{ marginLeft: `${indent}px` }}>
        <div
          className="flex items-center gap-2 p-2 rounded-md text-sm"
          style={{
            background: "oklch(0.55 0.04 160 / 0.06)",
            borderLeft: "3px solid oklch(0.55 0.04 160)",
          }}
        >
          <button
            type="button"
            onClick={() => onToggleCollapse(node.id)}
            className="p-0.5 rounded hover:bg-gray-200"
          >
            {collapsed ? (
              <ChevronRight className="h-3 w-3" style={{ color: "oklch(0.55 0.04 160)" }} />
            ) : (
              <ChevronDown className="h-3 w-3" style={{ color: "oklch(0.55 0.04 160)" }} />
            )}
          </button>
          <span className="font-semibold text-xs uppercase tracking-wider" style={{ color: "oklch(0.55 0.04 160)" }}>
            {node.operador ?? node.tipo}
          </span>
          <span className="text-xs text-muted-foreground ml-1">
            ({children.length} hijo{children.length !== 1 ? "s" : ""})
          </span>
        </div>

        {!collapsed && children.length > 0 && (
          <div className="ml-2 mt-1">
            {children.map((child) => (
              <NodeRenderer
                key={child.id}
                node={child}
                depth={depth + 1}
                catalogOptions={catalogOptions}
                readOnly={readOnly}
                onUpdate={onUpdate}
                onAddChild={onAddChild}
                onRemove={onRemove}
                onToggleCollapse={onToggleCollapse}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="mb-2" style={{ marginLeft: `${indent}px` }}>
      {/* Composite header row */}
      <div
        className="flex items-center gap-2 p-2 rounded-md text-sm"
        style={{
          background: "oklch(0.55 0.04 160 / 0.06)",
          borderLeft: "3px solid oklch(0.55 0.04 160)",
        }}
      >
        {/* Collapse toggle */}
        <button
          type="button"
          onClick={() => onToggleCollapse(node.id)}
          className="p-0.5 rounded hover:bg-gray-200"
          title={collapsed ? "Expandir" : "Colapsar"}
        >
          {collapsed ? (
            <ChevronRight className="h-3 w-3" style={{ color: "oklch(0.55 0.04 160)" }} />
          ) : (
            <ChevronDown className="h-3 w-3" style={{ color: "oklch(0.55 0.04 160)" }} />
          )}
        </button>

        {/* AND/OR/NOT select */}
        <select
          value={node.operador ?? "AND"}
          onChange={(e) => onUpdate(node.id, "operador", e.target.value)}
          className="text-xs font-semibold uppercase border rounded px-2 py-1 outline-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.3)" }}
        >
          {OPERADORES_COMPOSITE.map((op) => (
            <option key={op} value={op}>{op}</option>
          ))}
        </select>

        <span className="text-xs text-muted-foreground">
          ({children.length} hijo{children.length !== 1 ? "s" : ""})
        </span>

        {/* Add Atomic child */}
        <button
          type="button"
          onClick={() => onAddChild(node.id, "atomic")}
          className="ml-auto px-2 py-1 text-xs rounded hover:bg-gray-100 flex items-center gap-1"
          style={{ color: "oklch(0.55 0.04 160)" }}
          title="Agregar condición atómica"
        >
          <Plus className="h-3 w-3" />
          Atómico
        </button>

        {/* Add Composite child */}
        <button
          type="button"
          onClick={() => onAddChild(node.id, "composite")}
          className="px-2 py-1 text-xs rounded hover:bg-gray-100 flex items-center gap-1"
          style={{ color: "oklch(0.55 0.04 160)" }}
          title="Agregar condición compuesta"
        >
          <Plus className="h-3 w-3" />
          Compuesto
        </button>

        {/* Remove button */}
        <button
          type="button"
          onClick={() => onRemove(node.id)}
          className="p-1 rounded hover:bg-red-50"
          title="Eliminar"
          style={{ color: "oklch(0.6 0.2 25)" }}
        >
          <X className="h-3 w-3" />
        </button>
      </div>

      {/* Children (only if not collapsed) */}
      {!collapsed && children.length > 0 && (
        <div className="ml-2 mt-1">
          {children.map((child) => (
            <NodeRenderer
              key={child.id}
                node={child}
                depth={depth + 1}
                catalogOptions={catalogOptions}
              readOnly={readOnly}
              onUpdate={onUpdate}
              onAddChild={onAddChild}
              onRemove={onRemove}
              onToggleCollapse={onToggleCollapse}
            />
          ))}
        </div>
      )}

      {!collapsed && children.length === 0 && (
        <p className="text-xs text-muted-foreground ml-6 mt-1 italic">
          Sin condiciones. Usá [+ Atómico] o [+ Compuesto] para agregar.
        </p>
      )}
    </div>
  );
}

// ─── Node Renderer (atomic vs composite dispatch) ───────────────────

interface NodeRendererProps {
  node: CondicionTree & { _collapsed?: boolean };
  depth: number;
  catalogOptions?: string[];
  readOnly?: boolean;
  onUpdate: (nodeId: number, field: string, value: unknown) => void;
  onAddChild: (parentId: number, tipo: "atomic" | "composite") => void;
  onRemove: (nodeId: number) => void;
  onToggleCollapse: (nodeId: number) => void;
}

function NodeRenderer({
  node,
  depth,
  catalogOptions,
  readOnly,
  onUpdate,
  onAddChild,
  onRemove,
  onToggleCollapse,
}: NodeRendererProps) {
  const isComposite =
    node.tipo === "composite" || node.tipo === "AND" || node.tipo === "OR" || node.tipo === "NOT";

  if (isComposite) {
    return (
      <CompositeNode
        node={node}
        depth={depth}
        catalogOptions={catalogOptions}
        readOnly={readOnly}
        onUpdate={onUpdate}
        onAddChild={onAddChild}
        onRemove={onRemove}
        onToggleCollapse={onToggleCollapse}
      />
    );
  }

  return (
    <AtomicNode
      node={node}
      catalogOptions={catalogOptions}
      readOnly={readOnly}
      onUpdate={onUpdate}
      onRemove={onRemove}
    />
  );
}
