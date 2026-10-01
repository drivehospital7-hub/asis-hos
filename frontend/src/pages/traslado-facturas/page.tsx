import { useEffect, useState } from "react";
import {
  Search,
  FolderOpen,
  FolderInput,
  Copy,
  ArrowUp,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";

interface Encontrada {
  codigo: string;
  full_path: string;
  facturador: string;
}

interface BuscarData {
  encontradas: Encontrada[];
  no_encontradas: string[];
  raices?: string[];
}

interface DirEntry {
  name: string;
  path: string;
}

interface ExplorarData {
  actual: string | null;
  padre: string | null;
  dirs: DirEntry[];
}

interface ConfigResponse {
  status: string;
  data: {
    roots: string[];
    fuente: string;
    ultima_actualizacion: string | null;
  };
  errors: string[];
}

// Header XHR: el decorador de permisos hace redirect al login en POST
// sin X-Requested-With; con el header devuelve 403 JSON.
const XHR_HEADERS = {
  "X-Requested-With": "XMLHttpRequest",
  "Content-Type": "application/json",
};

const TOAST_DURATION = 3500;

// Ruta absoluta estilo Windows (UNC \\servidor\...), unidad (C:\...)
// o UNC posix (//servidor/...). Igual criterio que monitoreo-carpetas.
function isValidDest(value: string): boolean {
  return /^(\\\\|[a-zA-Z]:[\\/]|\/\/)/.test(value.trim());
}

// Normalización simple para comparar raíces: `\` vs `/` + minúsculas.
function normalizeRoot(value: string): string {
  return value.trim().replace(/\//g, "\\").toLowerCase();
}
// "\\\\srv\\share\\dir" -> [["\\\\srv", ...], ...] con path acumulado.
function splitSegments(actual: string): Array<{ label: string; path: string }> {
  const unc = actual.startsWith("\\\\");
  const posixUnc = !unc && actual.startsWith("//");
  const parts = actual.split(/[\\/]+/).filter(Boolean);
  if (unc) {
    return parts.map((_, i) => ({
      label: i < 2 ? parts.slice(0, i + 1).join("\\") : parts[i],
      path: "\\\\" + parts.slice(0, i + 1).join("\\"),
    }));
  }
  if (posixUnc) {
    return parts.map((_, i) => ({
      label: parts[i],
      path: "//" + parts.slice(0, i + 1).join("/"),
    }));
  }
  if (/^[a-zA-Z]:$/.test(parts[0] ?? "")) {
    return parts.map((_, i) => ({
      label: parts[i],
      path: parts.slice(0, i + 1).join("\\"),
    }));
  }
  return parts.map((_, i) => ({
    label: parts[i],
    path: "/" + parts.slice(0, i + 1).join("/"),
  }));
}

function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, TOAST_DURATION);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background shadow-lg">
        {message}
      </div>
    </div>
  );
}

