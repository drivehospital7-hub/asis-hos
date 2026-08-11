import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AtomicNode } from "./AtomicNode";

describe("AtomicNode source and operator selectors", () => {
  it("renders the available source fields and operator metadata", () => {
    const html = renderToStaticMarkup(
      <AtomicNode
        node={{
          id: 1,
          regla_id: 1,
          padre_id: 2,
          tipo: "atomic",
          operador: "eq",
          fuente_datos: "",
          valor_esperado: "",
          orden: 0,
        }}
        onUpdate={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(html).toContain('value="invoice.centro_costo"');
    expect(html).toContain("Igual (=)");
    expect(html).toContain("Mayor (&gt;)");
  });

  it("renders catalog keys for cat_in and keeps the preview action", () => {
    const html = renderToStaticMarkup(
      <AtomicNode
        node={{
          id: 1,
          regla_id: 1,
          padre_id: 2,
          tipo: "atomic",
          operador: "cat_in",
          fuente_datos: "invoice.codigo",
          valor_esperado: "existing_key",
          orden: 0,
        }}
        catalogOptions={["existing_key", "another_key"]}
        onUpdate={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(html).toContain('aria-label="Catalog key"');
    expect(html).toContain('value="another_key"');
    expect(html).toContain("Ver catálogo");
  });
});
