import * as React from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

interface SelectRegistryItem {
  value: string;
  label: React.ReactNode;
  disabled?: boolean;
}

interface SelectContextValue {
  value: string;
  onValueChange: (value: string) => void;
  items: SelectRegistryItem[];
}

const SelectContext = React.createContext<SelectContextValue | null>(null);

function useSelectContext() {
  const ctx = React.useContext(SelectContext);
  if (!ctx) throw new Error("Select components must be inside <Select>");
  return ctx;
}

function collectItems(children: React.ReactNode): SelectRegistryItem[] {
  const items: SelectRegistryItem[] = [];
  const walk = (nodes: React.ReactNode) => {
    React.Children.forEach(nodes, (child) => {
      if (!React.isValidElement(child)) return;
      const type = child.type as unknown as { displayName?: string };
      if (type?.displayName === "SelectContent") {
        React.Children.forEach((child.props as { children: React.ReactNode }).children, (item) => {
          if (React.isValidElement(item) && (item.type as unknown as { displayName?: string })?.displayName === "SelectItem") {
            const p = item.props as unknown as { value: string; children: React.ReactNode; disabled?: boolean; label?: React.ReactNode };
            items.push({ value: p.value, label: p.children ?? p.label, disabled: p.disabled });
          }
        });
      } else if (type?.displayName === "SelectItem") {
        const p = child.props as unknown as { value: string; children: React.ReactNode; disabled?: boolean; label?: React.ReactNode };
        items.push({ value: p.value, label: p.children ?? p.label, disabled: p.disabled });
      } else if ((child.props as { children?: React.ReactNode })?.children) {
        walk((child.props as { children: React.ReactNode }).children);
      }
    });
  };
  walk(children);
  return items;
}

interface SelectProps {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
}

function Select({ value: controlled, defaultValue = "", onValueChange, children }: SelectProps) {
  const [internal, setInternal] = React.useState(defaultValue);
  const isControlled = controlled !== undefined;
  const value = isControlled ? controlled! : internal;

  const handleChange = React.useCallback(
    (next: string) => {
      if (!isControlled) setInternal(next);
      onValueChange?.(next);
    },
    [isControlled, onValueChange],
  );

  const items = React.useMemo(() => collectItems(children), [children]);

  return (
    <SelectContext.Provider value={{ value, onValueChange: handleChange, items }}>
      <div data-slot="select" className="w-full">
        {children}
      </div>
    </SelectContext.Provider>
  );
}

interface SelectTriggerProps extends React.ComponentProps<"div"> {
  size?: "default" | "sm";
}

function SelectTrigger({ className, size = "default", children, ...props }: SelectTriggerProps) {
  const { value, onValueChange, items } = useSelectContext();

  let placeholder: string | undefined;
  React.Children.forEach(children, (child) => {
    if (React.isValidElement(child) && (child.type as unknown as { displayName?: string })?.displayName === "SelectValue") {
      placeholder = (child.props as { placeholder?: string }).placeholder;
    }
  });

  return (
    <div
      data-slot="select-trigger"
      className={cn(
        "relative flex h-8 w-full items-center rounded-lg border border-input bg-transparent text-sm focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50",
        size === "sm" && "h-7 text-xs",
        className,
      )}
      {...props}
    >
      <select
        data-slot="select-native"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        className="h-full w-full appearance-none bg-transparent px-2.5 pr-8 text-sm outline-none disabled:cursor-not-allowed disabled:opacity-50"
      >
        {placeholder && !value ? <option value="">{placeholder}</option> : null}
        {items.map((opt) => (
          <option key={opt.value} value={opt.value} disabled={opt.disabled}>
            {opt.label as string}
          </option>
        ))}
      </select>
      <span className="pointer-events-none absolute right-2.5 flex items-center">
        <ChevronDown className="size-4 opacity-50" />
      </span>
    </div>
  );
}

interface SelectValueProps {
  placeholder?: string;
}

function SelectValue(_props: SelectValueProps) {
  return null;
}
SelectValue.displayName = "SelectValue";

function SelectContent({ children }: { children: React.ReactNode }) {
  // Content is consumed by Select via collectItems — render hidden for fallback
  return <span data-slot="select-content" hidden>
    {children}
  </span>;
}
SelectContent.displayName = "SelectContent";

interface SelectItemProps {
  value: string;
  children: React.ReactNode;
  disabled?: boolean;
}

function SelectItem(_props: SelectItemProps) {
  return null;
}
SelectItem.displayName = "SelectItem";

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem };
