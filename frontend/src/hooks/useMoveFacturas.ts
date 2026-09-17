import { useCallback, useState } from "react";

export interface MoveFailure {
  src: string;
  error: string;
}

interface UseMoveFacturasOptions {
  onRefreshed?: (data: unknown) => void;
}

export interface UseMoveFacturasReturn {
  selectedPaths: string[];
  destDir: string;
  toast: string | null;
  moving: boolean;
  togglePath: (path: string) => void;
  toggleAll: (visiblePaths: string[]) => void;
  clear: () => void;
  setDestDir: (dir: string) => void;
  dismissToast: () => void;
  confirmAndMove: () => Promise<void>;
}

/** Toggle one full_path inside the string-key selection. */
export function togglePathInSelection(selection: string[], path: string): string[] {
  return selection.includes(path)
    ? selection.filter((s) => s !== path)
    : [...selection, path];
}

/** Toggle all FILTERED paths: deselect visible when all visible selected, else add missing. */
export function toggleAllPathsFiltered(selection: string[], visiblePaths: string[]): string[] {
  if (visiblePaths.length === 0) return selection;
  const allSelected = visiblePaths.every((p) => selection.includes(p));
  if (allSelected) {
    const visible = new Set(visiblePaths);
    return selection.filter((p) => !visible.has(p));
  }
  const selected = new Set(selection);
  for (const p of visiblePaths) selected.add(p);
  return [...selected];
}

/** Summary toast text: counts plus failed source names. */
export function buildMoveToast(moved: string[], failed: MoveFailure[]): string {
  const base = `Moved ${moved.length}, failed ${failed.length}`;
  if (failed.length === 0) return base;
  return `${base}: ${failed.map((f) => f.src).join(", ")}`;
}

/** String-key bulk-move selection + confirmed POST /move + refresh via GET /data. */
export function useMoveFacturas(options?: UseMoveFacturasOptions): UseMoveFacturasReturn {
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);
  const [destDir, setDestDir] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [moving, setMoving] = useState(false);

  const togglePath = useCallback((path: string) => {
    setSelectedPaths((prev) => togglePathInSelection(prev, path));
  }, []);

  const toggleAll = useCallback((visiblePaths: string[]) => {
    setSelectedPaths((prev) => toggleAllPathsFiltered(prev, visiblePaths));
  }, []);

  const clear = useCallback(() => {
    setSelectedPaths([]);
  }, []);

  const dismissToast = useCallback(() => {
    setToast(null);
  }, []);

  const confirmAndMove = useCallback(async () => {
    if (selectedPaths.length === 0 || moving) return;
    console.log("[FRONT] Move requested for %d invoice(s) to %s", selectedPaths.length, destDir);
    const showConfirm = (window as unknown as { __showConfirm?: (msg: string) => Promise<boolean> }).__showConfirm;
    const ok = showConfirm ? await showConfirm(`Move ${selectedPaths.length} invoice(s) to ${destDir}?`) : false;
    if (!ok) {
      console.log("[FRONT] Move cancelled by user, selection kept");
      return;
    }
    setMoving(true);
    try {
      const res = await fetch("/monitoreo-carpetas/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sources: selectedPaths, dest_dir: destDir }),
      });
      const data = await res.json();
      const moved = (data?.data?.moved ?? []) as string[];
      const failed = (data?.data?.failed ?? []) as MoveFailure[];
      setToast(buildMoveToast(moved, failed));
      setSelectedPaths([]);
      console.log("[FRONT] Move done: %d moved, %d failed", moved.length, failed.length);
      try {
        const refresh = await fetch("/monitoreo-carpetas/data");
        const refreshed = await refresh.json();
        options?.onRefreshed?.(refreshed?.data ?? refreshed);
      } catch (refreshErr) {
        console.error("[FRONT][ERROR] Refresh after move failed:", refreshErr);
      }
    } catch (err) {
      console.error("[FRONT][ERROR] Move request failed:", err);
      setToast("Move failed: connection error");
    } finally {
      setMoving(false);
    }
  }, [selectedPaths, destDir, moving, options]);

  return { selectedPaths, destDir, toast, moving, togglePath, toggleAll, clear, setDestDir, dismissToast, confirmAndMove };
}
