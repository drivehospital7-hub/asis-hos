import { useEffect, useMemo, useRef, useState } from "react";
import {
  FlaskConical,
  Search,
  ClipboardList,
  Settings2,
  Printer,
  FileSpreadsheet,
  Trash2,
  Pencil,
  Plus,
  Minus,
  Eye,
  RefreshCcw,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageTitle } from "@/components/page-title";
import {
  normalizeSearch,
  searchExamenes,
  migrateFlatToGrouped,
  listadoFechaInfo,
  buildPrefactura,
  normalizeItem,
  formatFechaEsCo,
  resolveUiActions,
  postArray,
  deletePrefactura,
  currentMonthRange,
  composeListadoView,
  paginate,
  listadoRowNumbers,
  daySectionTotals,
  badgeTooltip,
  LISTADO_PAGE_SIZES,
  DEFAULT_LISTADO_PAGE_SIZE,
  type Examen,
  type FlatExamen,
  type Prefactura,
  type PrefacturaItem,
  type FechaInfo,
  type DateRange,
} from "@/lib/examenes";
import { downloadBlob, filenameFromDisposition } from "@/lib/download";
import {
  buildPrefacturaDoc,
  printContenido,
  PREVIEW_STYLES,
} from "@/lib/print";

// ─── Module-level API helpers ───────────────────────────────────────────

async function fetchData<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const body = await res.json();
    return body.status === "success" ? (body.data as T) : null;
  } catch {
    return null;
  }
}

type TabId = "consulta" | "listado" | "admin";

interface FlagState {
  neps: boolean;
  mall: boolean;
  emss: boolean;
  nepsAuth: boolean;
  mallAuth: boolean;
  emssAuth: boolean;
}

const EMPTY_FLAGS: FlagState = {
  neps: false,
  mall: false,
  emss: false,
  nepsAuth: false,
  mallAuth: false,
  emssAuth: false,
};

const flagValue = (base: boolean, auth: boolean): string =>
  auth ? "AUTH" : base ? "X" : "";

interface ExamenesPageProps {
  can_write: boolean;
  current_facturador: string;
  default_examenes: Examen[];
}

