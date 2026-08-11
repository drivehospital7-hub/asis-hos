import { useState } from "react";
import { X, Eye, Loader2, ArrowLeftRight } from "lucide-react";
import type { CondicionTree } from "@/lib/api-reglas";
import { fetchCatalogo } from "@/lib/api-reglas";
import { FUENTES_DATOS, getValueTypeForOperator } from "./operators";
import { OperatorSelector } from "./OperatorSelector";
import { ValueInput } from "./ValueInput";

// ─── Props ─────────────────────────────────────────────────────────

interface AtomicNodeProps {
  node: CondicionTree;
  catalogOptions?: string[];
  readOnly?: boolean;
  onUpdate: (nodeId: number, field: string, value: unknown) => void;
  onRemove: (nodeId: number) => void;
}

// ─── Component ──────────────────────────────────────────────────────

export function AtomicNode({ node, catalogOptions, readOnly, onUpdate, onRemove }: AtomicNodeProps) {
  const operator = node.operador ?? "";
  const valueType = getValueTypeForOperator(operator);
  const isCatIn = operator === "cat_in";
  const catalogKey = isCatIn && typeof node.valor_esperado === "string" ? node.valor_esperado : null;

  // Catalog popover state
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [catalogValues, setCatalogValues] = useState<string[] | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  const handleViewCatalog = async () => {
    if (!catalogKey) return;
    setCatalogOpen(true);
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      const data = await fetchCatalogo(catalogKey);
      setCatalogValues(data.values);
    } catch (e) {
      setCatalogError(e instanceof Error ? e.message : "Error al cargar");
    } finally {
      setCatalogLoading(false);
    }
  };

  const handleConvertToInline = () => {
    if (!catalogValues) return;
    // Switch operator from cat_in -> in, and valor_esperado from key name -> array
    onUpdate(node.id, "operador", "in");
    onUpdate(node.id, "valor_esperado", catalogValues);
    setCatalogOpen(false);
  };

  if (readOnly) {
    return (
      <div
        className="flex items-center gap-2 p-2 rounded-md text-sm"
        style={{
          background: "white",
          borderLeft: "3px solid oklch(0.6 0.2 25 / 0.3)",
        }}
      >
        <span className="font-medium text-xs" style={{ color: "oklch(0.55 0.04 160)" }}>
          {node.fuente_datos ?? "?"}
        </span>
        <span className="text-xs text-muted-foreground">{operator}</span>
        <ValueInput
          valueType={valueType}
          value={node.valor_esperado}
          catalogOptions={isCatIn ? catalogOptions : undefined}
          readOnly
          onChange={() => {}}
        />
      </div>
    );
  }

  return (
    <div
      className="flex items-start gap-2 p-2 rounded-md text-sm"
      style={{
        background: "white",
        borderLeft: "3px solid oklch(0.6 0.2 25 / 0.3)",
      }}
    >
      {/* FUENTES_DATOS select */}
      <select
        value={node.fuente_datos ?? ""}
        onChange={(e) => onUpdate(node.id, "fuente_datos", e.target.value)}
        className="text-xs border rounded px-2 py-1 outline-none min-w-[180px]"
        style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
      >
        <option value="">-- fuente --</option>
        {FUENTES_DATOS.map((f) => (
          <option key={f} value={f}>{f}</option>
        ))}
      </select>

      {/* Operator selector */}
      <OperatorSelector
        value={operator}
        onChange={(op) => onUpdate(node.id, "operador", op)}
      />

      {/* Value input (dynamic per operator) */}
      <ValueInput
        valueType={valueType}
        value={node.valor_esperado}
        catalogOptions={isCatIn ? catalogOptions : undefined}
        onChange={(val) => onUpdate(node.id, "valor_esperado", val)}
      />

      {/* cat_in: "Ver catálogo" button */}
      {isCatIn && catalogKey && (
        <div className="relative">
          <button
            type="button"
            onClick={handleViewCatalog}
            className="px-2 py-1 text-xs rounded hover:bg-gray-100 flex items-center gap-1"
            style={{ color: "oklch(0.55 0.04 160)" }}
            title="Ver valores del catálogo"
          >
            <Eye className="h-3 w-3" />
            Ver catálogo
          </button>

          {/* Popover */}
          {catalogOpen && (
            <div
              className="absolute top-full left-0 mt-1 z-40 bg-white rounded-lg border shadow-lg p-3 min-w-[280px] max-w-[400px]"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.2)" }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold" style={{ color: "oklch(0.15 0.02 160)" }}>
                  Catálogo: {catalogKey}
                </span>
                <button
                  type="button"
                  onClick={() => setCatalogOpen(false)}
                  className="p-0.5 rounded hover:bg-gray-100"
                >
                  <X className="h-3 w-3" style={{ color: "oklch(0.55 0.04 160)" }} />
                </button>
              </div>

              {catalogLoading ? (
                <div className="flex items-center gap-2 py-4 justify-center">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-xs text-muted-foreground">Cargando...</span>
                </div>
              ) : catalogError ? (
                <p className="text-xs text-danger py-2">{catalogError}</p>
              ) : catalogValues && catalogValues.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2 italic">Catálogo vacío</p>
              ) : catalogValues ? (
                <>
                  <div className="max-h-[200px] overflow-y-auto mb-2">
                    <div className="flex flex-col gap-0.5">
                      {catalogValues.map((v, i) => (
                        <span
                          key={i}
                          className="text-xs font-mono px-2 py-0.5 rounded"
                          style={{ background: "oklch(0.55 0.04 160 / 0.06)", color: "oklch(0.15 0.02 160)" }}
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">
                    {catalogValues.length} valor(es)
                  </p>
                  <button
                    type="button"
                    onClick={handleConvertToInline}
                    className="w-full px-2 py-1.5 text-xs rounded border flex items-center justify-center gap-1 hover:bg-gray-50"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.3)", color: "oklch(0.55 0.04 160)" }}
                  >
                    <ArrowLeftRight className="h-3 w-3" />
                    Convertir a lista inline (in)
                  </button>
                </>
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* Remove button */}
      {!readOnly && (
        <button
          type="button"
          onClick={() => onRemove(node.id)}
          className="p-1 rounded hover:bg-red-50"
          title="Eliminar"
          style={{ color: "oklch(0.6 0.2 25)" }}
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}
