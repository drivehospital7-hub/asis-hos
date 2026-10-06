import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { GroupModeFields } from "./GroupModeFields";

const noop = vi.fn();

describe("GroupModeFields", () => {
  it("row mode explains itself and hides the builder", () => {
    const html = renderToStaticMarkup(
      <GroupModeFields mode="row" onModeChange={noop} paramsText="" onParamsChange={noop} />,
    );
    expect(html).toContain("Por fila");
    expect(html).toContain("Agrupada por factura");
    expect(html).not.toContain("Agrupar por");
  });

  it("group mode with empty params shows the builder", () => {
    const html = renderToStaticMarkup(
      <GroupModeFields mode="group" onModeChange={noop} paramsText="" onParamsChange={noop} />,
    );
    expect(html).toContain("Agrupar por");
    expect(html).toContain("Agregaciones");
    expect(html).toContain("numero_factura");
  });

  it("group mode with exotic params falls back to raw JSON", () => {
    const html = renderToStaticMarkup(
      <GroupModeFields
        mode="group"
        onModeChange={noop}
        paramsText='[{"umbral": 3}]'
        onParamsChange={noop}
      />,
    );
    expect(html).toContain("personalizados");
    expect(html).not.toContain("Agrupar por");
  });

  it("existing group config renders its values", () => {
    const html = renderToStaticMarkup(
      <GroupModeFields
        mode="group"
        onModeChange={noop}
        paramsText='[{"group_by": "numero_factura", "aggregations": [{"function": "collect_set", "field": "codigo_tipo_procedimiento", "target": "collect_set_tipos"}], "filter_field": "tarifario", "filter_value": "Soat"}]'
        onParamsChange={noop}
      />,
    );
    expect(html).toContain("Soat");
    expect(html).toContain("collect_set_tipos");
  });
});
