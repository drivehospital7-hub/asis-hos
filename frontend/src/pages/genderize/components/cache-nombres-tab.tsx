import { useState } from "react";
import { AlertTriangle, Search, X } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCacheNombres } from "@/hooks/useCacheNombres";

interface Props {
  className?: string;
}

const GENDER_OPTIONS = ["All", "F", "M", "L", "U"] as const;
const EDIT_GENDERS = ["F", "M", "L", "U"] as const;

function genderBadgeVariant(short: string): "default" | "secondary" | "outline" | "destructive" {
  if (short === "F") return "default";
  if (short === "M") return "secondary";
  if (short === "L") return "outline";
  return "outline";
}

function longLabel(gender: string): string {
  const map: Record<string, string> = {
    female: "female",
    male: "male",
    lastname: "lastname",
    undefined: "undefined",
    F: "female",
    M: "male",
    L: "lastname",
    U: "undefined",
  };
  return map[gender] ?? gender;
}

export function CacheNombresTab({ className }: Props) {
  const { search, setSearch, gender, setGender, page, setPage, pageSize, setPageSize, items, total, alerts, loading, error, refetch } =
    useCacheNombres();

  const [edits, setEdits] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const showBanner =
    alerts !== null && (alerts.total_collisions > 0 || alerts.invalid_genders.length > 0 || alerts.cleaned_keys.length > 0);

  const handleSave = async (nombre: string) => {
    const newGender = edits[nombre];
    if (!newGender) return;
    setSaving(nombre);
    setSaveError(null);
    try {
      const res = await fetch("/api/import/cache-corregir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre_normalizado: nombre, genero: newGender }),
      });
      const data = await res.json();
      if (data.status === "success") {
        refetch();
      } else {
        setSaveError(data.errors?.join(", ") ?? "Error al guardar");
      }
    } catch (err) {
      setSaveError("Error de conexión: " + (err as Error).message);
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className={className}>
      {showBanner && alerts && (
        <Alert className="mb-4 border-warning/40 bg-warning/10">
          <AlertTriangle className="h-4 w-4 text-warning" />
          <AlertTitle className="text-warning-foreground">Alertas de cache</AlertTitle>
          <AlertDescription className="text-sm text-warning-foreground/90">
            {alerts.total_collisions} colisiones ({alerts.collisions.filter((c) => c.same_value).length} same_value /{" "}
            {alerts.collisions.filter((c) => !c.same_value).length} different_value)
            {alerts.cleaned_keys.length > 0 && ` — ${alerts.cleaned_keys.length} claves limpiadas (BOM/ZW)`}
            {alerts.invalid_genders.length > 0 && ` — ${alerts.invalid_genders.length} géneros inválidos`}
            {alerts.recovered_nulls > 0 && ` — ${alerts.recovered_nulls} nulls recuperados`}
          </AlertDescription>
        </Alert>
      )}

      <Card className="p-4 border shadow-none mb-4" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar nombre..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="w-[160px]">
            <Select value={gender} onValueChange={setGender}>
              <SelectTrigger>
                <SelectValue placeholder="Género" />
              </SelectTrigger>
              <SelectContent>
                {GENDER_OPTIONS.map((opt) => (
                  <SelectItem key={opt} value={opt}>
                    {opt === "All" ? "All" : `${opt} — ${longLabel(opt)}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {(search || gender !== "All") && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearch("");
                setGender("All");
              }}
              className="gap-1"
            >
              <X className="h-4 w-4" />
              Limpiar
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {total} resultado{total !== 1 ? "s" : ""} — página {page} / {totalPages}
        </p>
      </Card>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {saveError && (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Error al guardar</AlertTitle>
          <AlertDescription>{saveError}</AlertDescription>
        </Alert>
      )}

      <Card className="border shadow-none overflow-hidden" style={{ borderColor: "oklch(0.55 0.04 160 / 0.1)", background: "white" }}>
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead>Nombre</TableHead>
              <TableHead>Género</TableHead>
              <TableHead>Prob.</TableHead>
              <TableHead>Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <>
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                    Cargando...
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell colSpan={4}>
                    <div className="space-y-2 animate-pulse">
                      <div className="h-4 bg-muted rounded w-full" />
                      <div className="h-4 bg-muted rounded w-5/6" />
                      <div className="h-4 bg-muted rounded w-4/6" />
                    </div>
                  </TableCell>
                </TableRow>
              </>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                  Sin resultados
                </TableCell>
              </TableRow>
            ) : (
              items.map((it) => (
                <TableRow key={it.nombre_normalizado}>
                  <TableCell className="font-medium text-xs max-w-[180px] truncate" title={it.nombre_normalizado}>
                    {it.nombre_normalizado}
                  </TableCell>
                  <TableCell>
                    <Badge variant={genderBadgeVariant(it.gender_short)} className="gap-1">
                      {it.gender_short} — {longLabel(it.gender)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs tabular-nums">{it.probability ?? "—"}</TableCell>
                  <TableCell>
                    <div className="flex gap-1.5 items-center">
                      <div className="w-[96px]">
                        <Select
                          value={edits[it.nombre_normalizado] ?? it.gender_short}
                          onValueChange={(v) => setEdits((prev) => ({ ...prev, [it.nombre_normalizado]: v }))}
                        >
                          <SelectTrigger size="sm">
                            <SelectValue placeholder={it.gender_short} />
                          </SelectTrigger>
                          <SelectContent>
                            {EDIT_GENDERS.map((opt) => (
                              <SelectItem key={opt} value={opt}>
                                {opt}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={saving === it.nombre_normalizado}
                        onClick={() => handleSave(it.nombre_normalizado)}
                        className="h-7 text-xs px-2 shrink-0"
                      >
                        {saving === it.nombre_normalizado ? "Guardando..." : "Guardar"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-border">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>
              Anterior
            </Button>
            <span className="text-sm text-muted-foreground">
              Página {page} / {totalPages}
            </span>
            <Button variant="outline" size="sm" disabled={page >= totalPages || loading} onClick={() => setPage(page + 1)}>
              Siguiente
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Por página</span>
            <div className="w-[90px]">
              <Select
                value={String(pageSize)}
                onValueChange={(v) => {
                  setPageSize(Number(v));
                  setPage(1);
                }}
              >
                <SelectTrigger size="sm">
                  <SelectValue placeholder="50" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="25">25</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