export function ExamenesPage({
  can_write,
  current_facturador,
  default_examenes,
}: ExamenesPageProps) {
  // ─── Data ──────────────────────────────────────────────────────────
  const [examenes, setExamenes] = useState<Examen[]>([]);
  const [listado, setListado] = useState<Prefactura[]>([]);
  const ui = useMemo(() => resolveUiActions(can_write), [can_write]);

  // ─── UI shell ──────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<TabId>("consulta");
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<number | null>(null);
  const [preview, setPreview] = useState<{ title: string; html: string } | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 2800);
  };

  // R4-001: tras un conflicto de escritura, recargar el estado del servidor
  // para que la UI no siga mostrando una versión que no se persistió.
  const reloadData = async () => {
    const [catsData, listData] = await Promise.all([
      fetchData<{ examenes?: Examen[] }>("/api/examenes"),
      fetchData<{ listado?: Prefactura[] }>("/api/listado"),
    ]);
    if (catsData?.examenes) setExamenes(catsData.examenes);
    if (listData?.listado) setListado(listData.listado);
    setListadoStatus(listData === null ? "error" : "ready");
  };

  const handleConflict = async (what: string) => {
    window.alert(`${what} cambió en otro equipo. Se recargó el estado actual para evitar pérdidas.`);
    await reloadData();
  };

  const confirmDialog = (
    window as unknown as { __showConfirm?: (msg: string) => Promise<boolean> }
  ).__showConfirm;
  const askConfirm = (msg: string): Promise<boolean> =>
    confirmDialog ? confirmDialog(msg) : Promise.resolve(window.confirm(msg));

  // ─── Consulta state ────────────────────────────────────────────────
  const [pacNom, setPacNom] = useState("");
  const [pacCed, setPacCed] = useState("");
  const [fecha, setFecha] = useState(() => formatFechaEsCo(new Date()));
  const [searchQuery, setSearchQuery] = useState("");
  const [searchError, setSearchError] = useState(false);
  const [singleResult, setSingleResult] = useState<Examen | null>(null);
  const [multiResults, setMultiResults] = useState<Examen[]>([]);
  const [selectedMulti, setSelectedMulti] = useState<Set<string>>(new Set());
  const [cart, setCart] = useState<PrefacturaItem[]>([]);
  const [saving, setSaving] = useState(false);

  const pacNomRef = useRef<HTMLInputElement>(null);
  const pacCedRef = useRef<HTMLInputElement>(null);
  const fechaRef = useRef<HTMLInputElement>(null);
  const qRef = useRef<HTMLInputElement>(null);

  // ─── Listado state ─────────────────────────────────────────────────
  const [listadoStatus, setListadoStatus] = useState<"loading" | "ready" | "error">("loading");
  const [listadoQuery, setListadoQuery] = useState("");
  // D3: always-visible from/to range pre-filled with the current month on
  // load; clearing is explicit — the inputs never re-prefill themselves.
  const [range, setRange] = useState<DateRange>(() => currentMonthRange(new Date()));
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_LISTADO_PAGE_SIZE);
  const [editDraft, setEditDraft] = useState<Prefactura | null>(null);
  const [pickerIdx, setPickerIdx] = useState<number | null>(null);
  const [pickerQuery, setPickerQuery] = useState("");

  // ─── Admin state ───────────────────────────────────────────────────
  const [admSearch, setAdmSearch] = useState("");
  const [admCod, setAdmCod] = useState("");
  const [admNom, setAdmNom] = useState("");
  const [admFlags, setAdmFlags] = useState<FlagState>(EMPTY_FLAGS);
  const [admEditIdx, setAdmEditIdx] = useState(-1);

  // ─── Init (EX-18) ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      let cats: Examen[] = [];
      let list: Prefactura[] = [];
      const catsData = await fetchData<{ examenes?: Examen[] }>("/api/examenes");
      if (catsData?.examenes) cats = catsData.examenes;
      const listData = await fetchData<{ listado?: Prefactura[] }>("/api/listado");
      if (listData?.listado) list = listData.listado;
      if (cancelled) return;

      // Flat → grouped auto-migration with localStorage backup (EX-18)
      if (Array.isArray(list) && list.length && (list[0] as unknown as { cod?: string }).cod) {
        try {
          localStorage.setItem("listado_backup", JSON.stringify(list));
        } catch {
          /* storage unavailable — migration still proceeds */
        }
        const oldCount = list.length;
        const baseListado = list;
        const migrated = migrateFlatToGrouped(list as unknown as FlatExamen[]);
        list = migrated;
        const migResult = await postArray("/api/listado", migrated, baseListado);
        if (migResult === "conflict") {
          // reloadData ya refrescó examenes + listado desde el servidor
          await handleConflict("El listado");
          return;
        }
        showToast(`✓ Datos migrados: ${migrated.length} prefacturas creadas de ${oldCount} exámenes`);
      }
      setExamenes(cats);
      setListado(list);
      // EX-11: fetch failures are an ERROR state — never "No hay registros".
      setListadoStatus(listData === null ? "error" : "ready");
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Pipeline (EX-11/29/30/31/33): listado → range (D2: cleared → raw listado
  // incl. sin-fecha) → global search on the FULL listado (D1) → desc sort (D4).
  const sorted = useMemo(
    () =>
      composeListadoView(listado, {
        from: range.from || null,
        to: range.to || null,
        query: listadoQuery,
      }),
    [listado, range.from, range.to, listadoQuery],
  );

  // Continuous N° over the FULL displayed set — stable across pages (#1682).
  const rowNumbers = useMemo(() => listadoRowNumbers(sorted), [sorted]);

  const paged = useMemo(
    () => paginate(sorted, page, pageSize),
    [sorted, page, pageSize],
  );

  // Day sections regroup INSIDE the page slice; headers repeat across pages.
  const pageDaySections = useMemo(() => {
    const map = new Map<string, { info: FechaInfo; entries: Prefactura[] }>();
    for (const pf of paged.items) {
      const info = listadoFechaInfo(pf.hora);
      if (!map.has(info.dayKey)) map.set(info.dayKey, { info, entries: [] });
      map.get(info.dayKey)!.entries.push(pf);
    }
    return [...map.values()].sort((a, b) => b.info.sortKey - a.info.sortKey);
  }, [paged.items]);

  // EX-31: ANY range/search change resets page → 1 and size → 25.
  useEffect(() => {
    setPage(1);
    setPageSize(DEFAULT_LISTADO_PAGE_SIZE);
  }, [listadoQuery, range.from, range.to]);

  const fechaStr = new Date().toLocaleDateString("es-CO", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  // ─── Consulta: search (EX-6) ───────────────────────────────────────
  const buscar = () => {
    setSearchError(false);
    setSingleResult(null);
    setMultiResults([]);
    setSelectedMulti(new Set());
    const q = normalizeSearch(searchQuery);
    if (!q) {
      setSearchError(true);
      return;
    }
    const matches = searchExamenes(examenes, q);
    if (matches.length === 0) {
      setSearchError(true);
      return;
    }
    if (matches.length === 1) {
      setSingleResult(matches[0]);
      return;
    }
    setMultiResults(matches);
  };

  const toggleMulti = (cod: string) => {
    setSelectedMulti((prev) => {
      const next = new Set(prev);
      if (next.has(cod)) next.delete(cod);
      else next.add(cod);
      return next;
    });
  };

  const addToCart = (item: Examen) => {
    if (cart.some((c) => c.cod === item.cod)) {
      window.alert("Este examen ya está en la prefactura.");
      return;
    }
    setCart([...cart, { ...item, cantidad: 1 }]);
  };

  const addSelectedToCart = () => {
    const sel = multiResults.filter((e) => selectedMulti.has(e.cod));
    if (!sel.length) {
      window.alert("Seleccione al menos un examen.");
      return;
    }
    const next = [...cart];
    for (const e of sel) {
      if (!next.some((c) => c.cod === e.cod)) next.push({ ...e, cantidad: 1 });
    }
    setCart(next);
    setMultiResults([]);
    setSelectedMulti(new Set());
  };

  /** Stepper onChange clamp: 0/negativos/NaN → 1 (EX-22/EX-27). */
  const setCartQty = (idx: number, value: string) => {
    setCart((prev) =>
      prev.map((c, i) => (i === idx ? normalizeItem({ ...c, cantidad: Number(value) }) : c)),
    );
  };

  const addFirstVisible = () => {
    if (singleResult) {
      addToCart(singleResult);
      setSingleResult(null);
    } else if (multiResults.length > 0) {
      addToCart(multiResults[0]);
      setMultiResults([]);
      setSelectedMulti(new Set());
    }
    qRef.current?.focus();
  };

  const removeFromCart = (idx: number) => {
    setCart((prev) => prev.filter((_, i) => i !== idx));
  };

  const vaciarCart = async () => {
    if (!cart.length) return;
    if (!(await askConfirm("¿Vaciar toda la prefactura?"))) return;
    setCart([]);
  };

  // ─── Consulta: Enter navigation (EX-7) ─────────────────────────────
  const focusNextOnEnter = (nextRef: React.RefObject<HTMLInputElement | null>) => (
    e: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    nextRef.current?.focus();
  };

  const handleQKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== "Enter") return;
    if (singleResult || multiResults.length > 0) addFirstVisible();
    else buscar();
  };

  // ─── Consulta: save-to-listado (EX-10, write-gated) ────────────────
  const handleSavePrefactura = async () => {
    if (!cart.length) {
      window.alert("La prefactura está vacía.");
      return;
    }
    const snapshot = cart.slice();
    const pf = buildPrefactura({
      paciente: pacNom,
      cedula: pacCed,
      facturador: current_facturador,
      items: snapshot,
      now: new Date(),
    });
    // Print preview mirrors the source: blank fields show underscores;
    // facturador vacío (sin nombre ni username) se muestra como "—" (EX-10).
    const previewDoc = buildPrefacturaDoc(
      {
        ...pf,
        paciente: pacNom.trim() || "________________________________",
        cedula: pacCed.trim() || "________________________________",
        facturador: current_facturador.trim() || "—",
      },
      fecha || "___/___/____",
    );
    setSaving(true);
    const optimistic = [...listado, pf];
    setListado(optimistic);
    const result = await postArray("/api/listado", optimistic, listado);
    if (result !== "ok") {
      setListado(listado); // rollback on failure — cart NOT cleared
      setSaving(false);
      if (result === "conflict") {
        await handleConflict("El listado");
      } else {
        window.alert("No se pudo guardar el listado. Reintente.");
      }
      return;
    }
    setSaving(false);
    setCart([]);
    showToast(`✓ ${snapshot.length} examen(es) agregados al listado`);
    setPreview({ title: "Prefactura — Vista previa", html: previewDoc });
  };

  // ─── Listado: row actions ──────────────────────────────────────────
  // EX-2: whole-record delete goes through the write-gated DELETE endpoint
  // (never the read-gated full-array POST). base_hash del arreglo actual →
  // 409/404 = copia stale → recargar; otro error → rollback.
  const delReg = async (id: string) => {
    const pf = listado.find((p) => p.id === id);
    if (!pf) return;
    if (!(await askConfirm(`¿Eliminar toda la prefactura de ${pf.paciente}?`))) return;
    const next = listado.filter((p) => p.id !== id);
    setListado(next);
    const result = await deletePrefactura(id, listado);
    if (result === "conflict") {
      await handleConflict("El listado");
    } else if (result === "error") {
      setListado(listado); // rollback — la UI nunca queda sin el registro
      window.alert("No se pudo eliminar la prefactura. Reintente.");
    } else {
      showToast(`✓ Prefactura de ${pf.paciente} eliminada`);
    }
  };

  const verRegistro = (id: string) => {
    const pf = listado.find((p) => p.id === id);
    if (!pf) return;
    printContenido(buildPrefacturaDoc(pf, fechaStr));
  };

  // EX-14/EX-34: exporta el conjunto exhibido (rango | búsqueda global) a
  // .xlsx server-side. El server devuelve 400 con envelope cuando el filtro
  // queda vacío; acá se avisa antes para no gastar el round-trip.
  const exportarExcel = async () => {
    if (!sorted.length) {
      window.alert("No hay registros en el filtro seleccionado.");
      return;
    }
    const params = new URLSearchParams();
    if (range.from) params.set("from", range.from);
    if (range.to) params.set("to", range.to);
    if (listadoQuery.trim()) params.set("q", listadoQuery.trim());
    try {
      const res = await fetch(`/api/examenes/export?${params.toString()}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        window.alert(body?.errors?.[0] ?? "No se pudo exportar el listado.");
        return;
      }
      const blob = await res.blob();
      // D9: el nombre viene del Content-Disposition (fuente única de verdad).
      downloadBlob(
        blob,
        filenameFromDisposition(res.headers.get("Content-Disposition")) ??
          "Listado_Lab_HospitalOrito.xlsx",
      );
    } catch {
      window.alert("No se pudo exportar el listado. Reintente.");
    }
  };

  // ─── Listado: edit modal (EX-12, write-gated) ──────────────────────
  const openEdit = (pf: Prefactura) => {
    setEditDraft({ ...pf, items: pf.items.map((i) => ({ ...i })) });
    setPickerIdx(null);
    setPickerQuery("");
  };

  const saveEdit = async () => {
    if (!editDraft) return;
    if (!editDraft.paciente.trim() || !editDraft.cedula.trim()) {
      window.alert("Paciente y Cédula son obligatorios.");
      return;
    }
    // Rebuild items from catalog snapshot by code; fallback keeps name + empty
    // flags. cantidad se preserva del borrador (EX-12, #1651): el catálogo no
    // tiene cantidad y reconstruir sin copiarla la DROPEARÍA silenciosamente.
    const items = editDraft.items
      .filter((i) => i.cod || i.nom)
      .map((i) => {
        const exam = examenes.find((e) => e.cod === i.cod);
        return exam
          ? { cod: exam.cod, nom: exam.nom, neps: exam.neps || "", mall: exam.mall || "", emss: exam.emss || "", cantidad: normalizeItem(i).cantidad }
          : { cod: i.cod, nom: i.nom, neps: "", mall: "", emss: "", cantidad: normalizeItem(i).cantidad };
      });
    const next = listado.map((p) =>
      p.id === editDraft.id
        ? {
            ...editDraft,
            paciente: editDraft.paciente.trim(),
            cedula: editDraft.cedula.trim(),
            hora: editDraft.hora.trim() || p.hora,
            items,
          }
        : p,
    );
    setListado(next);
    setEditDraft(null);
    if ((await postArray("/api/listado", next, listado)) === "conflict") {
      await handleConflict("El listado");
    }
  };

  const editAddItem = () => {
    if (!editDraft) return;
    const idx = editDraft.items.length;
    setEditDraft({
      ...editDraft,
      items: [...editDraft.items, { cod: "", nom: "Nuevo procedimiento", neps: "", mall: "", emss: "", cantidad: 1 }],
    });
    setPickerIdx(idx);
    setPickerQuery("");
  };

  const editRemoveItem = (idx: number) => {
    if (!editDraft) return;
    if (!window.confirm("¿Eliminar este procedimiento?")) return;
    setEditDraft({ ...editDraft, items: editDraft.items.filter((_, i) => i !== idx) });
  };

  const editSelectItem = (idx: number, cod: string) => {
    if (!editDraft) return;
    const exam = examenes.find((e) => e.cod === cod);
    // cantidad se preserva del borrador (EX-12, #1651) — no del catálogo.
    const items = editDraft.items.map((it, i) =>
      i === idx
        ? exam
          ? { cod: exam.cod, nom: exam.nom, neps: exam.neps || "", mall: exam.mall || "", emss: exam.emss || "", cantidad: normalizeItem(it).cantidad }
          : { cod, nom: it.nom, neps: "", mall: "", emss: "", cantidad: normalizeItem(it).cantidad }
        : it,
    );
    setEditDraft({ ...editDraft, items });
    setPickerIdx(null);
    setPickerQuery("");
  };

  const pickerResults = useMemo(() => {
    const q = normalizeSearch(pickerQuery);
    return q
      ? examenes.filter((e) => e.cod.includes(q) || e.nom.toUpperCase().includes(q))
      : examenes;
  }, [examenes, pickerQuery]);

  // ─── Admin: CRUD (EX-16, write-gated) ──────────────────────────────
  const admVisible = useMemo(() => {
    const q = normalizeSearch(admSearch);
    return q
      ? examenes.filter((e) => e.cod.includes(q) || e.nom.toUpperCase().includes(q))
      : examenes;
  }, [examenes, admSearch]);

  const guardarExamen = async () => {
    const cod = admCod.trim();
    const nom = admNom.trim();
    if (!cod || !nom) {
      window.alert("Complete el código y el nombre del examen.");
      return;
    }
    const ex: Examen = {
      cod,
      nom,
      neps: flagValue(admFlags.neps, admFlags.nepsAuth),
      mall: flagValue(admFlags.mall, admFlags.mallAuth),
      emss: flagValue(admFlags.emss, admFlags.emssAuth),
    };
    const editing = admEditIdx >= 0;
    let next: Examen[];
    if (editing) {
      next = examenes.map((e, i) => (i === admEditIdx ? ex : e));
    } else {
      if (examenes.some((e) => e.cod === cod)) {
        window.alert("Ya existe un examen con ese código CUPS.");
        return;
      }
      next = [...examenes, ex];
    }
    setExamenes(next);
    cancelarEdicion();
    const result = await postArray("/api/examenes", next, examenes);
    if (result === "conflict") {
      await handleConflict("El catálogo de exámenes");
      return;
    }
    if (result === "error") {
      window.alert("No se pudo guardar el examen. Reintente.");
      return;
    }
    showToast(editing ? "✓ Examen actualizado correctamente" : "✓ Nuevo examen guardado correctamente");
  };

  const editarExamen = (ex: Examen, idx: number) => {
    setAdmCod(ex.cod);
    setAdmNom(ex.nom);
    setAdmFlags({
      neps: ex.neps === "X",
      mall: ex.mall === "X",
      emss: ex.emss === "X",
      nepsAuth: ex.neps === "AUTH",
      mallAuth: ex.mall === "AUTH",
      emssAuth: ex.emss === "AUTH",
    });
    setAdmEditIdx(idx);
  };

  const cancelarEdicion = () => {
    setAdmCod("");
    setAdmNom("");
    setAdmFlags(EMPTY_FLAGS);
    setAdmEditIdx(-1);
  };

  const eliminarExamen = async (cod: string) => {
    if (!(await askConfirm(`¿Eliminar el examen ${cod}? Esta acción no se puede deshacer.`))) return;
    const next = examenes.filter((e) => e.cod !== cod);
    setExamenes(next);
    if ((await postArray("/api/examenes", next, examenes)) === "conflict") {
      await handleConflict("El catálogo de exámenes");
    }
  };

  const restaurarDefaults = async () => {
    if (!(await askConfirm("¿Restaurar la base original? Se perderán los cambios que haya hecho."))) return;
    // DEFAULT_EXAMENES comes from the backend shell (66 entries) — never a
    // hardcoded client copy (task 4.4 / apply progress deviation 1).
    setExamenes(default_examenes);
    const result = await postArray("/api/examenes", default_examenes, examenes);
    if (result === "conflict") {
      await handleConflict("El catálogo de exámenes");
      return;
    }
    if (result === "error") {
      window.alert("No se pudo restaurar la base. Reintente.");
      return;
    }
    showToast(`✓ Base restaurada con ${default_examenes.length} exámenes originales`);
  };

  const setFlag = (key: keyof FlagState) => {
    setAdmFlags((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // ─── Render helpers ─────────────────────────────────────────────────
  const renderTags = (e: Examen) => {
    const tags: string[] = [];
    if (e.neps === "X") tags.push("NEPS");
    else if (e.neps === "AUTH") tags.push("NEPS ⚠ AUTH");
    if (e.mall === "X") tags.push("MALLAM");
    else if (e.mall === "AUTH") tags.push("MALLAM ⚠ AUTH");
    if (e.emss === "X") tags.push("EMSS");
    else if (e.emss === "AUTH") tags.push("EMSS ⚠ AUTH");
    if (!tags.length) return <span className="text-xs text-gray-400">Sin clasificación asignada</span>;
    return (
      <div className="flex flex-wrap gap-1">
        {tags.map((t) => (
          <span
            key={t}
            className="rounded-full border px-2 py-0.5 text-[10px] font-bold"
            style={
              t.includes("AUTH")
                ? { background: "#fdf0ee", color: "#a32d2d", borderColor: "#f5c6c0" }
                : { background: "#e0f0e8", color: "#1a6b47", borderColor: "#b5d4f4" }
            }
          >
            {t}
          </span>
        ))}
      </div>
    );
  };

  const TABS: Array<{ id: TabId; label: string; icon: typeof Search; visible: boolean }> = [
    { id: "consulta", label: "Consulta", icon: Search, visible: true },
    { id: "listado", label: "Listado", icon: ClipboardList, visible: true },
    { id: "admin", label: "Admin", icon: Settings2, visible: ui.admin },
  ];

  const tabs = TABS.filter((t) => t.visible);

  return (
    <div>
      <Breadcrumbs items={[{ label: "Exámenes" }]} />
      <PageTitle
        eyebrow="Laboratorio Clínico"
        title="Exámenes — Prefacturación"
        description="Consulta CUPS, prefactura y listado mensual del laboratorio."
      />

      {/* Tabs */}
      <div className="mb-5 flex gap-1 border-b">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 rounded-t-lg border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors ${
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "consulta" && (
        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="mb-3 font-heading text-sm font-semibold" style={{ color: "#1a4731" }}>
              Datos del Paciente
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Nombre completo
                </label>
                <input
                  ref={pacNomRef}
                  type="text"
                  value={pacNom}
                  onChange={(e) => setPacNom(e.target.value)}
                  onKeyDown={focusNextOnEnter(pacCedRef)}
                  placeholder="Ej: Juan Pérez García"
                  className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)" }}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Cédula / Documento
                </label>
                <input
                  ref={pacCedRef}
                  type="text"
                  value={pacCed}
                  onChange={(e) => setPacCed(e.target.value)}
                  onKeyDown={focusNextOnEnter(fechaRef)}
                  maxLength={20}
                  placeholder="Ej: 1075698452"
                  className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)" }}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Fecha
                </label>
                <input
                  ref={fechaRef}
                  type="text"
                  value={fecha}
                  onChange={(e) => setFecha(e.target.value)}
                  onKeyDown={focusNextOnEnter(qRef)}
                  placeholder="DD/MM/AAAA"
                  className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)" }}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Facturador(a)
                </label>
                <div
                  className="flex w-full items-center rounded-lg border bg-gray-50 px-3 py-2 text-sm font-semibold text-gray-700"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)" }}
                >
                  {current_facturador || "—"}
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 font-heading text-sm font-semibold" style={{ color: "#1a4731" }}>
              Buscar Examen
            </h2>
            <div className="flex gap-2">
              <input
                ref={qRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleQKeyDown}
                maxLength={80}
                placeholder='Ej: 903859 o "potasio"'
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)" }}
              />
              <Button onClick={buscar}>
                <Search className="h-4 w-4" />
                Buscar
              </Button>
            </div>
            <p className="mt-2 text-xs text-gray-400">
              Escriba código CUPS o parte del nombre y presione Enter o clic en Buscar.
            </p>
            {searchError && (
              <p
                role="alert"
                className="mt-3 rounded-md border px-3 py-2 text-xs font-medium"
                style={{ background: "#fdf0ee", borderColor: "#f5c6c0", color: "#c0392b" }}
              >
                ⚠ Código o nombre no encontrado. Verifique e intente de nuevo.
              </p>
            )}

            {singleResult && (
              <div className="mt-4 rounded-lg border p-4" style={{ background: "#f7faf8", borderColor: "#c8ddd4" }}>
                <span
                  className="mb-2 inline-block rounded-full px-3 py-0.5 text-[10px] font-bold"
                  style={{ background: "#e0f0e8", color: "#1a6b47" }}
                >
                  {singleResult.cod}
                </span>
                <p className="mb-2 text-sm font-bold text-gray-900">{singleResult.nom}</p>
                {renderTags(singleResult)}
                <Button size="sm" className="mt-3" variant="secondary" onClick={() => addToCart(singleResult)}>
                  <Plus className="h-4 w-4" />
                  Agregar a prefactura
                </Button>
              </div>
            )}

            {multiResults.length > 0 && (
              <div className="mt-4">
                <p className="mb-2 text-xs font-bold text-gray-500">
                  {multiResults.length} exámenes encontrados — seleccione uno o varios:
                </p>
                <div className="space-y-1.5">
                  {multiResults.map((e) => (
                    <button
                      key={e.cod}
                      onClick={() => toggleMulti(e.cod)}
                      className={`block w-full rounded-lg border p-3 text-left transition-colors ${
                        selectedMulti.has(e.cod) ? "border-primary" : "hover:border-primary"
                      }`}
                      style={selectedMulti.has(e.cod) ? { background: "#e8f5ee" } : { background: "white" }}
                    >
                      <span className="text-xs font-bold" style={{ color: "#1a6b47" }}>
                        {e.cod}
                      </span>
                      {selectedMulti.has(e.cod) && (
                        <span className="ml-2 rounded-full px-2 py-0.5 text-[9px] font-bold text-white" style={{ background: "#1a4731" }}>
                          ✓ SEL
                        </span>
                      )}
                      <p className="mt-1 text-xs font-bold text-gray-900">{e.nom}</p>
                      {renderTags(e)}
                    </button>
                  ))}
                </div>
                <Button size="sm" variant="secondary" className="mt-3" onClick={addSelectedToCart}>
                  <Plus className="h-4 w-4" />
                  Agregar seleccionados a prefactura
                </Button>
              </div>
            )}
          </Card>

          {cart.length > 0 && (
            <Card className="p-5" style={{ borderColor: "#9fd4b8", background: "#e8f5ee" }}>
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-bold" style={{ color: "#1a4731" }}>
                  Prefactura — {cart.length} examen(s)
                </span>
                {ui.clear && (
                  <Button size="sm" variant="destructive" onClick={vaciarCart}>
                    <Trash2 className="h-3.5 w-3.5" />
                    Vaciar
                  </Button>
                )}
              </div>
              <div className="space-y-1.5">
                {cart.map((e, i) => {
                  const q = normalizeItem(e).cantidad;
                  return (
                    <div key={`${e.cod}-${i}`} className="flex items-start justify-between gap-2 rounded-md border bg-white p-2.5" style={{ borderColor: "#c5ddd0" }}>
                      <div className="min-w-0">
                        <div className="text-[10px] font-bold" style={{ color: "#1a6b47" }}>{e.cod}</div>
                        <div className="text-xs font-semibold text-gray-900">{e.nom}</div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        <button
                          onClick={() => setCartQty(i, String(q - 1))}
                          title="Disminuir cantidad"
                          className="rounded border p-1 leading-none"
                          style={{ borderColor: "#c5ddd0", color: "#1a6b47" }}
                        >
                          <Minus className="h-3 w-3" />
                        </button>
                        <input
                          type="number"
                          min={1}
                          step={1}
                          value={q}
                          onChange={(e) => setCartQty(i, e.target.value)}
                          title="Cantidad"
                          className="w-12 rounded border px-1 py-0.5 text-center text-xs outline-none"
                          style={{ borderColor: "#c5ddd0" }}
                        />
                        <button
                          onClick={() => setCartQty(i, String(q + 1))}
                          title="Aumentar cantidad"
                          className="rounded border p-1 leading-none"
                          style={{ borderColor: "#c5ddd0", color: "#1a6b47" }}
                        >
                          <Plus className="h-3 w-3" />
                        </button>
                        <button
                          onClick={() => removeFromCart(i)}
                          title="Quitar"
                          className="p-1 text-base leading-none"
                          style={{ color: "#c0392b" }}
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
              {ui.save && (
                <Button className="mt-3 w-full" disabled={saving} onClick={handleSavePrefactura}>
                  <Eye className="h-4 w-4" />
                  {saving ? "Guardando…" : "Imprimir y Enlistar"}
                </Button>
              )}
            </Card>
          )}

          <p className="text-center text-[10px] text-gray-400">
            Base de datos: <strong>{examenes.length}</strong> exámenes
          </p>
        </div>
      )}

      {activeTab === "listado" && (
        <div>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-heading text-sm font-semibold" style={{ color: "#1a4731" }}>
                Listado Mensual de Prefacturas
              </h2>
              <span className="text-[10px]" style={{ color: "#888" }}>
                Fecha: {fechaStr}
              </span>
            </div>
            {/* EX-17: Exportar Excel ABOVE the filters toolbar, right-aligned (D8). */}
            <div className="flex items-center gap-2">
              <span className="rounded-full px-3 py-1 text-xs font-bold text-white" style={{ background: "#1a4731" }}>
                {sorted.length} registro{sorted.length !== 1 ? "s" : ""}
              </span>
              <Button size="sm" variant="secondary" onClick={exportarExcel}>
                <FileSpreadsheet className="h-3.5 w-3.5" />
                Exportar Excel
              </Button>
            </div>
          </div>

          {/* Toolbar: search (EX-29, global — ignores the range) + always-visible from/to range (EX-30) */}
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={listadoQuery}
                onChange={(e) => setListadoQuery(e.target.value)}
                placeholder="Buscar por paciente, cédula, facturador o examen…"
                maxLength={80}
                className="w-64 rounded-md border py-1.5 pl-8 pr-2 text-xs outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)", background: "#f7faf8" }}
              />
            </div>
            <label className="flex items-center gap-1 text-[10px] font-bold text-gray-500">
              Desde:
              <input
                type="date"
                value={range.from}
                onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))}
                className="rounded-md border px-2 py-1.5 text-xs outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)", background: "#f7faf8" }}
              />
            </label>
            <label className="flex items-center gap-1 text-[10px] font-bold text-gray-500">
              Hasta:
              <input
                type="date"
                value={range.to}
                onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))}
                className="rounded-md border px-2 py-1.5 text-xs outline-none focus:border-primary"
                style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)", background: "#f7faf8" }}
              />
            </label>
          </div>

          {listadoStatus === "loading" ? (
            <Card className="p-10 text-center text-xs text-gray-400">
              <FlaskConical className="mx-auto mb-2 h-8 w-8 animate-pulse opacity-40" />
              Cargando listado…
            </Card>
          ) : listadoStatus === "error" ? (
            <Card className="p-10 text-center text-xs" style={{ background: "#fdf0ee", borderColor: "#f5c6c0", color: "#a32d2d" }}>
              <FlaskConical className="mx-auto mb-2 h-8 w-8 opacity-40" />
              No se pudo cargar el listado. Verifique la conexión e intente de nuevo.
            </Card>
          ) : listado.length === 0 ? (
            <Card className="p-10 text-center text-xs text-gray-400">
              <FlaskConical className="mx-auto mb-2 h-8 w-8 opacity-40" />
              <>No hay registros. Busque exámenes y use <strong>"Imprimir y Enlistar"</strong> para agregarlos al listado.</>
            </Card>
          ) : sorted.length === 0 ? (
            <Card className="p-10 text-center text-xs text-gray-400">
              <FlaskConical className="mx-auto mb-2 h-8 w-8 opacity-40" />
              {listadoQuery.trim() ? (
                <>Sin resultados para «{listadoQuery.trim()}». Ajuste la búsqueda.</>
              ) : (
                <>No hay registros en el periodo seleccionado. Ajuste el rango de fechas o agregue registros desde la Consulta.</>
              )}
            </Card>
          ) : (
            <>
              {/* D5: no internal scroll wrapper — the page flows naturally;
                  pagination caps rows; thead not sticky. Keep the horizontal
                  scroll container for narrow viewports. */}
              <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-[#1a4731] text-left text-[10px] text-white">
                      <th className="px-2 py-2 font-semibold">#</th>
                      <th className="px-2 py-2 font-semibold">Paciente</th>
                      <th className="px-2 py-2 font-semibold">Cédula</th>
                      <th className="px-2 py-2 font-semibold">Facturador</th>
                      <th className="px-2 py-2 font-semibold">Fec/Hora</th>
                      <th className="px-2 py-2 text-center font-semibold">Items</th>
                      <th className="px-2 py-2 font-semibold">Acc</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageDaySections.map((day) => (
                      <DaySectionRows
                        key={day.info.dayKey}
                        day={day}
                        rowNumbers={rowNumbers}
                        ui={ui}
                        onPrint={verRegistro}
                        onEdit={openEdit}
                        onDelete={delReg}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pager + page-size (EX-31) */}
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <label className="flex items-center gap-2 text-[10px] font-bold text-gray-500">
                  Registros por página:
                  <select
                    value={pageSize}
                    onChange={(e) => setPageSize(Number(e.target.value))}
                    className="rounded-md border px-2 py-1.5 text-xs outline-none focus:border-primary"
                    style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)", background: "#f7faf8" }}
                  >
                    {LISTADO_PAGE_SIZES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={paged.page <= 1}
                    onClick={() => setPage(paged.page - 1)}
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    Anterior
                  </Button>
                  <span className="text-[10px] font-bold text-gray-500">
                    Página {paged.page} de {paged.totalPages}
                  </span>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={paged.page >= paged.totalPages}
                    onClick={() => setPage(paged.page + 1)}
                  >
                    Siguiente
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "admin" && ui.admin && (
        <div className="space-y-5">
          <Card className="p-5">
            <h2 className="mb-3 font-heading text-sm font-semibold" style={{ color: "#1a4731" }}>
              Agregar / Editar Examen
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Código CUPS
                </label>
                <input
                  type="text"
                  value={admCod}
                  onChange={(e) => setAdmCod(e.target.value)}
                  maxLength={10}
                  placeholder="Ej: 903859"
                  className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)" }}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Nombre del examen
                </label>
                <input
                  type="text"
                  value={admNom}
                  onChange={(e) => setAdmNom(e.target.value)}
                  placeholder="Nombre completo del examen"
                  className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary"
                  style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)" }}
                />
              </div>
            </div>
            <p className="mt-3 text-[10px] font-bold uppercase tracking-wide text-gray-500">Aplica en:</p>
            <div className="mt-1.5 flex flex-wrap gap-4">
              {(
                [
                  ["neps", "NEPS"],
                  ["mall", "MALLAM"],
                  ["emss", "EMSS"],
                ] as Array<[keyof FlagState, string]>
              ).map(([key, label]) => (
                <div key={key} className="flex items-center gap-1.5 text-xs text-gray-600">
                  <input
                    type="checkbox"
                    checked={admFlags[key]}
                    onChange={() => setFlag(key)}
                    className="accent-[#1a4731]"
                  />
                  {label}
                  <input
                    type="checkbox"
                    checked={admFlags[`${key}Auth` as keyof FlagState]}
                    onChange={() => setFlag(`${key}Auth` as keyof FlagState)}
                    title={`${label} AUTH`}
                    className="accent-[#1a4731]"
                  />
                  <span className="text-[10px] text-gray-400">AUTH</span>
                </div>
              ))}
            </div>
            <div className="mt-3 flex gap-2">
              <Button onClick={guardarExamen}>
                <FlaskConical className="h-4 w-4" />
                Guardar examen
              </Button>
              {admEditIdx >= 0 && (
                <Button variant="secondary" onClick={cancelarEdicion}>
                  <X className="h-4 w-4" />
                  Cancelar edición
                </Button>
              )}
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 font-heading text-sm font-semibold" style={{ color: "#1a4731" }}>
              Base de Exámenes ({examenes.length})
            </h2>
            <input
              type="text"
              value={admSearch}
              onChange={(e) => setAdmSearch(e.target.value)}
              placeholder="Buscar examen por código o nombre..."
              className="mb-3 w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary"
              style={{ borderColor: "oklch(0.55 0.04 160 / 0.25)", background: "#f7faf8" }}
            />
            {admVisible.length === 0 ? (
              <p className="py-3 text-xs text-gray-400">No se encontraron exámenes.</p>
            ) : (
              <div className="divide-y">
                {admVisible.map((e, i) => {
                  const realIdx = examenes.findIndex((x) => x.cod === e.cod);
                  return (
                    <div key={e.cod} className="flex items-center gap-2 py-2">
                      <span className="w-16 shrink-0 text-[10px] font-bold" style={{ color: "#1a4731" }}>
                        {e.cod}
                      </span>
                      <span className="flex-1 text-xs text-gray-800">{e.nom}</span>
                      <div className="flex shrink-0 gap-1 text-[9px] font-bold">
                        {e.neps && (
                          <span className="rounded px-1.5 py-0.5" style={{ background: "#e6f1fb", color: "#0c447c" }}>
                            {e.neps === "AUTH" ? "N⚠" : "N"}
                          </span>
                        )}
                        {e.mall && (
                          <span className="rounded px-1.5 py-0.5" style={{ background: "#eaf3de", color: "#27500a" }}>
                            {e.mall === "AUTH" ? "M⚠" : "M"}
                          </span>
                        )}
                        {e.emss && (
                          <span className="rounded px-1.5 py-0.5" style={{ background: "#faeeda", color: "#633806" }}>
                            {e.emss === "AUTH" ? "E⚠" : "E"}
                          </span>
                        )}
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <Button size="sm" variant="secondary" onClick={() => editarExamen(e, realIdx)} title="Editar">
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => eliminarExamen(e.cod)} title="Eliminar">
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                      <span className="sr-only">{i}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="mb-1 font-heading text-sm font-semibold" style={{ color: "#1a4731" }}>
              Restaurar base de datos original
            </h2>
            <p className="mb-3 text-[11px] text-gray-500">
              Esto reemplaza todos los exámenes actuales con la lista original de {default_examenes.length} exámenes.
              Use solo si borró algo por error.
            </p>
            <Button size="sm" variant="destructive" onClick={restaurarDefaults}>
              <RefreshCcw className="h-3.5 w-3.5" />
              Restaurar base original
            </Button>
          </Card>
        </div>
      )}

      {/* Edit modal (EX-12) */}
      {editDraft && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setEditDraft(null);
          }}
        >
          <div className="w-full max-w-xl overflow-hidden rounded-xl bg-white shadow-2xl">
            <div className="flex items-center justify-between bg-[#1a4731] px-5 py-3 text-white">
              <span className="text-sm font-bold">Editar Prefactura</span>
              <button onClick={() => setEditDraft(null)} className="text-xl leading-none">
                ×
              </button>
            </div>
            <style dangerouslySetInnerHTML={{ __html: PREVIEW_STYLES }} />
            <div className="max-h-[70vh] overflow-y-auto bg-white p-5">
              <div className="pdoc">
                <div className="pdoc-hdr">
                  <h2>E.S.E. HOSPITAL ORITO</h2>
                  <p>Prefactura de Servicios de Laboratorio Clínico — Edición</p>
                </div>
                <div className="pdoc-body">
                  <div className="prow">
                    <span className="plbl">Fecha:</span>
                    <span className="pval">{fechaStr}</span>
                  </div>
                  <div className="psep"></div>
                  <div className="prow">
                    <span className="plbl">Paciente:</span>
                    <input
                      type="text"
                      value={editDraft.paciente}
                      onChange={(e) => setEditDraft({ ...editDraft, paciente: e.target.value })}
                      placeholder="Nombre del paciente"
                      className="flex-1 rounded border px-2 py-1 text-sm font-bold text-gray-900 outline-none"
                      style={{ borderColor: "#ccc" }}
                    />
                  </div>
                  <div className="prow">
                    <span className="plbl">Cédula / Doc.:</span>
                    <input
                      type="text"
                      value={editDraft.cedula}
                      onChange={(e) => setEditDraft({ ...editDraft, cedula: e.target.value })}
                      placeholder="Número de documento"
                      className="flex-1 rounded border px-2 py-1 text-sm font-bold text-gray-900 outline-none"
                      style={{ borderColor: "#ccc" }}
                    />
                  </div>
                  <div className="psep"></div>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-[11px] font-bold text-gray-500">PROCEDIMIENTOS</span>
                    <Button size="sm" variant="secondary" onClick={editAddItem}>
                      <Plus className="h-3.5 w-3.5" />
                      Añadir procedimiento
                    </Button>
                  </div>
                  <table className="ptbl">
                    <thead>
                      <tr>
                        <th style={{ width: 30 }}>#</th>
                        <th style={{ width: 80 }}>Código</th>
                        <th>Examen</th>
                        <th style={{ width: 60 }}>Cant</th>
                        <th style={{ width: 140 }}>Aplica en</th>
                        <th style={{ width: 30 }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {editDraft.items.map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ color: "#888", textAlign: "center" }}>{idx + 1}</td>
                          <td>
                            <span className="text-xs font-bold" style={{ color: "#1a4731" }}>
                              {item.cod}
                            </span>
                          </td>
                          <td>
                            <span className="text-xs">{item.nom}</span>
                            {pickerIdx === idx && (
                              <div className="mt-1 rounded-md border p-2" style={{ background: "#f7faf8", borderColor: "#c5d5cc" }}>
                                <input
                                  type="text"
                                  autoFocus
                                  value={pickerQuery}
                                  onChange={(e) => setPickerQuery(e.target.value)}
                                  placeholder="Buscar examen por código o nombre..."
                                  className="w-full rounded border px-2 py-1 text-xs outline-none"
                                  style={{ borderColor: "#c5d5cc" }}
                                />
                                <div className="mt-1 max-h-44 overflow-y-auto">
                                  {pickerResults.slice(0, 30).map((e) => (
                                    <button
                                      key={e.cod}
                                      onClick={() => editSelectItem(idx, e.cod)}
                                      className="flex w-full items-center gap-2 rounded border-b px-2 py-1.5 text-left text-xs hover:bg-[#e8f5ee]"
                                    >
                                      <span className="min-w-16 font-bold" style={{ color: "#1a4731" }}>
                                        {e.cod}
                                      </span>
                                      <span className="flex-1">{e.nom}</span>
                                    </button>
                                  ))}
                                  {pickerResults.length === 0 && (
                                    <p className="py-3 text-center text-xs text-gray-400">No se encontraron exámenes.</p>
                                  )}
                                </div>
                              </div>
                            )}
                          </td>
                          <td>
                            <input
                              type="number"
                              min={1}
                              step={1}
                              value={normalizeItem(item).cantidad}
                              onChange={(e) => {
                                const q = Number(e.target.value);
                                setEditDraft({
                                  ...editDraft,
                                  items: editDraft.items.map((it, i) =>
                                    i === idx ? normalizeItem({ ...it, cantidad: q }) : it,
                                  ),
                                });
                              }}
                              title="Cantidad"
                              className="w-14 rounded border px-1 py-0.5 text-center text-xs outline-none"
                              style={{ borderColor: "#ccc" }}
                            />
                          </td>
                          <td>
                            <div className="flex gap-1 text-[9px] font-bold">
                              {item.neps && (
                                <span className="rounded px-1" style={{ background: "#e6f1fb", color: "#0c447c" }}>
                                  {item.neps === "AUTH" ? "N⚠" : "N"}
                                </span>
                              )}
                              {item.mall && (
                                <span className="rounded px-1" style={{ background: "#eaf3de", color: "#27500a" }}>
                                  {item.mall === "AUTH" ? "M⚠" : "M"}
                                </span>
                              )}
                              {item.emss && (
                                <span className="rounded px-1" style={{ background: "#faeeda", color: "#633806" }}>
                                  {item.emss === "AUTH" ? "E⚠" : "E"}
                                </span>
                              )}
                            </div>
                          </td>
                          <td>
                            <div className="flex gap-1">
                              <button
                                onClick={() => {
                                  setPickerIdx(pickerIdx === idx ? null : idx);
                                  setPickerQuery("");
                                }}
                                title="Cambiar examen"
                                className="p-1 text-xs"
                                style={{ color: "#2c5282" }}
                              >
                                <RefreshCcw className="h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() => editRemoveItem(idx)}
                                title="Eliminar procedimiento"
                                className="p-1 text-xs"
                                style={{ color: "#c0392b" }}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="mt-4 flex items-center border-t pt-2">
                    <span className="plbl" style={{ width: "auto" }}>
                      Facturador(a):
                    </span>
                    <span className="ml-2 text-[11px] font-bold">{editDraft.facturador}</span>
                  </div>
                  <div className="mt-2 flex items-center">
                    <span className="text-[10px] text-gray-400">
                      Hora:{" "}
                      <input
                        type="text"
                        value={editDraft.hora}
                        onChange={(e) => setEditDraft({ ...editDraft, hora: e.target.value })}
                        className="w-28 rounded border px-1.5 py-0.5 text-[10px] outline-none"
                        style={{ borderColor: "#ccc" }}
                      />
                    </span>
                    <span className="ml-auto text-[10px] text-gray-400">Laboratorio Clínico — E.S.E. Hospital Orito</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t bg-gray-50 px-5 py-3">
              <Button variant="secondary" onClick={() => setEditDraft(null)}>
                Cancelar
              </Button>
              <Button onClick={saveEdit}>Guardar cambios</Button>
            </div>
          </div>
        </div>
      )}

      {/* Preview modal (EX-13) */}
      {preview && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setPreview(null);
          }}
        >
          <div className="w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-2xl">
            <div className="flex items-center justify-between bg-[#1a4731] px-5 py-3 text-white">
              <h3 className="text-sm font-bold">{preview.title}</h3>
              <button onClick={() => setPreview(null)} className="text-xl leading-none">
                ×
              </button>
            </div>
            <style dangerouslySetInnerHTML={{ __html: PREVIEW_STYLES }} />
            <div className="max-h-[65vh] overflow-y-auto bg-white p-5">
              <div className="pdoc" dangerouslySetInnerHTML={{ __html: preview.html }} />
            </div>
            <div className="flex gap-2 border-t bg-gray-50 px-5 py-3">
              <Button onClick={() => printContenido(preview.html)}>
                <Printer className="h-4 w-4" />
                Imprimir / Guardar PDF
              </Button>
              <Button variant="secondary" onClick={() => setPreview(null)}>
                Cerrar
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          role="status"
          className="fixed left-1/2 top-1/2 z-[10001] -translate-x-1/2 -translate-y-1/2 rounded-lg border-2 px-5 py-3.5 text-center text-sm font-bold shadow-2xl"
          style={{ background: "#f4fff8", borderColor: "#2f8f63", color: "#123d29" }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}

// ─── Day section with non-expandable prefactura rows ────────────────────

interface DaySectionRowsProps {
  day: { info: FechaInfo; entries: Prefactura[] };
  rowNumbers: Map<string, number>;
  ui: ReturnType<typeof resolveUiActions>;
  onPrint: (id: string) => void;
  onEdit: (pf: Prefactura) => void;
  onDelete: (id: string) => void;
}

function DaySectionRows({
  day,
  rowNumbers,
  ui,
  onPrint,
  onEdit,
  onDelete,
}: DaySectionRowsProps) {
  // Totals computed over the PAGE slice of this day (EX-11).
  const totals = daySectionTotals(day.entries);
  return (
    <>
      <tr className="bg-[#e8f5ee] text-[11px] font-bold" style={{ color: "#1a4731" }}>
        <td colSpan={7} className="px-2 py-2">
          <div className="flex items-center justify-between gap-2">
            <span>{day.info.dayLabel}</span>
            <span className="text-[10px] font-semibold">
              {totals.records} registros · {totals.items} ítems · {totals.cantidad} cantidades
            </span>
          </div>
        </td>
      </tr>
      {day.entries.map((pf) => (
        <PfRows
          key={pf.id}
          pf={pf}
          // Continuous N° over the full displayed set — CSV parity (#1682).
          rowNumber={rowNumbers.get(pf.id) ?? 0}
          ui={ui}
          onPrint={onPrint}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </>
  );
}

interface PfRowsProps {
  pf: Prefactura;
  rowNumber: number;
  ui: ReturnType<typeof resolveUiActions>;
  onPrint: (id: string) => void;
  onEdit: (pf: Prefactura) => void;
  onDelete: (id: string) => void;
}

function PfRows({
  pf,
  rowNumber,
  ui,
  onPrint,
  onEdit,
  onDelete,
}: PfRowsProps) {
  return (
    <>
      <tr className="border-b transition-colors hover:bg-[#f0f7f2]" style={{ borderColor: "oklch(0.55 0.04 160 / 0.08)" }}>
        <td className="px-2 py-2 text-[10px] text-gray-400">{rowNumber}</td>
        <td className="px-2 py-2 font-bold text-gray-900">{pf.paciente}</td>
        <td className="px-2 py-2">{pf.cedula}</td>
        <td className="px-2 py-2 text-[10px]">{pf.facturador}</td>
        <td className="px-2 py-2 text-[10px] text-gray-500">{pf.hora}</td>
        <td className="px-2 py-2 text-center">
          <span
            title={badgeTooltip(pf.items)}
            className="rounded-full px-2.5 py-0.5 text-[10px] font-bold text-white"
            style={{ background: "#2c6e4e" }}
          >
            {pf.items.length}
          </span>
        </td>
        <td className="px-2 py-2">
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPrint(pf.id)}
              title="Ver e imprimir"
              className="rounded p-1 text-white"
              style={{ background: "#1a6b47" }}
            >
              <Printer className="h-3 w-3" />
            </button>
            {ui.edit && (
              <button
                onClick={() => onEdit(pf)}
                title="Editar"
                className="rounded p-1 text-white"
                style={{ background: "#2c5282" }}
              >
                <Pencil className="h-3 w-3" />
              </button>
            )}
            {ui.delete && (
              <button
                onClick={() => void onDelete(pf.id)}
                title="Eliminar"
                className="rounded p-1 text-white"
                style={{ background: "#c0392b" }}
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )}
          </div>
        </td>
      </tr>
    </>
  );
}