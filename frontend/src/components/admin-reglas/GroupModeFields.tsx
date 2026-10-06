/** Evaluation-mode switch + group_by params builder for the rule editor.
 *
 * Two modes, mirroring the engine routing on `parametros[0].group_by`:
 * - "row": row-by-row (params stay empty/null).
 * - "group": per-factura group evaluation. A small form (group_by field,
 *   aggregations, optional prefilter) generates the params JSON so admins
 *   never hand-write it.
 *
 * Rules whose params are exotic (non-group JSON) fall back to the raw
 * textarea — current behavior preserved, nothing is overwritten.
 */

import { useState } from "react";
import {
  AGG_FUNCTIONS,
  FACTURA_LEVEL_FIELDS,
  INVOICE_ROW_FIELDS,
  getGroupConfig,
  isBuilderCompatibleParams,
  type GroupAggregation,
  type RuleMode,
} from "./operators";

interface GroupModeFieldsProps {
  mode: RuleMode;
  onModeChange: (mode: RuleMode) => void;
  paramsText: string;
  onParamsChange: (text: string) => void;
  disabled?: boolean;
}

const inputClassName =
  "w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary";
const inputStyle = { borderColor: "oklch(0.55 0.04 160 / 0.2)" };
const labelStyle = { color: "oklch(0.55 0.04 160)" };

function defaultTarget(fn: string, field: string): string {
  const base = (field.split(".").pop() ?? "valor").trim() || "valor";
  return `${fn}_${base}`;
}

function emitConfig(
  cfg: { group_by: string | string[]; aggregations: GroupAggregation[]; filter_field?: string; filter_value?: string },
  rest: unknown[],
  onParamsChange: (text: string) => void,
): void {
  const out: Record<string, unknown> = {
    group_by: cfg.group_by,
    aggregations: cfg.aggregations,
  };
  if (cfg.filter_field) {
    out.filter_field = cfg.filter_field;
    if (cfg.filter_value) out.filter_value = cfg.filter_value;
  }
  onParamsChange(JSON.stringify([out, ...rest], null, 2));
}

