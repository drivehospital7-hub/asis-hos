import { useMemo, useState } from "react";
import { AlertTriangle, Plus, Trash2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface BulkAddResult {
  agregados: { nombre_normalizado: string; gender: string; gender_short: string }[];
  omitidos: { nombre_normalizado: string; gender: string; gender_short: string; motivo: string }[];
  errores: string[];
  total_procesados: number;
  total_agregados: number;
  total_omitidos: number;
}

interface ParsedItem {
  nombre: string;
  gender: string;
}

const VALID_GENDERS = ["F", "M", "L", "U"] as const;

function normalizeName(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function parseLocal(raw: string): { items: ParsedItem[]; invalidos: number } {
  const items: ParsedItem[] = [];
  let invalidos = 0;
  for (const block of raw.split(/[,;\n]+/)) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    const parts = trimmed.split(/\s+/);
    if (parts.length < 2) {
      invalidos += 1;
      continue;
    }
    const gender = parts[parts.length - 1].toUpperCase();
    if (!(VALID_GENDERS as readonly string[]).includes(gender)) {
      invalidos += 1;
      continue;
    }
    const nombre = normalizeName(parts.slice(0, -1).join(" "));
    if (!nombre) {
      invalidos += 1;
      continue;
    }
    items.push({ nombre, gender });
  }
  return { items, invalidos };
}

interface Props {
  className?: string;
}

export function BulkAddTab({ className }: Props) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<BulkAddResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const preview = useMemo(() => parseLocal(text), [text]);

  const handleSend = async () => {
    if (!text.trim() || sending) return;
    setSending(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/import/cache-bulk-add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (data.status === "success") {
        setResult(data.data as BulkAddResult);
      } else {
        setError(data.errors?.join(", ") ?? "Error al agregar nombres");
      }
    } catch (err) {
      setError("Error de conexión: " + (err as Error).message);
    } finally {
      setSending(false);
    }
  };

  const handleClear = () => {
    setText("");
    setResult(null);
    setError(null);
  };

  return (
    <div className={className}>
      <Card
        className="p-4 border shadow-none mb-4"
        style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}
      >
        <p className="text-xs text-muted-foreground mb-2">
          Formato: <span className="font-mono">nombre F/M/L/U</span> separados por coma, punto y coma o salto de
          línea. Ej: <span className="font-mono">maria F, jose M; garcia L</span>
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={"maria F, jose M\nangela F; garcia L"}
          rows={6}
          className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        />
        <div className="flex flex-wrap items-center gap-3 mt-3">
          <Button onClick={handleSend} disabled={!text.trim() || sending} className="gap-1.5">
            <Plus className="h-4 w-4" />
            {sending ? "Agregando..." : "Agregar nombres"}
          </Button>
          <Button variant="outline" onClick={handleClear} disabled={sending} className="gap-1.5">
            <Trash2 className="h-4 w-4" />
            Limpiar
          </Button>
          <p className="text-xs text-muted-foreground">
            {preview.items.length} válido{preview.items.length !== 1 ? "s" : ""}
            {preview.invalidos > 0 && ` — ${preview.invalidos} inválido${preview.invalidos !== 1 ? "s" : ""}`}
          </p>
        </div>
      </Card>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <Card
          className="p-4 border shadow-none"
          style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}
        >
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge variant="default">Agregados: {result.total_agregados}</Badge>
            <Badge variant="secondary">Omitidos: {result.total_omitidos}</Badge>
            {result.errores.length > 0 && <Badge variant="destructive">Errores: {result.errores.length}</Badge>}
          </div>

          {result.agregados.length > 0 && (
            <div className="mb-3">
              <p className="text-sm font-semibold mb-1">Agregados</p>
              <ul className="text-xs space-y-1 list-disc list-inside">
                {result.agregados.map((a) => (
                  <li key={a.nombre_normalizado} className="font-mono">
                    {a.nombre_normalizado} — {a.gender_short}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.omitidos.length > 0 && (
            <div className="mb-3">
              <p className="text-sm font-semibold mb-1">Omitidos</p>
              <ul className="text-xs space-y-1 list-disc list-inside">
                {result.omitidos.map((o) => (
                  <li key={o.nombre_normalizado} className="font-mono">
                    {o.nombre_normalizado} — {o.gender_short} ({o.motivo})
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.errores.length > 0 && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Bloques con error</AlertTitle>
              <AlertDescription>
                <ul className="space-y-1 list-disc list-inside">
                  {result.errores.map((e, i) => (
                    <li key={i} className="text-xs">
                      {e}
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}
        </Card>
      )}
    </div>
  );
}
