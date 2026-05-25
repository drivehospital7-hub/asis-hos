/** NOMBRE_MAP — maps short name from cronograma to full name. */
export const NOMBRE_MAP: Record<string, string> = {
  CARLOS: "CARLOS OMAR",
  ALEJANDRA: "ALEJANDRA ESPAÑA",
  YULIETH: "DANIELA PAEZ",
  CAROLINA: "ANGIE ARIAS",
};

/** Toast auto-dismiss duration in milliseconds. */
export const TOAST_DURATION = 2500;

/** Schedule table column headers. */
export const SCHEDULE_HEADERS = ["Día", "07:00-13:00", "13:00-19:00", "19:00-07:00"] as const;

/** Results table column labels. */
export const RESULT_HEADERS = [
  "Fecha Crea",
  "Fecha Egreso",
  "N° Factura",
  "Estado",
  "Responsable",
  "Área",
  "Paciente",
  "HC Pendiente",
  "Envío",
] as const;

/** Header strings used to detect columns in autoDetectColumns (lowercased). */
export const HEADER_DETECTION: Record<string, string> = {
  fechaCrea: "fecha crea",
  fechaCierre: "fec. cierre",
  fechaCierreAlt: "fec.cierre",
  fechaEgreso: "fecha egreso",
  fechaEgresoAlt: "fechaegreso",
  factura: "n factura",
  facturaAlt: "factura",
  estado: "estado",
  area: "area",
  historia: "n historia",
  historiaAlt: "historia",
  paciente: "paciente",
  hcPendiente: "hc pendiente",
  hcPendienteAlt: "h.c",
};

/** Value patterns used for fallback column detection. */
export const PATTERNS = {
  date: /^\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}$/,
  factPrefix: /^(CAP|FEV)/i,
  factPrefixOnly: /^(CAP|FEV)$/i,
  factFull: /^(CAP|FEV)\d+/i,
  numericLong: /^\d{8,}$/,
  estado: /^(Abierta|Pendiente|Cerrada|Anulado)$/i,
  hc: /^(Si|No|Sí)$/i,
  area: /^(Urgencias|Hospitalización)$/i,
  name: /^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ]/,
} as const;
