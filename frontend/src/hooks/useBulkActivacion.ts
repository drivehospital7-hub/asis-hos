import { useState, useCallback } from "react";
import {
  toggleIdInSelection,
  toggleAllFiltered,
  runWithConcurrency,
} from "@/lib/bulk-activacion";

interface Props {
  runOne: (id: number, activo: boolean) => Promise<unknown>;
}

export interface BulkFailure {
  id: number;
  message: string;
}

export interface UseBulkActivacionReturn {
  selectedIds: number[];
  running: boolean;
  done: number;
  total: number;
  failures: BulkFailure[];
  toggleId: (id: number) => void;
  toggleAll: (filteredIds: number[]) => void;
  clear: () => void;
  prune: (validIds: number[]) => void;
  retainOnly: (ids: number[]) => void;
  runBulk: (activo: boolean) => Promise<BulkFailure[]>;
}

/** Selección + ejecución masiva de activación (concurrencia ≤5, reusa PUT por id). */
export function useBulkActivacion({ runOne }: Props): UseBulkActivacionReturn {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(0);
  const [total, setTotal] = useState(0);
  const [failures, setFailures] = useState<BulkFailure[]>([]);

  const toggleId = useCallback((id: number) => {
    setSelectedIds((prev) => toggleIdInSelection(prev, id));
  }, []);

  const toggleAll = useCallback((filteredIds: number[]) => {
    setSelectedIds((prev) => toggleAllFiltered(prev, filteredIds));
  }, []);

  const clear = useCallback(() => {
    setSelectedIds([]);
    setFailures([]);
    setDone(0);
    setTotal(0);
  }, []);

  const prune = useCallback((validIds: number[]) => {
    setSelectedIds((prev) => {
      const valid = new Set(validIds);
      const next = prev.filter((id) => valid.has(id));
      return next.length === prev.length ? prev : next;
    });
  }, []);

  const retainOnly = useCallback((ids: number[]) => {
    const keep = new Set(ids);
    setSelectedIds((prev) => prev.filter((id) => keep.has(id)));
  }, []);

  const runBulk = useCallback(
    async (activo: boolean) => {
      if (selectedIds.length === 0 || running) return [];
      const ids = [...selectedIds];
      setRunning(true);
      setDone(0);
      setTotal(ids.length);
      setFailures([]);
      const { errors } = await runWithConcurrency(
        ids,
        (id) => runOne(id, activo),
        { limit: 5, onProgress: (d) => setDone(d) },
      );
      const failures = errors.map((e) => ({ id: e.item, message: e.message }));
      setFailures(failures);
      setRunning(false);
      return failures;
    },
    [selectedIds, running, runOne],
  );

  return { selectedIds, running, done, total, failures, toggleId, toggleAll, clear, prune, retainOnly, runBulk };
}
