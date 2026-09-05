import { useState, useRef } from "react";
import { Plus, X } from "lucide-react";
import type { ValueType } from "./operators";

// ─── Props ─────────────────────────────────────────────────────────

interface ValueInputProps {
  valueType: ValueType;
  value: unknown;
  catalogOptions?: string[];
  readOnly?: boolean;
  onChange: (value: unknown) => void;
}

// ─── Component ──────────────────────────────────────────────────────

export function ValueInput({ valueType, value, catalogOptions, readOnly, onChange }: ValueInputProps) {
  if (readOnly) {
    return (
      <span className="text-xs font-mono" style={{ color: "oklch(0.15 0.02 160)" }}>
        {formatValue(value, valueType)}
      </span>
    );
  }

  switch (valueType) {
    case "number":
      return (
        <NumberInput value={value} onChange={onChange} />
      );
    case "string":
      return (
        catalogOptions ? (
          <CatalogSelect value={value} options={catalogOptions} onChange={onChange} />
        ) : (
          <TextInput value={value} onChange={onChange} />
        )
      );
    case "json":
      return (
        <JsonEditor value={value} onChange={onChange} />
      );
    case "array":
      return (
        <ArrayEditor value={value} onChange={onChange} />
      );
    case "hidden":
      return (
        <HiddenLabel value={value} />
      );
    default:
      return (
        <TextInput value={value} onChange={onChange} />
      );
  }
}

function CatalogSelect({
  value,
  options,
  onChange,
}: {
  value: unknown;
  options: string[];
  onChange: (value: unknown) => void;
}) {
  const currentValue = typeof value === "string" ? value : "";
  const selectOptions = currentValue && !options.includes(currentValue)
    ? [currentValue, ...options]
    : options;

  return (
    <select
      aria-label="Catalog key"
      value={String(value ?? "")}
      onChange={(e) => onChange(e.target.value)}
      className="text-xs font-mono border rounded px-2 py-1 outline-none flex-1 min-w-[160px]"
      style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
    >
      <option value="">-- catalog key --</option>
      {selectOptions.map((key) => (
        <option key={key} value={key}>{key}</option>
      ))}
    </select>
  );
}

// ─── Sub-widgets ────────────────────────────────────────────────────

function NumberInput({ value, onChange }: { value: unknown; onChange: (v: unknown) => void }) {
  return (
    <input
      type="number"
      step="any"
      value={String(value ?? "")}
      onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
      className="text-xs font-mono border rounded px-2 py-1 outline-none flex-1 min-w-[80px]"
      style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
      placeholder="0"
    />
  );
}

function TextInput({ value, onChange }: { value: unknown; onChange: (v: unknown) => void }) {
  return (
    <input
      type="text"
      value={String(value ?? "")}
      onChange={(e) => onChange(e.target.value)}
      className="text-xs font-mono border rounded px-2 py-1 outline-none flex-1 min-w-[100px]"
      style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
      placeholder="valor"
    />
  );
}

function JsonEditor({ value, onChange }: { value: unknown; onChange: (v: unknown) => void }) {
  const textValue = value && typeof value === "object" ? JSON.stringify(value, null, 2) : String(value ?? "");
  return (
    <textarea
      value={textValue}
      onChange={(e) => {
        const raw = e.target.value;
        try {
          const parsed = JSON.parse(raw);
          onChange(parsed);
        } catch {
          // Keep invalid JSON as string so user can continue editing
          onChange(raw);
        }
      }}
      className="text-xs font-mono border rounded px-2 py-1 outline-none flex-1 min-w-[180px]"
      style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
      rows={2}
      placeholder='{"table":"...", "field":"..."}'
    />
  );
}

function ArrayEditor({ value, onChange }: { value: unknown; onChange: (v: unknown) => void }) {
  const items: string[] = Array.isArray(value) ? value.map((v) => String(v ?? "")) : [];
  const [newValue, setNewValue] = useState("");
  const addRef = useRef<HTMLInputElement>(null);

  const emit = (updated: string[]) => onChange(updated);

  const handleUpdate = (idx: number, val: string) => {
    const copy = [...items];
    copy[idx] = val;
    emit(copy);
  };

  const handleRemove = (idx: number) => {
    const copy = [...items];
    copy.splice(idx, 1);
    emit(copy);
  };

  const handleAdd = () => {
    const trimmed = newValue.trim();
    if (!trimmed) return;
    emit([...items, trimmed]);
    setNewValue("");
    // Focus back on the add input for rapid entry
    setTimeout(() => addRef.current?.focus(), 0);
  };

  return (
    <div className="w-[260px]">
      {/* Item rows */}
      <div className="flex flex-col gap-1 max-h-[180px] overflow-y-auto mb-1">
        {items.length === 0 && (
          <span className="text-xs text-muted-foreground italic px-1">(vacío)</span>
        )}
        {items.map((item, idx) => (
          <div key={idx} className="flex items-center gap-1">
            <input
              type="text"
              value={item}
              onChange={(e) => handleUpdate(idx, e.target.value)}
              className="text-xs font-mono border rounded px-2 py-1 outline-none flex-1 min-w-[50px]"
              style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
            />
            <button
              type="button"
              onClick={() => handleRemove(idx)}
              className="p-0.5 rounded hover:bg-red-50 flex-shrink-0"
              title="Quitar"
              style={{ color: "oklch(0.6 0.2 25)" }}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Add row */}
      <div className="flex items-center gap-1">
        <input
          ref={addRef}
          type="text"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleAdd();
            }
          }}
          className="text-xs font-mono border rounded px-2 py-1 outline-none flex-1 min-w-[80px]"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.3)" }}
          placeholder="Nuevo valor..."
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={!newValue.trim()}
          className="p-1 rounded hover:bg-gray-100 flex-shrink-0 disabled:opacity-40"
          title="Agregar"
          style={{ color: "oklch(0.55 0.04 160)" }}
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function HiddenLabel({ value }: { value: unknown }) {
  if (value !== null && value !== undefined && value !== "") {
    return (
      <span className="text-xs italic" style={{ color: "oklch(0.55 0.04 160 / 0.6)" }}>
        {String(value)}
      </span>
    );
  }
  return (
    <span className="text-xs italic" style={{ color: "oklch(0.55 0.04 160 / 0.4)" }}>
      (valor derivado del contexto)
    </span>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────

function formatValue(value: unknown, valueType: ValueType): string {
  if (value === null || value === undefined) return "—";
  if (valueType === "json" && typeof value === "object") {
    return JSON.stringify(value);
  }
  if (valueType === "array" && Array.isArray(value)) {
    if (value.length === 0) return "[]";
    if (value.length <= 5) return value.join(", ");
    return `${value.slice(0, 3).join(", ")} … +${value.length - 3} más`;
  }
  return String(value);
}
