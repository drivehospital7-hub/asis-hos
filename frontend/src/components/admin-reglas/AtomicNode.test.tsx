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

  it("row mode hides set-only operators and group.* sources", () => {
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
        mode="row"
        onUpdate={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(html).not.toContain('value="set_contains_all"');
    expect(html).not.toContain('value="set_intersects"');
    expect(html).not.toContain('value="group.collect_set_codigo"');
    // row operators stay
    expect(html).toContain("Igual (=)");
    expect(html).toContain('value="invoice.centro_costo"');
  });

  it("group mode keeps set operators and group sources", () => {
    const html = renderToStaticMarkup(
      <AtomicNode
        node={{
          id: 1,
          regla_id: 1,
          padre_id: 2,
          tipo: "atomic",
          operador: "set_intersects",
          fuente_datos: "group.collect_set_codigo",
          valor_esperado: ["03"],
          orden: 0,
        }}
        mode="group"
        onUpdate={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(html).toContain('value="set_intersects"');
    expect(html).toContain('value="group.collect_set_codigo"');
  });

  it("marks unknown fuente_datos as invalid without blocking", () => {
    const html = renderToStaticMarkup(
      <AtomicNode
        node={{
          id: 1,
          regla_id: 1,
          padre_id: 2,
          tipo: "atomic",
          operador: "eq",
          fuente_datos: "invoice.campo_inexistente",
          valor_esperado: "",
          orden: 0,
        }}
        mode="group"
        onUpdate={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(html).toContain('aria-invalid="true"');
    // known sources stay valid
    const okHtml = renderToStaticMarkup(
      <AtomicNode
        node={{
          id: 1,
          regla_id: 1,
          padre_id: 2,
          tipo: "atomic",
          operador: "eq",
          fuente_datos: "group.collect_set_tipos",
          valor_esperado: "",
          orden: 0,
        }}
        mode="group"
        onUpdate={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    expect(okHtml).not.toContain('aria-invalid="true"');
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