export function TrasladoFacturasPage({ can_write = false }: { can_write?: boolean }) {
  const [roots, setRoots] = useState<string[]>([]);
  const [selectedRoots, setSelectedRoots] = useState<string[]>([]);
  // Raíces manuales: solo viven en la sesión de búsqueda, no se guardan
  // en el config de monitoreo. Viajan en `raices[]` junto a las de config.
  const [manualRoots, setManualRoots] = useState<string[]>([]);
  const [manualInput, setManualInput] = useState("");
  const [manualError, setManualError] = useState("");
  const [codigos, setCodigos] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState("");
  const [encontradas, setEncontradas] = useState<Encontrada[]>([]);
  const [noEncontradas, setNoEncontradas] = useState<string[]>([]);
  const [searched, setSearched] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

  const [explorar, setExplorar] = useState<ExplorarData | null>(null);
  const [exploring, setExploring] = useState(false);
  const [destInput, setDestInput] = useState("");
  const [operating, setOperating] = useState<"move" | "copy" | null>(null);
  const [toast, setToast] = useState("");

  // Raíces: checks multi-select sobre la config de monitoreo (todas por defecto).
  useEffect(() => {
    fetch("/monitoreo-carpetas/config")
      .then((res) => res.json())
      .then((data: ConfigResponse) => {
        if (data.status === "success") {
          setRoots(data.data.roots);
          setSelectedRoots(data.data.roots);
        }
      })
      .catch(() => {
        // Silently fail — el aviso de vacío guía a monitoreo.
      });
  }, []);

  const fetchExplorar = async (path?: string) => {
    setExploring(true);
    try {
      const url = path
        ? `/traslado-facturas/explorar?path=${encodeURIComponent(path)}`
        : "/traslado-facturas/explorar";
      const res = await fetch(url);
      const json = await res.json();
      if (json.status === "success") {
        const data = json.data as ExplorarData;
        setExplorar(data);
        if (data.actual) setDestInput(data.actual);
      } else {
        setError(json.errors?.[0] || "Error al explorar carpetas");
      }
    } catch {
      setError("Error de conexión con el servidor");
    } finally {
      setExploring(false);
    }
  };

  // Al aparecer encontradas (con permiso) se carga el explorador una vez.
  useEffect(() => {
    if (can_write && encontradas.length > 0 && !explorar && !exploring) {
      void fetchExplorar();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [can_write, encontradas.length]);

  const toggleRoot = (root: string) => {
    setSelectedRoots((prev) =>
      prev.includes(root) ? prev.filter((r) => r !== root) : [...prev, root],
    );
  };

  const handleAddManual = () => {
    const value = manualInput.trim();
    if (!value) {
      setManualError("Escribí una ruta antes de agregar.");
      return;
    }
    const known = [...roots, ...manualRoots].map(normalizeRoot);
    if (known.includes(normalizeRoot(value))) {
      setManualError("Esa ruta ya está en la lista.");
      return;
    }
    setManualRoots((prev) => [...prev, value]);
    setManualInput("");
    setManualError("");
  };

  const handleRemoveManual = (root: string) => {
    setManualRoots((prev) => prev.filter((r) => r !== root));
  };

  // Raíces efectivas para `raices[]`: checks de config + manuales de sesión.
  const effectiveRoots = [...selectedRoots, ...manualRoots];

  const togglePath = (path: string) => {
    setSelected((prev) =>
      prev.includes(path) ? prev.filter((p) => p !== path) : [...prev, path],
    );
  };

  const toggleAll = () => {
    setSelected((prev) =>
      prev.length === encontradas.length ? [] : encontradas.map((e) => e.full_path),
    );
  };

  const handleBuscar = async () => {
    if (!codigos.trim()) return;
    setBuscando(true);
    setError("");
    try {
      const res = await fetch("/traslado-facturas/buscar", {
        method: "POST",
        headers: XHR_HEADERS,
        body: JSON.stringify({ raices: effectiveRoots, codigos }),
      });
      const json = await res.json();
      // Error de validación del backend (400 si `raices` vacías/no-lista,
      // 422 legado): el envelope `error` con `errors[]` se muestra tal cual.
      if (json.status === "error") {
        setError(json.errors?.[0] || "Error al buscar facturas");
        setEncontradas([]);
        setNoEncontradas([]);
        setSearched(false);
      } else {
        const data = json.data as BuscarData;
        setEncontradas(data.encontradas ?? []);
        setNoEncontradas(data.no_encontradas ?? []);
        setSelected((data.encontradas ?? []).map((e) => e.full_path));
        setSearched(true);
      }
    } catch {
      setError("Error de conexión con el servidor");
    } finally {
      setBuscando(false);
    }
  };

  const handleTrasladar = async (operation: "move" | "copy") => {
    if (selected.length === 0 || !destInput.trim() || operating) return;
    if (operation === "move") {
      const ok = window.confirm(
        `¿Mover ${selected.length} carpeta(s) a ${destInput.trim()}? Esta acción quita las carpetas de su ubicación actual.`,
      );
      if (!ok) return;
    }
    setOperating(operation);
    setError("");
    try {
      const res = await fetch("/traslado-facturas/trasladar", {
        method: "POST",
        headers: XHR_HEADERS,
        body: JSON.stringify({
          sources: selected,
          dest_dir: destInput.trim(),
          operation,
        }),
      });
      const json = await res.json();
      const done: string[] =
        json.data?.moved ?? json.data?.copied ?? [];
      const failed: Array<{ src: string; error: string }> = json.data?.failed ?? [];
      const verb = operation === "move" ? "movida(s)" : "copiada(s)";
      if (json.status === "success") {
        setToast(`${done.length} carpeta(s) ${verb} a destino.`);
      } else {
        setToast(
          `${done.length} ${verb}, ${failed.length} con error. ${json.errors?.[0] ?? ""}`.trim(),
        );
      }
      // Refresca la búsqueda tras éxito para reflejar las nuevas rutas.
      if (done.length > 0) await handleBuscarRefresca();
    } catch {
      setError("Error de conexión con el servidor");
    } finally {
      setOperating(null);
    }
  };

  const handleBuscarRefresca = async () => {
    try {
      const res = await fetch("/traslado-facturas/buscar", {
        method: "POST",
        headers: XHR_HEADERS,
        body: JSON.stringify({ raices: effectiveRoots, codigos }),
      });
      const json = await res.json();
      // Idem validación 400/422: refresco silencioso, solo aplica en éxito.
      if (json.status === "success") {
        const data = json.data as BuscarData;
        setEncontradas(data.encontradas ?? []);
        setNoEncontradas(data.no_encontradas ?? []);
        setSelected((data.encontradas ?? []).map((e) => e.full_path));
      }
    } catch {
      // Silently fail — el toast ya informó el traslado.
    }
  };

  const allSelected = encontradas.length > 0 && selected.length === encontradas.length;
  const destValid = isValidDest(destInput);
  const showDestino = can_write && encontradas.length > 0;
  const segments = explorar?.actual ? splitSegments(explorar.actual) : [];

  return (
    <div className="mx-auto max-w-6xl">
      <Breadcrumbs items={[{ label: "Traslado de Facturas" }]} />
      <PageTitle
        eyebrow="EPS MALLAMAS"
        title="Traslado de Facturas"
        description="Pegá una cadena de códigos, buscá sus carpetas en el servidor y movelas o copialas a la carpeta destino."
      />

      {/* Card Raíces */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <h2 className="font-display font-semibold text-foreground mb-1">Raíces de búsqueda</h2>
        <p className="text-xs text-muted-foreground mb-4">
          Carpetas raíz configuradas en Monitoreo. La búsqueda solo revisa las seleccionadas.
          Las rutas manuales solo viven en esta sesión y no se guardan en el config de monitoreo.
        </p>
        {roots.length === 0 ? (
          <p className="text-xs text-warning-foreground flex items-center gap-1">
            <AlertCircle className="h-3 w-3" />
            Sin raíces configuradas. Configuralas en Monitoreo de Carpetas antes de buscar.
          </p>
        ) : (
          <div className="space-y-1.5">
            {roots.map((root) => (
              <label key={root} className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedRoots.includes(root)}
                  onChange={() => toggleRoot(root)}
                />
                <span className="font-mono text-foreground/80">{root}</span>
              </label>
            ))}
          </div>
        )}
        {manualRoots.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {manualRoots.map((root) => (
              <span
                key={root}
                className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-2.5 py-1 font-mono text-[11px] text-foreground/80"
              >
                {root}
                <button
                  type="button"
                  onClick={() => handleRemoveManual(root)}
                  className="text-muted-foreground hover:text-destructive"
                  aria-label={`Quitar ${root}`}
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="mt-3">
          <div className="flex gap-2">
            <Input
              value={manualInput}
              onChange={(e) => {
                setManualInput(e.target.value);
                if (manualError) setManualError("");
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddManual();
                }
              }}
              placeholder="\\\\servidor\\ruta"
              className="flex-1 font-mono text-xs"
            />
            <Button variant="outline" size="sm" onClick={handleAddManual}>
              Agregar ruta manual
            </Button>
          </div>
          {manualError ? (
            <p className="text-[11px] text-danger mt-1">{manualError}</p>
          ) : manualInput.trim() && !isValidDest(manualInput) ? (
            <p className="text-[11px] text-warning-foreground mt-1">
              Parece ruta parcial — usá la ruta completa UNC, ej. \\\\192.168.0.127\\facturacion\\facturacion.
            </p>
          ) : null}
        </div>
      </Card>

      {/* Card Códigos */}
      <Card className="p-6 border-border bg-card shadow-none mb-6">
        <h2 className="font-display font-semibold text-foreground mb-1">Códigos a buscar</h2>
        <p className="text-xs text-muted-foreground mb-4">
          Pegá la cadena con códigos separados por comas, espacios o saltos de línea.
        </p>
        <textarea
          value={codigos}
          onChange={(e) => setCodigos(e.target.value)}
          placeholder="FEV123, CAP456, ..."
          rows={4}
          className="w-full rounded-lg border border-border bg-card px-3 py-2 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        {error && (
          <div className="mt-3 rounded-md border border-danger/30 bg-danger/5 p-3">
            <p className="text-xs font-medium text-danger">{error}</p>
          </div>
        )}
        <div className="mt-4 flex justify-end">
          <Button
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
            disabled={buscando || !codigos.trim()}
            onClick={handleBuscar}
          >
            <Search className="h-4 w-4" />
            {buscando ? "Buscando…" : "Buscar"}
          </Button>
        </div>
      </Card>

      {/* Resultados */}
      {searched && (
        <>
          <Card className="p-6 border-border bg-card shadow-none mb-6">
            <details>
              <summary className="flex items-center gap-2 cursor-pointer pb-3 border-b border-border list-none">
                <CheckCircle2 className="h-5 w-5 text-success" />
                <h3 className="font-display font-semibold text-foreground text-sm">
                  Encontradas
                  <span className="text-muted-foreground ml-1">({encontradas.length})</span>
                </h3>
              </summary>
              {encontradas.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2 pt-3">
                  Ningún código pegado tiene carpeta en las raíces seleccionadas.
                </p>
              ) : (
                <div className="overflow-x-auto pt-3">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border">
                        {can_write && (
                          <th className="pb-2 pr-3">
                            <input
                              type="checkbox"
                              checked={allSelected}
                              onChange={toggleAll}
                              aria-label="Seleccionar todas"
                            />
                          </th>
                        )}
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Código</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Facturador</th>
                        <th className="text-left font-semibold text-foreground pb-2 pr-3">Ruta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {encontradas.map((e) => (
                        <tr key={e.full_path} className="border-b border-border/50 last:border-0">
                          {can_write && (
                            <td className="py-1.5 pr-3">
                              <input
                                type="checkbox"
                                checked={selected.includes(e.full_path)}
                                onChange={() => togglePath(e.full_path)}
                                aria-label={`Seleccionar ${e.codigo}`}
                              />
                            </td>
                          )}
                          <td className="py-1.5 pr-3 text-foreground/90 font-medium">{e.codigo}</td>
                          <td className="py-1.5 pr-3 text-foreground/80">{e.facturador}</td>
                          <td className="py-1.5 pr-3 text-foreground/60 font-mono max-w-[320px] truncate" title={e.full_path}>
                            {e.full_path}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </details>
          </Card>

          <Card className="p-6 border-border bg-card shadow-none mb-6">
            <details>
              <summary className="flex items-center gap-2 cursor-pointer pb-3 border-b border-border list-none">
                <AlertCircle className="h-5 w-5 text-warning-foreground" />
                <h3 className="font-display font-semibold text-foreground text-sm">
                  No encontradas
                  <span className="text-muted-foreground ml-1">({noEncontradas.length})</span>
                </h3>
              </summary>
              {noEncontradas.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2 pt-3">
                  Todos los códigos tienen carpeta.
                </p>
              ) : (
                <ul className="space-y-1 pt-3">
                  {noEncontradas.map((c) => (
                    <li key={c} className="text-xs font-mono text-foreground/80">
                      {c}
                    </li>
                  ))}
                </ul>
              )}
            </details>
          </Card>
        </>
      )}

      {/* Card Destino */}
      {showDestino ? (
        <Card className="p-6 border-border bg-card shadow-none mb-6">
          <h2 className="font-display font-semibold text-foreground mb-1">Carpeta destino</h2>
          <p className="text-xs text-muted-foreground mb-4">
            Explorá el servidor o pegá la ruta UNC completa. {selected.length} carpeta(s) seleccionada(s).
          </p>

          {explorar?.actual && (
            <nav className="flex flex-wrap items-center gap-1 text-xs mb-3" aria-label="Ruta actual">
              {segments.map((seg, i) => (
                <span key={seg.path} className="flex items-center gap-1">
                  {i > 0 && <span className="text-muted-foreground">/</span>}
                  <button
                    type="button"
                    className="font-mono text-primary hover:underline"
                    onClick={() => void fetchExplorar(seg.path)}
                  >
                    {seg.label}
                  </button>
                </span>
              ))}
            </nav>
          )}

          {exploring ? (
            <p className="text-xs text-muted-foreground py-2">Explorando…</p>
          ) : (
            <div className="rounded-lg border border-border/50 divide-y divide-border/50 mb-4">
              {explorar?.padre && (
                <button
                  type="button"
                  onClick={() => void fetchExplorar(explorar.padre ?? undefined)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-xs text-muted-foreground hover:bg-muted/40"
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                  Subir al padre
                </button>
              )}
              {(explorar?.dirs ?? []).map((d) => (
                <button
                  key={d.path}
                  type="button"
                  onClick={() => void fetchExplorar(d.path)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-xs text-foreground/80 hover:bg-muted/40"
                >
                  <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="font-mono truncate" title={d.path}>{d.name}</span>
                </button>
              ))}
              {explorar && explorar.dirs.length === 0 && (
                <p className="px-3 py-2 text-xs text-muted-foreground">Sin subcarpetas.</p>
              )}
            </div>
          )}

          <div>
            <Input
              value={destInput}
              onChange={(e) => setDestInput(e.target.value)}
              placeholder="\\\\servidor\\ruta\\destino"
              className="w-full font-mono text-xs"
            />
            {destInput.trim() && !destValid && (
              <p className="text-[11px] text-warning-foreground mt-1">
                Parece ruta parcial — usá la ruta completa UNC, ej. \\\\servidor\\carpeta\\destino.
              </p>
            )}
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <Button
              variant="outline"
              disabled={operating !== null || selected.length === 0 || !destValid}
              onClick={() => void handleTrasladar("copy")}
            >
              <Copy className="h-4 w-4" />
              {operating === "copy" ? "Copiando…" : `Copiar (${selected.length})`}
            </Button>
            <Button
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
              disabled={operating !== null || selected.length === 0 || !destValid}
              onClick={() => void handleTrasladar("move")}
            >
              <FolderInput className="h-4 w-4" />
              {operating === "move" ? "Moviendo…" : `Mover (${selected.length})`}
            </Button>
          </div>
        </Card>
      ) : (
        searched && encontradas.length > 0 && !can_write && (
          <Card className="p-4 border-border bg-card shadow-none mb-6">
            <p className="text-xs text-muted-foreground">
              Solo lectura: podés buscar y ver resultados, pero trasladar carpetas requiere permiso de escritura.
            </p>
          </Card>
        )
      )}

      {toast && <Toast message={toast} onDone={() => setToast("")} />}
    </div>
  );
}
