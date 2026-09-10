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
        <input
          type="text"
          name="grupo_error"
          list="grupo-error-labels"
          value={grupoError}
          onChange={(e) => onChange("grupo_error", e.target.value)}
          placeholder="e.g. Centros de Costo"
          className={inputClassName}
          style={inputStyle}
          disabled={disabled}
        />
        <datalist id="grupo-error-labels">
          {GRUPO_ERROR_LABELS.map((label) => (
            <option key={label} value={label} />
          ))}
        </datalist>
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
        <input
          type="text"
          name="detalle_a_campo"
          value={detalleACampo}
          onChange={(e) => onChange("detalle_a_campo", e.target.value)}
          placeholder="e.g. codigo,procedimiento"
          className={inputClassName}
          style={inputStyle}
          disabled={disabled}
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1" style={labelStyle}>
          Detail B field
        </label>
        <input
          type="text"
          name="detalle_b_campo"
          value={detalleBCampo}
          onChange={(e) => onChange("detalle_b_campo", e.target.value)}
          placeholder="e.g. centro_actual,centro_costo"
          className={inputClassName}
          style={inputStyle}
          disabled={disabled}
        />
      </div>
    </div>
  );
}
