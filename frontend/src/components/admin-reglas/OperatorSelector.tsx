import { CATEGORIAS, GROUP_ONLY_OPERATORS, OPERADORES_ATOMICOS, type RuleMode } from "./operators";
import { SearchableSelect, type SearchOption } from "./SearchableSelect";

// ─── Props ─────────────────────────────────────────────────────────

interface OperatorSelectorProps {
  value: string;
  onChange: (operator: string) => void;
  readOnly?: boolean;
  /** Row mode hides set-only operators (guidance; free text still allowed). */
  mode?: RuleMode;
}

// ─── Helpers ────────────────────────────────────────────────────────

const CATEGORY_LABEL: Record<string, string> = Object.fromEntries(
  CATEGORIAS.map((c) => [c.id, c.label]),
);

function toOptions(mode?: RuleMode): SearchOption[] {
  return OPERADORES_ATOMICOS.filter(
    (op) => mode !== "row" || !GROUP_ONLY_OPERATORS.includes(op.value),
  ).map((op) => ({
    value: op.value,
    label: `${op.label} — ${CATEGORY_LABEL[op.category] ?? op.category}`,
  }));
}

/** Map typed text (raw value or friendly label) back to an operator value. */
export function resolveOperatorInput(
  text: string,
  options: SearchOption[],
): string {
  const trimmed = text.trim();
  if (!trimmed) return "";
  const byValue = options.find((o) => o.value === trimmed);
  if (byValue) return byValue.value;
  const byLabel = options.find(
    (o) => (o.label ?? o.value).toLowerCase() === trimmed.toLowerCase(),
  );
  return byLabel ? byLabel.value : trimmed;
}

// ─── Component ──────────────────────────────────────────────────────

export function OperatorSelector({ value, onChange, readOnly, mode }: OperatorSelectorProps) {
  if (readOnly) {
    return (
      <span className="text-xs text-muted-foreground">{value || "—"}</span>
    );
  }

  const options = toOptions(mode);
  const known = value === "" || options.some((o) => o.value === value);

  return (
    <SearchableSelect
      value={value}
      options={options}
      onChange={(text) => onChange(resolveOperatorInput(text, options))}
      ariaLabel="Operador"
      placeholder="-- operador -- (escribí para buscar)"
      minWidth="130px"
      invalid={!known}
    />
  );
}
