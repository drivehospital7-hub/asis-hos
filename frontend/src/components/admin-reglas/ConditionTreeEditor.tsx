import { useReducer, useEffect, useRef } from "react";
import type { CondicionTree } from "@/lib/api-reglas";
import { CompositeNode } from "./CompositeNode";

// ─── Types ──────────────────────────────────────────────────────────

type TreeNode = CondicionTree & { _collapsed?: boolean };
type ReducerState = TreeNode[];

type Action =
  | { type: "LOAD_TREE"; payload: CondicionTree[] }
  | { type: "ADD_CHILD"; payload: { parentId: number; tipo: "atomic" | "composite" } }
  | { type: "UPDATE_NODE"; payload: { nodeId: number; field: string; value: unknown } }
  | { type: "REMOVE_NODE"; payload: { nodeId: number } }
  | { type: "TOGGLE_COLLAPSE"; payload: { nodeId: number } }
  | { type: "REORDER_CHILDREN"; payload: { parentId: number; sourceIndex: number; destIndex: number } };

// ─── Reducer ────────────────────────────────────────────────────────

export function treeReducer(state: ReducerState, action: Action): ReducerState {
  switch (action.type) {
    case "LOAD_TREE":
      return hydrateTree(action.payload);

    case "ADD_CHILD": {
      const { parentId, tipo } = action.payload;
      const copy: TreeNode[] = JSON.parse(JSON.stringify(state));
      const newNode = createChildNode(parentId, tipo);
      if (tryAddChild(copy, parentId, newNode)) return copy;
      return state;
    }

    case "UPDATE_NODE": {
      const { nodeId, field, value } = action.payload;
      const copy: TreeNode[] = JSON.parse(JSON.stringify(state));
      updateNodeInTree(copy, nodeId, field, value);
      return copy;
    }

    case "REMOVE_NODE": {
      const { nodeId } = action.payload;
      const copy: TreeNode[] = JSON.parse(JSON.stringify(state));
      removeNodeFromTree(copy, nodeId);
      return copy;
    }

    case "TOGGLE_COLLAPSE": {
      const { nodeId } = action.payload;
      const copy: TreeNode[] = JSON.parse(JSON.stringify(state));
      toggleCollapseInTree(copy, nodeId);
      return copy;
    }

    case "REORDER_CHILDREN": {
      const { parentId, sourceIndex, destIndex } = action.payload;
      const copy: TreeNode[] = JSON.parse(JSON.stringify(state));
      reorderChildrenInTree(copy, parentId, sourceIndex, destIndex);
      return copy;
    }

    default:
      return state;
  }
}

// ─── Serialization ──────────────────────────────────────────────────

/** Strip `_collapsed` before sending to API. */
export function serializeTree(tree: CondicionTree[]): CondicionTree[] {
  return JSON.parse(JSON.stringify(tree), (_key, value) => {
    if (_key === "_collapsed") return undefined;
    return value;
  });
}

/** Add `_collapsed: false` to all composite nodes on load (R8 default expanded). */
export function hydrateTree(tree: CondicionTree[]): TreeNode[] {
  return JSON.parse(JSON.stringify(tree), (_key, value) => {
    if (
      value !== null &&
      typeof value === "object" &&
      "tipo" in value &&
      !("_collapsed" in value)
    ) {
      const isComposite =
        value.tipo === "composite" ||
        value.tipo === "AND" ||
        value.tipo === "OR" ||
        value.tipo === "NOT";
      if (isComposite) {
        return { ...value, _collapsed: false };
      }
    }
    return value;
  }) as TreeNode[];
}

// ─── Tree walk helpers (recursive, mutates copy) ───────────────────

function updateNodeInTree(
  nodes: TreeNode[],
  nodeId: number,
  field: string,
  value: unknown,
): boolean {
  for (const n of nodes) {
    if (n.id === nodeId) {
      (n as Record<string, unknown>)[field] = value;
      return true;
    }
    if (
      n.condiciones &&
      updateNodeInTree(n.condiciones as TreeNode[], nodeId, field, value)
    )
      return true;
  }
  return false;
}

function removeNodeFromTree(nodes: TreeNode[], nodeId: number): boolean {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i].id === nodeId) {
      nodes.splice(i, 1);
      return true;
    }
    if (
      nodes[i].condiciones &&
      removeNodeFromTree(nodes[i].condiciones as TreeNode[], nodeId)
    )
      return true;
  }
  return false;
}

function tryAddChild(
  nodes: TreeNode[],
  parentId: number,
  newNode: TreeNode,
): boolean {
  for (const n of nodes) {
    if (n.id === parentId) {
      if (!n.condiciones) n.condiciones = [];
      if (n.operador === "NOT" && n.condiciones.length >= 1) return false;
      n.condiciones.push(newNode);
      return true;
    }
    if (
      n.condiciones &&
      tryAddChild(n.condiciones as TreeNode[], parentId, newNode)
    )
      return true;
  }
  return false;
}

