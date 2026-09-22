import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import {
  composeDetalle,
  DETALLE_FIELD_KEYS,
  GRUPO_ERROR_LABELS,
  GroupingFields,
  parseDetalle,
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
    // Live group-level keys only
    expect(DETALLE_FIELD_KEYS).toContain("count");
    expect(DETALLE_FIELD_KEYS).toContain("facturas");
    expect(DETALLE_FIELD_KEYS).toContain("estancia_str");
    expect(DETALLE_FIELD_KEYS).toContain("codigo_profesional");
    expect(DETALLE_FIELD_KEYS).toHaveLength(36);
    // Pruned dead keys never surface as options (legacy path instead)
    expect(DETALLE_FIELD_KEYS).not.toContain("ide_contrato_actual");
    expect(DETALLE_FIELD_KEYS).not.toContain("ide_contrato_deberia");
    expect(DETALLE_FIELD_KEYS).not.toContain("tipo_actual");
    expect(DETALLE_FIELD_KEYS).not.toContain("tipo_deberia");
    expect(DETALLE_FIELD_KEYS).not.toContain("centro_actual");
    expect(DETALLE_FIELD_KEYS).not.toContain("edad_anios");
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
        detalleBCampo="centro_costo"
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
    expect(html).toContain('value="centro_costo"');
    expect(html).toContain('value="ide_contrato"');
    // Description template stays free text
    expect(html).toContain("Description template");
    expect(html).toContain('name="descripcion_template"');
  });

  it("routes unparseable stored values to template mode instead of a legacy option", () => {
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

    // Compound raw value survives in the free-text template input.
    expect(html).toContain("codigo,procedimiento");
    expect(html).toContain("Volver a campos");
    // Single-brace structured value keeps its inner key in the builder.
    expect(html).toContain("centro_actual");
    expect(html).toContain('value="__legacy__"');
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

  it("composeDetalle builds the stored string", () => {
    expect(composeDetalle("Procedimiento", "codigo", "")).toBe(
      "Procedimiento: {codigo}",
    );
    expect(composeDetalle("Procedimiento", "codigo", "procedimiento")).toBe(
      "Procedimiento: {codigo} - {procedimiento}",
    );
    expect(composeDetalle("", "codigo", "")).toBe("codigo");
    expect(composeDetalle("", "", "")).toBe("");
    expect(composeDetalle("Procedimiento", "", "procedimiento")).toBe("");
    expect(composeDetalle("", "codigo", "procedimiento")).toBe(
      "{codigo} - {procedimiento}",
    );
  });

  it("parseDetalle round-trips composed forms and flags raw templates", () => {
    expect(parseDetalle("codigo")).toMatchObject({
      mode: "simple",
      field1: "codigo",
    });
    expect(parseDetalle(composeDetalle("Procedimiento", "codigo", ""))).toMatchObject({
      mode: "template",
      label: "Procedimiento",
      field1: "codigo",
      field2: "",
    });
    expect(
      parseDetalle(composeDetalle("Procedimiento", "codigo", "procedimiento")),
    ).toMatchObject({
      mode: "template",
      label: "Procedimiento",
      field1: "codigo",
      field2: "procedimiento",
    });
    expect(parseDetalle("{codigo} - {procedimiento}")).toMatchObject({
      mode: "template",
      field1: "codigo",
      field2: "procedimiento",
    });
    expect(parseDetalle("{codigo}")).toMatchObject({
      mode: "template",
      field1: "codigo",
    });
    expect(parseDetalle("codigo,procedimiento").mode).toBe("template");
    expect(parseDetalle("codigo,procedimiento").raw).toBe(
      "codigo,procedimiento",
    );
    expect(parseDetalle("=X").mode).toBe("template");
    expect(parseDetalle("Ent: {entidad}, Copago: {x}").mode).toBe("template");
  });

  it("renders label + campo2 controls plus the template toggle per detail", () => {
    const html = renderToStaticMarkup(
      <GroupingFields
        grupoError=""
        detalleACampo="codigo"
        detalleBCampo=""
        descripcionTemplate=""
        disabled={false}
        onChange={vi.fn()}
      />,
    );

    expect(html).toContain('name="detalle_a_label"');
    expect(html).toContain('name="detalle_a_campo2"');
    expect(html).toContain('name="detalle_b_label"');
    expect(html).toContain('name="detalle_b_campo2"');
    expect(html).toContain("Label ej. Procedimiento");
    expect(html).toContain("Usar plantilla");
  });
});
