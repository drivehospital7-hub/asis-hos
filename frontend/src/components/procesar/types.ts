/** Shared /procesar result types (used by /procesar and the simulator). */

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
  _enviada?: boolean;
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
}
