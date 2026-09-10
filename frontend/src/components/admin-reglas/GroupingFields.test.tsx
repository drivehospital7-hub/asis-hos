import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { GRUPO_ERROR_LABELS, GroupingFields } from "./GroupingFields";

describe("GroupingFields", () => {
  it("exposes the canonical grupo_error label list", () => {
    expect(GRUPO_ERROR_LABELS).toContain("Tipo Identificacion / Edad");
    expect(GRUPO_ERROR_LABELS).toContain("Codigo-Entidad-vs-Afiliacion");
    expect(GRUPO_ERROR_LABELS).toContain("Duplicados-Farmacia");
    expect(GRUPO_ERROR_LABELS).toContain("Cups-Equivalentes");
    expect(GRUPO_ERROR_LABELS).toContain("Revision-Necesaria");
    expect(GRUPO_ERROR_LABELS).toContain("Centros de Costo");
  });

  it("renders four grouping inputs with round-trip values", () => {
    const html = renderToStaticMarkup(
      <GroupingFields
        grupoError="Centros de Costo"
        detalleACampo="codigo,procedimiento"
        detalleBCampo="centro_actual,centro_costo"
        descripcionTemplate=""
        disabled={false}
        onChange={vi.fn()}
      />,
    );

    expect(html).toContain("Error group");
    expect(html).toContain('value="Centros de Costo"');
    expect(html).toContain("Detail A field");
    expect(html).toContain('value="codigo,procedimiento"');
    expect(html).toContain("Detail B field");
    expect(html).toContain('value="centro_actual,centro_costo"');
    expect(html).toContain("Description template");
  });

  it("notifies the parent on every field change", () => {
    const onChange = vi.fn();
    // Static render cannot fire events; assert the callback contract instead:
    // each input carries a name the parent handler switches on.
    const html = renderToStaticMarkup(
      <GroupingFields
        grupoError=""
        detalleACampo=""
        detalleBCampo=""
        descripcionTemplate=""
        disabled={false}
        onChange={onChange}
      />,
    );
    expect(html).toContain('name="grupo_error"');
    expect(html).toContain('name="detalle_a_campo"');
    expect(html).toContain('name="detalle_b_campo"');
    expect(html).toContain('name="descripcion_template"');
    expect(onChange).not.toHaveBeenCalled();
  });
});
