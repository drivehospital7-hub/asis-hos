/** Helpers puros para activación masiva de reglas.
 *
 * Sin dependencias de React: selección por ids + runner con
 * concurrencia acotada. Reusa el PUT existente (updateRegla por id).
 */

export interface BulkError<T> {
  item: T;
  message: string;
}

export interface RunOptions {
  limit?: number;
  onProgress?: (done: number, total: number) => void;
}

/** Toggle de un id dentro de la selección. */
export function toggleIdInSelection(selection: number[], id: number): number[] {
  return selection.includes(id)
    ? selection.filter((s) => s !== id)
    : [...selection, id];
}

/** Toggle de todas las FILTRADAS: si ya están todas, las quita; si no, agrega las faltantes. */
export function toggleAllFiltered(selection: number[], filteredIds: number[]): number[] {
  if (filteredIds.length === 0) return selection;
  const allSelected = filteredIds.every((id) => selection.includes(id));
  if (allSelected) {
    const filtered = new Set(filteredIds);
    return selection.filter((id) => !filtered.has(id));
  }
  const selected = new Set(selection);
  for (const id of filteredIds) selected.add(id);
  return [...selected];
}

/** Ejecuta fn sobre items con concurrencia máxima `limit` (default 5).
 * Colecta errores sin abortar el resto. */
export async function runWithConcurrency<T>(
  items: T[],
  fn: (item: T) => Promise<unknown>,
  options?: RunOptions,
): Promise<{ errors: BulkError<T>[] }> {
  const limit = Math.max(1, Math.min(options?.limit ?? 5, 5));
  const errors: BulkError<T>[] = [];
  let done = 0;
  let cursor = 0;

  async function worker(): Promise<void> {
    while (cursor < items.length) {
      const item = items[cursor];
      cursor += 1;
      try {
        await fn(item);
      } catch (e) {
        errors.push({ item, message: e instanceof Error ? e.message : "Error desconocido" });
      }
      done += 1;
      options?.onProgress?.(done, items.length);
    }
  }

  const workers = Array.from(
    { length: Math.min(limit, items.length) },
    () => worker(),
  );
  await Promise.all(workers);
  return { errors };
}
