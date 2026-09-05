import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { ValueInput } from "./ValueInput";

describe("ValueInput catalog keys", () => {
  it("renders a select for catalog options", () => {
    const element = ValueInput({
      valueType: "string",
      value: "",
      catalogOptions: ["catalog_a", "catalog_b"],
      onChange: vi.fn(),
    });

    const html = renderToStaticMarkup(element);
    expect(html).toContain("catalog_a");
    expect(html).toContain("catalog_b");
  });

  it("updates the expected value when a catalog key is selected", () => {
    const onChange = vi.fn();
    const element = ValueInput({
      valueType: "string",
      value: "",
      catalogOptions: ["catalog_a"],
      onChange,
    });

    element.type({ ...element.props }).props.onChange({
      target: { value: "catalog_a" },
    });

    expect(onChange).toHaveBeenCalledWith("catalog_a");
  });
});