export function GroupModeFields({
  mode,
  onModeChange,
  paramsText,
  onParamsChange,
  disabled,
}: GroupModeFieldsProps) {
  const [showJson, setShowJson] = useState(false);
  const builderCompatible = isBuilderCompatibleParams(paramsText);

  const parsed = (() => {
    try {
      return paramsText.trim() ? (JSON.parse(paramsText) as unknown) : null;
    } catch {
      return null;
    }
  })();
  const rest: unknown[] = Array.isArray(parsed) ? parsed.slice(1) : [];
  const cfg = getGroupConfig(parsed) ?? {
    group_by: "numero_factura",
    aggregations: [],
  };
  // group_by may be a list (composite); the builder edits single-field.
  const groupBySingle =
    typeof cfg.group_by === "string" ? cfg.group_by : cfg.group_by[0] ?? "numero_factura";

  const update = (patch: Partial<typeof cfg>) => {
    const nextAggs = (patch.aggregations ?? cfg.aggregations ?? []).map((a) => ({ ...a }));
    emitConfig(
      {
        group_by: patch.group_by ?? groupBySingle,
        aggregations: nextAggs,
        ...(patch.filter_field !== undefined || cfg.filter_field
          ? { filter_field: patch.filter_field ?? cfg.filter_field ?? "" }
          : {}),
        ...(patch.filter_value !== undefined || cfg.filter_value
          ? { filter_value: patch.filter_value ?? cfg.filter_value ?? "" }
          : {}),
      },
      rest,
      onParamsChange,
    );
  };

  const handleModeChange = (next: RuleMode) => {
    onModeChange(next);
    if (next === "group" && builderCompatible) {
      const existing = getGroupConfig(parsed);
      if (!existing) {
        emitConfig({ group_by: "numero_factura", aggregations: [] }, rest, onParamsChange);
      }
    }
    if (next === "row" && builderCompatible) {
      const existing = getGroupConfig(parsed);
      if (existing) onParamsChange(rest.length > 0 ? JSON.stringify(rest, null, 2) : "");
    }
  };

  return (
    <div className="mb-4">
      <label className="block text-sm font-medium mb-1" style={labelStyle}>
        Modo de evaluación
      </label>
      <div className="flex gap-2 mb-3" role="radiogroup" aria-label="Modo de evaluación">
        {(
          [
            { value: "row", label: "Por fila" },
            { value: "group", label: "Agrupada por factura" },
          ] as { value: RuleMode; label: string }[]
        ).map((opt) => (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={mode === opt.value}
            disabled={disabled}
            onClick={() => handleModeChange(opt.value)}
            className={`px-4 py-2 rounded-lg border text-sm font-medium ${
              mode === opt.value ? "text-white" : ""
            }`}
            style={
              mode === opt.value
                ? { background: "oklch(0.55 0.04 160)", borderColor: "oklch(0.55 0.04 160)" }
                : inputStyle
            }
          >
            {opt.label}
          </button>
        ))}
      </div>

      {mode === "row" && (
        <p className="text-xs text-muted-foreground">
          Cada fila se evalúa por separado. Los operadores de conjunto (set) y las fuentes{" "}
          <code>group.*</code> se ocultan de los selects.
        </p>
      )}

      {mode === "group" && !builderCompatible && (
        <>
          <p className="text-xs text-muted-foreground mb-2">
            Estos parámetros son personalizados: se editan como JSON (no se sobrescriben).
          </p>
          <textarea
            value={paramsText}
            onChange={(e) => onParamsChange(e.target.value)}
            className="w-full rounded-lg border px-4 py-2.5 text-sm font-mono outline-none focus:border-primary"
            style={inputStyle}
            rows={3}
            disabled={disabled}
          />
        </>
      )}

      {mode === "group" && builderCompatible && (
        <div className="rounded-lg border p-4" style={inputStyle}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
            <div>
              <label className="block text-sm font-medium mb-1" style={labelStyle}>
                Agrupar por
              </label>
              <select
                value={groupBySingle}
                onChange={(e) => update({ group_by: e.target.value })}
                className={inputClassName}
                style={inputStyle}
                disabled={disabled}
              >
                {INVOICE_ROW_FIELDS.filter(
                  (f) => f === "invoice.numero_factura" || f === "invoice.identificacion" || FACTURA_LEVEL_FIELDS.includes(f),
                ).map((f) => (
                  <option key={f} value={f.replace(/^invoice\./, "")}>
                    {f.replace(/^invoice\./, "")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={labelStyle}>
                Prefiltro (campo factura-nivel, opcional)
              </label>
              <select
                value={cfg.filter_field ?? ""}
                onChange={(e) => update({ filter_field: e.target.value || undefined, filter_value: e.target.value ? (cfg.filter_value ?? "") : undefined })}
                className={inputClassName}
                style={inputStyle}
                disabled={disabled}
              >
                <option value="">— sin prefiltro —</option>
                {FACTURA_LEVEL_FIELDS.map((f) => (
                  <option key={f} value={f.replace(/^invoice\./, "")}>
                    {f.replace(/^invoice\./, "")}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {cfg.filter_field && (
            <div className="mb-3">
              <label className="block text-sm font-medium mb-1" style={labelStyle}>
                Valor del prefiltro
              </label>
              <input
                type="text"
                value={cfg.filter_value ?? ""}
                onChange={(e) => update({ filter_value: e.target.value })}
                className={inputClassName}
                style={inputStyle}
                disabled={disabled}
                placeholder='p. ej. Soat'
              />
            </div>
          )}

          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium" style={labelStyle}>
              Agregaciones
            </span>
            <button
              type="button"
              disabled={disabled}
              onClick={() =>
                update({
                  aggregations: [
                    ...(cfg.aggregations ?? []),
                    { function: "collect_set", field: "codigo", target: "collect_set_codigo" },
                  ],
                })
              }
              className="text-xs underline"
            >
              + Agregar
            </button>
          </div>
          {(cfg.aggregations ?? []).length === 0 && (
            <p className="text-xs text-muted-foreground mb-2">
              Sin agregaciones: el árbol solo ve la primera fila del grupo. Agregá al menos una
              (p. ej. conjunto de un campo) para condiciones sobre el grupo.
            </p>
          )}
          {(cfg.aggregations ?? []).map((agg, idx) => (
            <div key={idx} className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-2 items-end">
              <div>
                <label className="block text-xs mb-1" style={labelStyle}>Función</label>
                <select
                  value={agg.function}
                  onChange={(e) => {
                    const next = [...(cfg.aggregations ?? [])];
                    next[idx] = { ...next[idx], function: e.target.value };
                    update({ aggregations: next });
                  }}
                  className="w-full rounded-lg border px-2 py-2 text-sm outline-none"
                  style={inputStyle}
                  disabled={disabled}
                >
                  {AGG_FUNCTIONS.map((f) => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
              </div>
              {agg.function === "compute_horas" ? (
                <>
                  <div>
                    <label className="block text-xs mb-1" style={labelStyle}>Desde</label>
                    <select
                      value={agg.field1 ?? "fec_factura"}
                      onChange={(e) => {
                        const next = [...(cfg.aggregations ?? [])];
                        next[idx] = { ...next[idx], field1: e.target.value };
                        update({ aggregations: next });
                      }}
                      className="w-full rounded-lg border px-2 py-2 text-sm outline-none"
                      style={inputStyle}
                      disabled={disabled}
                    >
                      {INVOICE_ROW_FIELDS.map((f) => (
                        <option key={f} value={f.replace(/^invoice\./, "")}>
                          {f.replace(/^invoice\./, "")}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs mb-1" style={labelStyle}>Hasta</label>
                    <select
                      value={agg.field2 ?? "fecha_cierre"}
                      onChange={(e) => {
                        const next = [...(cfg.aggregations ?? [])];
                        next[idx] = { ...next[idx], field2: e.target.value };
                        update({ aggregations: next });
                      }}
                      className="w-full rounded-lg border px-2 py-2 text-sm outline-none"
                      style={inputStyle}
                      disabled={disabled}
                    >
                      {INVOICE_ROW_FIELDS.map((f) => (
                        <option key={f} value={f.replace(/^invoice\./, "")}>
                          {f.replace(/^invoice\./, "")}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              ) : (
                <div className="md:col-span-2">
                  <label className="block text-xs mb-1" style={labelStyle}>Campo</label>
                  <select
                    value={agg.field ?? ""}
                    onChange={(e) => {
                      const next = [...(cfg.aggregations ?? [])];
                      const updated = { ...next[idx], field: e.target.value };
                      if (!updated.target || updated.target === defaultTarget(next[idx].function, next[idx].field ?? "")) {
                        updated.target = defaultTarget(updated.function, e.target.value);
                      }
                      next[idx] = updated;
                      update({ aggregations: next });
                    }}
                    className="w-full rounded-lg border px-2 py-2 text-sm outline-none"
                    style={inputStyle}
                    disabled={disabled}
                  >
                    <option value="">— campo —</option>
                    {INVOICE_ROW_FIELDS.map((f) => (
                      <option key={f} value={f.replace(/^invoice\./, "")}>
                        {f.replace(/^invoice\./, "")}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex gap-1">
                <div className="flex-1">
                  <label className="block text-xs mb-1" style={labelStyle}>Destino</label>
                  <input
                    type="text"
                    value={agg.target}
                    onChange={(e) => {
                      const next = [...(cfg.aggregations ?? [])];
                      next[idx] = { ...next[idx], target: e.target.value };
                      update({ aggregations: next });
                    }}
                    className="w-full rounded-lg border px-2 py-2 text-sm font-mono outline-none"
                    style={inputStyle}
                    disabled={disabled}
                    placeholder={defaultTarget(agg.function, agg.field ?? "")}
                  />
                </div>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => update({ aggregations: (cfg.aggregations ?? []).filter((_, i) => i !== idx) })}
                  className="px-2 py-1 text-xs rounded hover:bg-red-50 self-end"
                  style={{ color: "oklch(0.6 0.2 25)" }}
                  title="Quitar agregación"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}

          <button
            type="button"
            onClick={() => setShowJson((v) => !v)}
            className="mt-1 text-xs underline"
          >
            {showJson ? "Ocultar JSON" : "Ver JSON generado"}
          </button>
          {showJson && (
            <pre className="mt-2 text-xs font-mono p-2 rounded overflow-x-auto" style={{ background: "oklch(0.55 0.04 160 / 0.05)" }}>
              {paramsText || "(vacío)"}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
