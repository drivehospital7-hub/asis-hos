import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { FUENTES_DATOS } from "./operators";
import { resolveOperatorInput } from "./OperatorSelector";
import { SearchableSelect } from "./SearchableSelect";

describe("conditional searchable selects", () => {
  it("lists every fuente_datos used by seeded rules", () => {
    for (const fuente of [
      "invoice.codigo_profesional",
      "invoice.collect_set_codigo",
      "invoice.collect_set_tarifario",
      "invoice.count",
      "invoice.estancia_horas",
    ]) {
      expect(FUENTES_DATOS).toContain(fuente);
    }
  });

  it("renders a searchable input bound to a datalist", () => {
    const html = renderToStaticMarkup(
      <SearchableSelect
        value="invoice.codigo_profesional"
        options={FUENTES_DATOS}
        onChange={vi.fn()}
        ariaLabel="Fuente de datos"
        placeholder="-- fuente -- (escribí para buscar)"
      />,
    );

    expect(html).toContain('aria-label="Fuente de datos"');
    expect(html).toContain('value="invoice.codigo_profesional"');
    expect(html).toContain('value="invoice.codigo"');
    expect(html).toContain("<datalist");
  });

  it("resolves operator labels back to values", () => {
    const options = [
      { value: "eq", label: "Igual (=) — Comparación" },
      { value: "cat_in", label: "En catálogo (cat_in) — Set / Lista" },
    ];

    expect(resolveOperatorInput("eq", options)).toBe("eq");
    expect(resolveOperatorInput("Igual (=) — Comparación", options)).toBe("eq");
    expect(resolveOperatorInput("igual (=) — comparación", options)).toBe("eq");
    expect(resolveOperatorInput("", options)).toBe("");
  });
});
