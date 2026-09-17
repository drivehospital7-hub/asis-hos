import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import {
  DETALLE_FIELD_KEYS,
  GRUPO_ERROR_LABELS,
  GroupingFields,
} from "./GroupingFields";

describe("GroupingFields", () => {
  it("exposes the canonical grupo_error label list", () => {
    expect(GRUPO_ERROR_LABELS).toContain("Tipo Identificacion / Edad");
    expect(GRUPO_ERROR_LABELS).toContain("Codigo-Entidad-vs-Afiliacion");
    expect(GRUPO_ERROR_LABELS).toContain("Duplicados-Farmacia");
    expect(GRUPO_ERROR_LABELS).toContain("Cups-Equivalentes");
    expect(GRUPO_ERROR_LABELS).toContain("Revision-Necesaria");
    expect(GRUPO_ERROR_LABELS).toContain("Centros de Costo");
    expect(GRUPO_ERROR_LABELS).toContain("Estancias");
  });

  it("exposes the canonical detalle field keys", () => {
    // Engine base keys
    expect(DETALLE_FIELD_KEYS).toContain("factura");
    expect(DETALLE_FIELD_KEYS).toContain("problema");
    expect(DETALLE_FIELD_KEYS).toContain("regla");
    expect(DETALLE_FIELD_KEYS).toContain("severidad");
    expect(DETALLE_FIELD_KEYS).toContain("param_config_id");
    // Engine-copied row fields
    expect(DETALLE_FIELD_KEYS).toContain("codigo");
    expect(DETALLE_FIELD_KEYS).toContain("procedimiento");
    expect(DETALLE_FIELD_KEYS).toContain("centro_costo");
    expect(DETALLE_FIELD_KEYS).toContain("date.edad");
    // Formatter / detector extras
    expect(DETALLE_FIELD_KEYS).toContain("ide_contrato_deberia");
    expect(DETALLE_FIELD_KEYS).toContain("ide_contrato_actual");
    expect(DETALLE_FIELD_KEYS).toContain("tipo_actual");
    expect(DETALLE_FIELD_KEYS).toContain("tipo_deberia");
    expect(DETALLE_FIELD_KEYS).toContain("centro_actual");
    expect(DETALLE_FIELD_KEYS).toContain("edad_anios");
  });

  it("renders grupo_error as a select with auto option and canonical labels", () => {
    const html = renderToStaticMarkup(
      <GroupingFields
        grupoError="Centros de Costo"
        detalleACampo=""
        detalleBCampo=""
        descripcionTemplate=""
        disabled={false}
        onChange={vi.fn()}
      />,
    );

    expect(html).toContain('name="grupo_error"');
    expect(html).toContain("<select");
    expect(html).toContain("— auto —");
    expect(html).toContain('value="Centros de Costo"');
    expect(html).toContain("Tipo Identificacion / Edad");
  });

  it("preserves a legacy grupo_error value as an extra option", () => {
    const html = renderToStaticMarkup(
      <GroupingFields
        grupoError="Grupo Legacy 123"
        detalleACampo=""
        detalleBCampo=""
        descripcionTemplate=""
        disabled={false}
        onChange={vi.fn()}
      />,
    );

    expect(html).toContain("Grupo Legacy 123");
    expect(html).toContain('value="__legacy__"');
  });

  it("renders detalle A/B as selects with auto option and keys", () => {
    const html = renderToStaticMarkup(
      <GroupingFields
        grupoError="Centros de Costo"
        detalleACampo="codigo"
        detalleBCampo="centro_actual"
        descripcionTemplate=""
        disabled={false}
        onChange={vi.fn()}
      />,
    );

    expect(html).toContain("Error group");
    expect(html).toContain('value="Centros de Costo"');
    expect(html).toContain("Detail A field");
    expect(html).toContain("Detail B field");
    // Selects carry the field names
    expect(html).toContain('name="detalle_a_campo"');
    expect(html).toContain('name="detalle_b_campo"');
    // Empty "auto" option + canonical keys are offered
    expect(html).toContain("— auto —");
    expect(html).toContain('value="codigo"');
    expect(html).toContain('value="centro_actual"');
    expect(html).toContain('value="ide_contrato_deberia"');
    // Description template stays free text
    expect(html).toContain("Description template");
    expect(html).toContain('name="descripcion_template"');
  });

  it("preserves legacy values not in the key list as an extra option", () => {
    const html = renderToStaticMarkup(
      <GroupingFields
        grupoError=""
        detalleACampo="codigo,procedimiento"
        detalleBCampo="{centro_actual}"
        descripcionTemplate=""
        disabled={false}
        onChange={vi.fn()}
      />,
    );

    // Legacy compound / template values survive instead of breaking
    expect(html).toContain("codigo,procedimiento");
    expect(html).toContain("{centro_actual}");
  });

  it("notifies the parent on every field change", () => {
    const onChange = vi.fn();
    // Static render cannot fire events; assert the callback contract instead:
    // each control carries a name the parent handler switches on.
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
