import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { GruposTable, tipoBadgeClass } from "./GruposManager";

const ITEMS = [
  { nombre: "Duplicados-Farmacia", tipo: "sistema", total_reglas: 1, reglas_activas: 0 },
  { nombre: "Mi Grupo", tipo: "simple", total_reglas: 2, reglas_activas: 1 },
  { nombre: "Vacio", tipo: "canonico", total_reglas: 0, reglas_activas: 0 },
] as const;

describe("GruposTable", () => {
  it("shows usage counts and locks sistema groups", () => {
    const html = renderToStaticMarkup(
      <GruposTable items={[...ITEMS]} busy={null} onRename={vi.fn()} onUnassign={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(html).toContain("Duplicados-Farmacia");
    expect(html).toContain("bloqueado");
    expect(html).toContain("Mi Grupo");
    expect(html).toContain("Renombrar");
    expect(html).toContain("Eliminar");
  });

  it("allows rename and catalog-delete for unused groups", () => {
    const html = renderToStaticMarkup(
      <GruposTable
        items={[{ nombre: "Vacio", tipo: "simple", total_reglas: 0, reglas_activas: 0 }]}
        busy={null}
        onRename={vi.fn()}
        onUnassign={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(html).not.toContain("disabled=");
    expect(html).toContain("Renombrar");
    expect(html).toContain("Eliminar");
  });

  it("badges sistema distinctly", () => {
    expect(tipoBadgeClass("sistema")).toContain("purple");
    expect(tipoBadgeClass("simple")).not.toContain("purple");
  });
});
