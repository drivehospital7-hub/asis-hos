import { describe, expect, it } from "vitest";
import {
  getGroupConfig,
  isBuilderCompatibleParams,
  parseRuleMode,
} from "./operators";

describe("parseRuleMode", () => {
  it("defaults to row for empty / null / non-group params", () => {
    expect(parseRuleMode(null)).toBe("row");
    expect(parseRuleMode(undefined)).toBe("row");
    expect(parseRuleMode([])).toBe("row");
    expect(parseRuleMode([{ umbral: 3 }])).toBe("row");
    expect(parseRuleMode("group_by")).toBe("row");
  });

  it("detects group mode from parametros[0].group_by", () => {
    expect(parseRuleMode([{ group_by: "numero_factura" }])).toBe("group");
    expect(
      parseRuleMode([{ group_by: ["a", "b"], aggregations: [] }]),
    ).toBe("group");
  });
});

describe("getGroupConfig", () => {
  it("returns null outside group mode", () => {
    expect(getGroupConfig(null)).toBeNull();
    expect(getGroupConfig([{ umbral: 1 }])).toBeNull();
  });

  it("extracts group_by + aggregations + optional filter", () => {
    const cfg = getGroupConfig([
      {
        group_by: "numero_factura",
        aggregations: [{ function: "collect_set", field: "codigo", target: "collect_set_codigo" }],
        filter_field: "tarifario",
        filter_value: "Soat",
      },
    ]);
    expect(cfg?.group_by).toBe("numero_factura");
    expect(cfg?.aggregations).toHaveLength(1);
    expect(cfg?.filter_field).toBe("tarifario");
    expect(cfg?.filter_value).toBe("Soat");
  });

  it("defaults missing aggregations to []", () => {
    expect(getGroupConfig([{ group_by: "numero_factura" }])?.aggregations).toEqual([]);
  });
});

describe("empty operators", () => {
  it("exposes is_empty / not_empty as value-less operators", async () => {
    const mod = await import("./operators");
    const values = mod.OPERADORES_ATOMICOS.map((o) => o.value);
    expect(values).toContain("is_empty");
    expect(values).toContain("not_empty");
    expect(mod.getValueTypeForOperator("is_empty")).toBe("hidden");
    expect(mod.getValueTypeForOperator("not_empty")).toBe("hidden");
  });
});

describe("isBuilderCompatibleParams", () => {
  it("accepts empty text", () => {
    expect(isBuilderCompatibleParams("")).toBe(true);
    expect(isBuilderCompatibleParams("   ")).toBe(true);
  });

  it("accepts pure group config arrays", () => {
    expect(isBuilderCompatibleParams('[{"group_by": "numero_factura"}]')).toBe(true);
    expect(
      isBuilderCompatibleParams(
        '[{"group_by": "x", "aggregations": [], "filter_field": "a", "filter_value": "b"}]',
      ),
    ).toBe(true);
  });

  it("rejects exotic or invalid JSON", () => {
    expect(isBuilderCompatibleParams('[{"umbral": 3}]')).toBe(false);
    expect(isBuilderCompatibleParams('{"group_by": "x"}')).toBe(false);
    expect(isBuilderCompatibleParams("not json")).toBe(false);
  });
});
