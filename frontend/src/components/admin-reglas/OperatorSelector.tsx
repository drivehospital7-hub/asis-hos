import { CATEGORIAS, getOperatorsByCategory } from "./operators";

// ─── Props ─────────────────────────────────────────────────────────

interface OperatorSelectorProps {
  value: string;
  onChange: (operator: string) => void;
  readOnly?: boolean;
}

// ─── Component ──────────────────────────────────────────────────────

export function OperatorSelector({ value, onChange, readOnly }: OperatorSelectorProps) {
  if (readOnly) {
    return (
      <span className="text-xs text-muted-foreground">{value || "—"}</span>
    );
  }

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="text-xs border rounded px-2 py-1 outline-none min-w-[130px]"
      style={{ borderColor: "oklch(0.6 0.2 25 / 0.2)" }}
    >
      <option value="">-- operador --</option>
      {CATEGORIAS.map((cat) => (
        <optgroup key={cat.id} label={cat.label}>
          {getOperatorsByCategory(cat.id).map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
