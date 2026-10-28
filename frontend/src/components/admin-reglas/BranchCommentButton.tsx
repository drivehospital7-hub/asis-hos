import { useState } from "react";
import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface BranchCommentButtonProps {
  /** Current memo (null/"" = none). */
  comentario?: string | null;
  /** Persist on save (parent wires to onUpdate(node.id, "comentario", text)). */
  onSave: (text: string) => void;
  readOnly?: boolean;
}

/**
 * Tiny "+" memo button for rule branches. Display-only note with zero
 * evaluation effect. Amber filled when a memo exists, ghost otherwise.
 */
export function BranchCommentButton({ comentario, onSave, readOnly }: BranchCommentButtonProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(comentario ?? "");
  const hasMemo = Boolean(comentario && comentario.trim() !== "");

  return (
    <span className="inline-flex items-center">
      <button
        type="button"
        title={hasMemo ? `Memo: ${comentario}` : "Agregar memo a la rama (solo nota, no afecta la evaluación)"}
        onClick={() => {
          if (readOnly) return;
          setDraft(comentario ?? "");
          setOpen((v) => !v);
        }}
        className={cn(
          "h-5 w-5 inline-flex items-center justify-center rounded text-[11px] font-bold leading-none border transition-colors",
          hasMemo
            ? "bg-amber-400/30 border-amber-500/60 text-amber-800 hover:bg-amber-400/50"
            : "bg-transparent border-border text-muted-foreground hover:bg-muted",
        )}
      >
        <Plus className="h-3 w-3" />
      </button>
      {open && !readOnly && (
        <span className="ml-1 inline-flex items-center gap-1">
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                onSave(draft.trim());
                setOpen(false);
              }
              if (e.key === "Escape") setOpen(false);
            }}
            placeholder="Memo de la rama…"
            className="text-xs border rounded px-1.5 py-0.5 outline-none w-44"
          />
          <button
            type="button"
            className="text-[11px] px-1.5 py-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20"
            onClick={() => {
              onSave(draft.trim());
              setOpen(false);
            }}
          >
            OK
          </button>
        </span>
      )}
    </span>
  );
}
