import { useId } from "react";

// ─── Types ──────────────────────────────────────────────────────────

export interface SearchOption {
  value: string;
  label?: string;
}

interface SearchableSelectProps {
  value: string;
  options: (string | SearchOption)[];
  onChange: (value: string) => void;
  ariaLabel: string;
  placeholder?: string;
  minWidth?: string;
  invalid?: boolean;
}

// ─── Helpers ────────────────────────────────────────────────────────

function normalize(options: (string | SearchOption)[]): SearchOption[] {
  return options.map((o) => (typeof o === "string" ? { value: o } : o));
}

// ─── Component ──────────────────────────────────────────────────────
//
// Native <input list + datalist>: searchable without dependencies,
// keyboard-accessible, and it always displays the stored value — even
// when the value is not in the option list (e.g. rules seeded before
// the list was extended). Unknown values are never hidden behind a
// "-- placeholder --" again.

export function SearchableSelect({
  value,
  options,
  onChange,
  ariaLabel,
  placeholder,
  minWidth = "180px",
  invalid = false,
}: SearchableSelectProps) {
  const listId = useId();
  const items = normalize(options);

  return (
    <span className="inline-flex flex-1" style={{ minWidth }}>
      <input
        aria-label={ariaLabel}
        aria-invalid={invalid || undefined}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        list={listId}
        placeholder={placeholder}
        autoComplete="off"
        className="text-xs border rounded px-2 py-1 outline-none w-full"
        style={{
          borderColor: invalid
            ? "oklch(0.6 0.2 25 / 0.6)"
            : "oklch(0.6 0.2 25 / 0.2)",
        }}
      />
      <datalist id={listId}>
        {items.map((o) => (
          <option key={o.value} value={o.value} label={o.label ?? o.value} />
        ))}
      </datalist>
    </span>
  );
}
