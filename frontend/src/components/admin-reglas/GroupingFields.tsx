/** Grouping fields for rule-declared /procesar error groups.
 *
 * Lets admins manage `reglas.grupo_error` plus the Detalle A/B mapping
 * columns without touching code. Mirrors the canonical labels in
 * `app/constants/grupo_error.py`.
 */

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
 * factura/problema/regla/severidad/param_config_id + the ~30 row fields
 * copied into the problem dict) plus the extra keys produced by
 * formatters/detectors in `app/services/normalized_rows.py`
 * (`ide_contrato_deberia`, `tipo_actual`, `centro_actual`, ...).
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
  "edad",
  "date.edad",
  "date.edad_meses",
  "numero_identificacion",
  // Extra keys added by formatters / detectors
  "numero_factura",
  "tipo_factura",
  "entidad",
  "entidad_cobrar_nombre",
  "ide_contrato_actual",
  "ide_contrato_deberia",
  "ide_actual",
  "ide_deberia",
  "tipo_actual",
  "tipo_deberia",
  "centro_actual",
  "centro_deberia",
  "cod_entidad_actual",
  "cod_entidad_esperado",
  "edad_anios",
  "edad_meses",
  "cantidad_repeticiones",
  "cantidad_esperada",
  "count",
  "codigo_profesional",
  "descripcion",
  "detalle",
  "nota",
  "observacion",
  "estancia_str",
  "valores",
  "tipos",
  "facturas",
  "pares_duplicados",
  "total_pares",
];

interface Props {
  grupoError: string;
  detalleACampo: string;
  detalleBCampo: string;
  descripcionTemplate: string;
  disabled: boolean;
  onChange: (field: string, value: string) => void;
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
          placeholder="e.g. Center {centro_actual}"
          className={inputClassName}
          style={inputStyle}
          disabled={disabled}
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1" style={labelStyle}>
          Detail A field
        </label>
        <select
          name="detalle_a_campo"
          value={DETALLE_FIELD_KEYS.includes(detalleACampo) || detalleACampo === "" ? detalleACampo : "__legacy__"}
          onChange={(e) =>
            onChange(
              "detalle_a_campo",
              e.target.value === "__legacy__" ? detalleACampo : e.target.value,
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
          {detalleACampo !== "" && !DETALLE_FIELD_KEYS.includes(detalleACampo) && (
            <option value="__legacy__">{detalleACampo}</option>
          )}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1" style={labelStyle}>
          Detail B field
        </label>
        <select
          name="detalle_b_campo"
          value={DETALLE_FIELD_KEYS.includes(detalleBCampo) || detalleBCampo === "" ? detalleBCampo : "__legacy__"}
          onChange={(e) =>
            onChange(
              "detalle_b_campo",
              e.target.value === "__legacy__" ? detalleBCampo : e.target.value,
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
          {detalleBCampo !== "" && !DETALLE_FIELD_KEYS.includes(detalleBCampo) && (
            <option value="__legacy__">{detalleBCampo}</option>
          )}
        </select>
      </div>
    </div>
  );
}
