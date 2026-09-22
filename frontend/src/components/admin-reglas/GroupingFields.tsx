/** Grouping fields for rule-declared /procesar error groups.
 *
 * Lets admins manage `reglas.grupo_error` plus the Detalle A/B mapping
 * columns without touching code. Mirrors the canonical labels in
 * `app/constants/grupo_error.py`.
 */

import { useState } from "react";

export const GRUPO_ERROR_LABELS: string[] = [
  "Tipo Identificacion / Edad",
  "Codigo-Entidad-vs-Afiliacion",
  "Duplicados-Farmacia",
  "Cups-Equivalentes",
  "Revision-Necesaria",
  "Centros de Costo",
  "IDE Contrato",
  "Profesionales",
  "Cantidades",
  "Cantidades SOAT",
  "Cantidades Hospitalización",
  "Cantidades SOAT Hospitalización",
  "Estancias",
  "Decimales",
  "Tipo Usuario",
  "Copago vs Entidad",
  "Cups Sin Contrato",
  "MAL CAPITADO",
  "Ruta Duplicada",
  "Doble Tipo Procedimiento",
  "Codigos Hospitalizacion",
  "Cronograma Bacteriologas",
  "Duplicado ID-Codigo",
];

/**
 * Canonical keys available in the engine `problem` dict (`item`) that
 * `detalle_a_campo` / `detalle_b_campo` can point to.
 *
 * Derived from `app/services/engine/engine.py` (base keys
 * factura/problema/regla/severidad/param_config_id + the row fields
 * copied into the problem dict) plus the group-level keys produced by
 * `app/services/engine/group_evaluator.py` (`count`, `facturas`) and
 * `app/services/normalized_rows.py` (`estancia_str`, plus
 * `codigo_profesional` in group context only).
 *
 * `descripcion_template` stays free text — braces are documented
 * via its placeholder instead.
 */
export const DETALLE_FIELD_KEYS: string[] = [
  // Base problem keys
  "factura",
  "problema",
  "regla",
  "severidad",
  "param_config_id",
  // Row fields copied by the engine
  "codigo",
  "codigo_equiv",
  "procedimiento",
  "tipo_identificacion",
  "codigo_entidad_cobrar",
  "tipo_procedimiento",
  "vlr_subsidiado",
  "vlr_procedimiento",
  "cantidad",
  "convenio_facturado",
  "centro_costo",
  "ide_contrato",
  "entidad_cobrar",
  "entidad_afiliacion",
  "tipo_usuario",
  "vlr_copago",
  "codigo_tipo_procedimiento",
  "laboratorio",
  "tarifario",
  "tipo_factura_descripcion",
  "responsable_cierra",
  "profesional_atiende",
  "identificacion",
  "fec_nacimiento",
  "fec_factura",
  "date.edad",
  "date.edad_meses",
  // Extra keys produced by group formatters (group context only)
  "count",
  "codigo_profesional",
  "estancia_str",
  "facturas",
];

interface Props {
  grupoError: string;
  detalleACampo: string;
  detalleBCampo: string;
  descripcionTemplate: string;
  disabled: boolean;
  onChange: (field: string, value: string) => void;
}

export interface DetalleParsed {
  mode: "simple" | "template";
  label: string;
  field1: string;
  field2: string;
  raw?: string;
}

export function composeDetalle(
  label: string,
  field1: string,
  field2: string,
): string {
  const l = (label ?? "").trim();
  const f1 = (field1 ?? "").trim();
  const f2 = (field2 ?? "").trim();
  if (!f1) return "";
  if (!l && !f2) return f1;
  return `${l ? `${l}: ` : ""}{${f1}}${f2 ? ` - {${f2}}` : ""}`;
}

export function parseDetalle(stored: string): DetalleParsed {
  const s = (stored ?? "").trim();
  if (!s) return { mode: "simple", label: "", field1: "", field2: "" };
  let m = s.match(/^([^{}]+?):\s*\{([^{}]+)\}\s*-\s*\{([^{}]+)\}$/);
  if (m) {
    const label = m[1].trim();
    const field1 = m[2].trim();
    const field2 = m[3].trim();
    if (field1 && field2) return { mode: "template", label, field1, field2 };
  }
  m = s.match(/^([^{}]+?):\s*\{([^{}]+)\}$/);
  if (m) {
    const label = m[1].trim();
    const field1 = m[2].trim();
    if (label && field1) return { mode: "template", label, field1, field2: "" };
  }
  m = s.match(/^\{([^{}]+)\}\s*-\s*\{([^{}]+)\}$/);
  if (m) {
    const field1 = m[1].trim();
    const field2 = m[2].trim();
    if (field1 && field2) return { mode: "template", label: "", field1, field2 };
  }
  m = s.match(/^\{([^{}]+)\}$/);
  if (m) {
    const field1 = m[1].trim();
    if (field1) return { mode: "template", label: "", field1, field2: "" };
  }
  if (!/[{}\\:,=]/.test(s) && !/\s/.test(s))
    return { mode: "simple", label: "", field1: s, field2: "" };
  return { mode: "template", label: "", field1: "", field2: "", raw: stored };
}

