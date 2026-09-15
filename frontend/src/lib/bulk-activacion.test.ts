import { describe, it, expect, vi } from "vitest";
import {
  toggleIdInSelection,
  toggleAllFiltered,
  runWithConcurrency,
} from "./bulk-activacion";

describe("toggleIdInSelection", () => {
  it("agrega un id ausente", () => {
    expect(toggleIdInSelection([1, 2], 3)).toEqual([1, 2, 3]);
  });

  it("quita un id presente", () => {
    expect(toggleIdInSelection([1, 2, 3], 2)).toEqual([1, 3]);
  });
});

describe("toggleAllFiltered", () => {
  it("selecciona las filtradas respetando la selección previa", () => {
    expect(toggleAllFiltered([9], [1, 2, 3])).toEqual([9, 1, 2, 3]);
  });

  it("deselecciona solo las filtradas cuando ya están todas", () => {
    expect(toggleAllFiltered([9, 1, 2], [1, 2])).toEqual([9]);
  });

  it("no cambia nada con lista filtrada vacía", () => {
    expect(toggleAllFiltered([1], [])).toEqual([1]);
  });
});

describe("runWithConcurrency", () => {
  it("respeta el límite de concurrencia y reporta progreso", async () => {
    let active = 0;
    let maxActive = 0;
    const seen: Array<[number, number]> = [];
    const fn = async (n: number) => {
      active += 1;
      maxActive = Math.max(maxActive, active);
      await new Promise((r) => setTimeout(r, 5));
      active -= 1;
      void n;
    };
    const { errors } = await runWithConcurrency([1, 2, 3, 4, 5, 6], fn, {
      limit: 5,
      onProgress: (d, t) => seen.push([d, t]),
    });
    expect(errors).toEqual([]);
    expect(maxActive).toBeLessThanOrEqual(5);
    expect(seen[seen.length - 1]).toEqual([6, 6]);
  });

  it("colecta errores sin abortar el resto", async () => {
    const fn = vi.fn(async (n: number) => {
      if (n === 2) throw new Error("falla #2");
    });
    const { errors } = await runWithConcurrency([1, 2, 3], fn, { limit: 2 });
    expect(fn).toHaveBeenCalledTimes(3);
    expect(errors).toEqual([{ item: 2, message: "falla #2" }]);
  });
});
