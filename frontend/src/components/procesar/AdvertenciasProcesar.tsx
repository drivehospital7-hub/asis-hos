import { AlertTriangle, FileWarning } from "lucide-react";
import { Card } from "@/components/ui/card";
import type {
  ReglaSinDatos,
  ValorNoCatalogado,
} from "./types";

interface AdvertenciasProcesarProps {
  advertenciasReglas?: ReglaSinDatos[];
  valoresNoCatalogados?: ValorNoCatalogado[];
}

/**
 * Warning cards for /procesar: rules that evaluated blind (missing mapped
 * columns) and unrecognized Excel values (outside allowlist catalogs).
 * Renders nothing when there is nothing to warn about. Display-only:
 * processing already succeeded when these arrive.
 */
export function AdvertenciasProcesar({
  advertenciasReglas = [],
  valoresNoCatalogados = [],
}: AdvertenciasProcesarProps) {
  if (advertenciasReglas.length === 0 && valoresNoCatalogados.length === 0) {
    return null;
  }

  return (
    <div className="mb-6 space-y-4">
      {advertenciasReglas.length > 0 && (
        <Card className="p-6 border-warning/30 bg-warning/5 shadow-none">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-warning/10 text-warning-foreground">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-display font-semibold text-foreground">
                Reglas sin datos ({advertenciasReglas.length})
              </h2>
              <p className="text-xs text-muted-foreground">
                Estas reglas leyeron columnas que no están en el Excel y pueden no haber detectado nada
              </p>
            </div>
          </div>
          <ul className="space-y-2">
            {advertenciasReglas.map((a) => (
              <li
                key={`${a.regla_id ?? a.regla}`}
                className="rounded-md border border-border bg-card px-4 py-3"
              >
                <p className="text-xs font-semibold text-foreground">
                  {a.regla}{" "}
                  <span className="font-mono font-normal text-muted-foreground">
                    {a.regla_id != null ? `#${a.regla_id}` : ""}
                  </span>
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Columnas faltantes:{" "}
                  <span className="font-mono text-foreground/80">
                    {a.campos_faltantes.join(", ")}
                  </span>
                </p>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {valoresNoCatalogados.length > 0 && (
        <Card className="p-6 border-warning/30 bg-warning/5 shadow-none">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-warning/10 text-warning-foreground">
              <FileWarning className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-display font-semibold text-foreground">
                Valores no reconocidos ({valoresNoCatalogados.length})
              </h2>
              <p className="text-xs text-muted-foreground">
                Valores del Excel fuera de los catálogos válidos — revisá si cambió algo en la producción
              </p>
            </div>
          </div>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/60 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="text-left font-medium px-4 py-3">Campo</th>
                  <th className="text-left font-medium px-4 py-3">Valor</th>
                  <th className="text-right font-medium px-4 py-3">Filas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {valoresNoCatalogados.map((v, i) => (
                  <tr
                    key={`${v.campo}-${v.valor}-${i}`}
                    className="hover:bg-muted/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-foreground/70">{v.campo}</td>
                    <td className="px-4 py-3 text-xs text-foreground/80 max-w-xs">{v.valor}</td>
                    <td className="px-4 py-3 text-xs text-right text-foreground/80">{v.conteo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