function DetalleEditor({
  id,
  stored,
  disabled,
  onChange,
}: {
  id: "a" | "b";
  stored: string;
  disabled: boolean;
  onChange: (field: string, value: string) => void;
}) {
  const fieldName = id === "a" ? "detalle_a_campo" : "detalle_b_campo";
  const title = id === "a" ? "Detail A field" : "Detail B field";
  const parsed = parseDetalle(stored);
  const [forced, setForced] = useState<"auto" | "builder" | "raw">("auto");
  const isRaw =
    forced === "raw" || (forced === "auto" && parsed.raw !== undefined);
  const campo1Value =
    DETALLE_FIELD_KEYS.includes(parsed.field1) || parsed.field1 === ""
      ? parsed.field1
      : "__legacy__";
  const campo2Value = DETALLE_FIELD_KEYS.includes(parsed.field2)
    ? parsed.field2
    : "";

  if (isRaw) {
    return (
      <div>
        <label className="block text-sm font-medium mb-1" style={labelStyle}>
          {title}
        </label>
        <input
          type="text"
          name={`${fieldName}_template`}
          value={stored}
          onChange={(e) => onChange(fieldName, e.target.value)}
          placeholder="e.g. Procedimiento: {codigo} - {procedimiento}"
          className={inputClassName}
          style={inputStyle}
          disabled={disabled}
        />
        <button
          type="button"
          onClick={() => setForced("builder")}
          disabled={disabled}
          className="mt-1 text-xs underline"
        >
          Volver a campos
        </button>
      </div>
    );
  }

  return (
    <div>
      <label className="block text-sm font-medium mb-1" style={labelStyle}>
        {title}
      </label>
      <select
        name={fieldName}
        value={campo1Value}
        onChange={(e) =>
          onChange(
            fieldName,
            e.target.value === "__legacy__"
              ? composeDetalle(parsed.label, parsed.field1, parsed.field2)
              : composeDetalle(parsed.label, e.target.value, parsed.field2),
          )
        }
        className={inputClassName}
        style={inputStyle}
        disabled={disabled}
      >
        <option value="">— auto —</option>
        {DETALLE_FIELD_KEYS.map((key) => (
          <option key={key} value={key}>
            {key}
          </option>
        ))}
        {parsed.field1 !== "" && !DETALLE_FIELD_KEYS.includes(parsed.field1) && (
          <option value="__legacy__">{parsed.field1}</option>
        )}
      </select>
      <input
        type="text"
        name={`detalle_${id}_label`}
        value={parsed.label}
        onChange={(e) =>
          onChange(
            fieldName,
            composeDetalle(e.target.value, parsed.field1, parsed.field2),
          )
        }
        placeholder="Label ej. Procedimiento"
        className={`${inputClassName} mt-2`}
        style={inputStyle}
        disabled={disabled}
      />
      <select
        name={`detalle_${id}_campo2`}
        value={campo2Value}
        onChange={(e) =>
          onChange(
            fieldName,
            composeDetalle(parsed.label, parsed.field1, e.target.value),
          )
        }
        className={`${inputClassName} mt-2`}
        style={inputStyle}
        disabled={disabled}
      >
        <option value="">— none —</option>
        {DETALLE_FIELD_KEYS.map((key) => (
          <option key={key} value={key}>
            {key}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={() => setForced("raw")}
        disabled={disabled}
        className="mt-1 text-xs underline"
      >
        Usar plantilla
      </button>
    </div>
  );
}

const inputClassName =
  "w-full rounded-lg border px-4 py-2.5 text-sm outline-none focus:border-primary";

const inputStyle = { borderColor: "oklch(0.55 0.04 160 / 0.2)" };

const labelStyle = { color: "oklch(0.55 0.04 160)" };

export function GroupingFields({
  grupoError,
  detalleACampo,
  detalleBCampo,
  descripcionTemplate,
  disabled,
  onChange,
}: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
      <div>
        <label className="block text-sm font-medium mb-1" style={labelStyle}>
          Error group
        </label>
        <select
          name="grupo_error"
          value={GRUPO_ERROR_LABELS.includes(grupoError) || grupoError === "" ? grupoError : "__legacy__"}
          onChange={(e) =>
            onChange(
              "grupo_error",
              e.target.value === "__legacy__" ? grupoError : e.target.value,
            )
          }
          className={inputClassName}
          style={inputStyle}
          disabled={disabled}
        >
          <option value="">— auto —</option>
          {GRUPO_ERROR_LABELS.map((label) => (
            <option key={label} value={label}>
              {label}
            </option>
          ))}
          {grupoError !== "" && !GRUPO_ERROR_LABELS.includes(grupoError) && (
            <option value="__legacy__">{grupoError}</option>
          )}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1" style={labelStyle}>
          Description template
        </label>
        <input
          type="text"
          name="descripcion_template"
          value={descripcionTemplate}
          onChange={(e) => onChange("descripcion_template", e.target.value)}
          placeholder="e.g. Center {centro_costo}"
          className={inputClassName}
          style={inputStyle}
          disabled={disabled}
        />
      </div>
      <DetalleEditor id="a" stored={detalleACampo} disabled={disabled} onChange={onChange} />
      <DetalleEditor id="b" stored={detalleBCampo} disabled={disabled} onChange={onChange} />
    </div>
  );
}
