/** Shared /procesar result types (used by /procesar and the simulator). */

export interface AnexoItem {
  campo: string;
  valor: string;
}

export interface FacturaItem {
  tipo_error: string;
  factura: string;
  fec_factura: string;
  responsable_cierra: string;
  descripcion: string;
  procedimiento: string;
  detalle: string;
  fecha_cierre_vacia?: boolean;
  regla?: string;
  /** Numero de rama (1-based, orden del editor) que disparo la regla. */
  rama?: number;
  rama_id?: number;
  _enviada?: boolean;
  /** Anexo efimero display-only desde el Excel principal (solo furips). */
  anexo?: AnexoItem[];
}

export interface TipoGroup {
  tipo: string;
  tipo_key: string;
  cantidad: number;
  cantidad_mostradas?: number;
  facturas: FacturaItem[];
}

export interface FacturaGroup {
  tipo_factura: string;
  total: number;
  tipos: TipoGroup[];
}

export interface ProcesarResultData {
  errores: FacturaGroup[];
  total_errores: number;
  tipos_procesados: string[];
  columnas?: string[];
  export_id?: string | null;
  advertencias_reglas?: ReglaSinDatos[];
  valores_no_catalogados?: ValorNoCatalogado[];
}

/** Regla que leyo campos sin columna mapeada (antirregla muda). */
export interface ReglaSinDatos {
  regla: string;
  regla_id: number | null;
  campos_faltantes: string[];
}

/** Valor del Excel fuera de los catalogos allowlist. */
export interface ValorNoCatalogado {
  campo: string;
  valor: string;
  conteo: number;
}