function toggleCollapseInTree(nodes: TreeNode[], nodeId: number): boolean {
  for (const n of nodes) {
    if (n.id === nodeId) {
      n._collapsed = !n._collapsed;
      return true;
    }
    if (
      n.condiciones &&
      toggleCollapseInTree(n.condiciones as TreeNode[], nodeId)
    )
      return true;
  }
  return false;
}

function reorderChildrenInTree(
  nodes: TreeNode[],
  parentId: number,
  sourceIndex: number,
  destIndex: number,
): boolean {
  for (const n of nodes) {
    if (n.id === parentId && n.condiciones) {
      const children = n.condiciones as TreeNode[];
      if (
        sourceIndex >= 0 &&
        sourceIndex < children.length &&
        destIndex >= 0 &&
        destIndex < children.length
      ) {
        const [moved] = children.splice(sourceIndex, 1);
        children.splice(destIndex, 0, moved);
      }
      return true;
    }
    if (
      n.condiciones &&
      reorderChildrenInTree(
        n.condiciones as TreeNode[],
        parentId,
        sourceIndex,
        destIndex,
      )
    )
      return true;
  }
  return false;
}

// ─── Node creation ──────────────────────────────────────────────────

let temporaryNodeId = Date.now() * 1000;

function createChildNode(
  parentId: number,
  tipo: "atomic" | "composite",
): TreeNode {
  // Keep temporary IDs within Number's safe integer range and unique per session.
  const id = ++temporaryNodeId;

  if (tipo === "composite") {
    return {
      id,
      regla_id: 0,
      padre_id: parentId,
      tipo: "composite",
      operador: "AND",
      fuente_datos: null,
      valor_esperado: null,
      orden: 0,
      condiciones: [],
      _collapsed: false,
    } as unknown as TreeNode;
  }

  return {
    id,
    regla_id: 0,
    padre_id: parentId,
    tipo: "atomic",
    operador: "eq",
    fuente_datos: "",
    valor_esperado: "",
    orden: 0,
  } as unknown as TreeNode;
}

/** Return a user-facing error when a NOT node has an invalid arity. */
export function validateConditionTree(tree: CondicionTree[]): string | null {
  for (const node of tree) {
    const children = node.condiciones ?? [];
    if (node.operador === "NOT" && children.length !== 1) {
      return "Each NOT condition must have exactly one child.";
    }
    const nestedError = validateConditionTree(children);
    if (nestedError) return nestedError;
  }
  return null;
}

// ─── Editor Component (Option A: parent owns state) ────────────────

interface ConditionTreeEditorProps {
  /** The tree of condition nodes (owned by parent). */
  tree: CondicionTree[];
  /** Called when tree changes — parent still owns state. */
  onChange: (updatedTree: CondicionTree[]) => void;
  /** Whether the tree is read-only. */
  readOnly?: boolean;
  catalogOptions?: string[];
}

export function ConditionTreeEditor({
  tree,
  onChange,
  readOnly,
  catalogOptions,
}: ConditionTreeEditorProps) {
  // Initialize reducer state from tree prop (lazy init — runs once per mount)
  const [state, dispatch] = useReducer(
    treeReducer,
    tree,
    (t) => hydrateTree(t ?? []),
  );

  // Stable callback ref to avoid re-triggering effects
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  // Skip the initial notification — parent already has the same tree.
  // Only notify after user-driven dispatches.
  const isMounted = useRef(false);
  useEffect(() => {
    if (!isMounted.current) {
      isMounted.current = true;
      return;
    }
    onChangeRef.current(serializeTree(state));
  }, [state]);

  const handleUpdate = (nodeId: number, field: string, value: unknown) => {
    dispatch({ type: "UPDATE_NODE", payload: { nodeId, field, value } });
  };

  const handleAddChild = (parentId: number, tipo: "atomic" | "composite") => {
    dispatch({ type: "ADD_CHILD", payload: { parentId, tipo } });
  };

  const handleRemove = (nodeId: number) => {
    dispatch({ type: "REMOVE_NODE", payload: { nodeId } });
  };

  const handleToggleCollapse = (nodeId: number) => {
    dispatch({ type: "TOGGLE_COLLAPSE", payload: { nodeId } });
  };

  if (!state || state.length === 0) {
    return (
      <div
        className="rounded-lg border p-4"
        style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
      >
        <p className="text-sm text-muted-foreground">Sin condiciones</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-lg border p-4"
      style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
    >
      {state.map((node) => (
        <CompositeNode
          key={node.id}
          node={node}
          depth={0}
          catalogOptions={catalogOptions}
          readOnly={readOnly}
          onUpdate={handleUpdate}
          onAddChild={handleAddChild}
          onRemove={handleRemove}
          onToggleCollapse={handleToggleCollapse}
        />
      ))}
    </div>
  );
}

export default ConditionTreeEditor;
