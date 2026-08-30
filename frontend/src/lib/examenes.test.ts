import { describe, it, expect, afterEach, vi } from "vitest";
import {
  normalizeSearch,
  searchExamenes,
  normalizeListadoQuery,
  searchListado,
  inRange,
  filterByDateRange,
  paginate,
  listadoRowNumbers,
  daySectionTotals,
  badgeTooltip,
  migrateFlatToGrouped,
  listadoFechaInfo,
  groupMonths,
  filterByMonth,
  buildPrefactura,
  normalizeItem,
  formatFechaEsCo,
  formatHoraEsCo,
  tcDisplay,
  resolveUiActions,
  genPrefacturaId,
  canonicalJson,
  baseHash,
  postArray,
  type Examen,
  type Prefactura,
} from "./examenes";

const CATALOG: Examen[] = [
  { cod: "903859", nom: "Potasio En Suero U Otros Fluidos", neps: "X", mall: "X", emss: "X" },
  { cod: "903016", nom: "Ferritina", neps: "AUTH", mall: "AUTH", emss: "AUTH" },
  { cod: "903810", nom: "Calcio Semiautomatizado", neps: "X", mall: "", emss: "" },
  { cod: "906131", nom: "Trypanosoma Cruzi Anticuerpos Ig G", neps: "", mall: "", emss: "" },
];

// ─── normalizeSearch / searchExamenes (EX-6) ─────────────────────────────

describe("normalizeSearch", () => {
  it("trims and uppercases the query", () => {
    expect(normalizeSearch("  903859  ")).toBe("903859");
    expect(normalizeSearch(" potasio ")).toBe("POTASIO");
  });

  it("returns empty string for blank input", () => {
    expect(normalizeSearch("")).toBe("");
    expect(normalizeSearch("   ")).toBe("");
  });
});

describe("searchExamenes", () => {
  it("returns the exact cod match first (single result)", () => {
    const results = searchExamenes(CATALOG, "903859");
    expect(results).toHaveLength(1);
    expect(results[0].cod).toBe("903859");
  });

  it("exact match wins even when substrings also match", () => {
    const results = searchExamenes(CATALOG, "903810");
    expect(results).toHaveLength(1);
    expect(results[0].cod).toBe("903810");
  });

  it("matches substring on cod when no exact match", () => {
    const results = searchExamenes(CATALOG, "906");
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((e) => e.cod.includes("906"))).toBe(true);
  });

  it("matches substring on nom case-insensitively", () => {
    const results = searchExamenes(CATALOG, "potasio");
    expect(results).toHaveLength(1);
    expect(results[0].cod).toBe("903859");
  });

  it("normalizes the query (trim + uppercase) before matching", () => {
    expect(searchExamenes(CATALOG, "  POTASIO  ")).toHaveLength(1);
    expect(searchExamenes(CATALOG, " 903859 ")).toHaveLength(1);
  });

  it("returns empty array for blank query", () => {
    expect(searchExamenes(CATALOG, "")).toEqual([]);
    expect(searchExamenes(CATALOG, "   ")).toEqual([]);
  });

  it("returns empty array when nothing matches", () => {
    expect(searchExamenes(CATALOG, "zzz")).toEqual([]);
  });

  it("returns empty array when catalog is empty", () => {
    expect(searchExamenes([], "903859")).toEqual([]);
  });
});

// ─── migrateFlatToGrouped (D5, EX-18) ────────────────────────────────────

describe("migrateFlatToGrouped", () => {
  const flat = [
    { cod: "903859", nom: "Potasio", neps: "X", mall: "X", emss: "X", paciente: "Juan Perez", cedula: "111", facturador: "Angie Chapuel", hora: "15/01/2026 08:30" },
    { cod: "903016", nom: "Ferritina", neps: "AUTH", mall: "", emss: "", paciente: "Juan Perez", cedula: "111", facturador: "Angie Chapuel", hora: "15/01/2026 08:30" },
    { cod: "903810", nom: "Calcio", neps: "X", mall: "", emss: "", paciente: "Maria Lopez", cedula: "222", facturador: "Cataleya Tapia", hora: "16/01/2026 09:00" },
  ];

  it("groups flat records by (paciente|facturador) case-insensitive", () => {
    const result = migrateFlatToGrouped(flat);
    expect(result).toHaveLength(2);
    const juan = result.find((p) => p.paciente === "Juan Perez");
    expect(juan?.items).toHaveLength(2);
    const maria = result.find((p) => p.paciente === "Maria Lopez");
    expect(maria?.items).toHaveLength(1);
  });

  it("grouping key is case-insensitive", () => {
    const mixed = [
      { ...flat[0], paciente: "JUAN PEREZ" },
      { ...flat[1], paciente: "juan perez" },
    ];
    expect(migrateFlatToGrouped(mixed)).toHaveLength(1);
  });

  it("preserves patient/facturador/hora on the prefactura", () => {
    const result = migrateFlatToGrouped([flat[0]]);
    expect(result[0].paciente).toBe("Juan Perez");
    expect(result[0].cedula).toBe("111");
    expect(result[0].facturador).toBe("Angie Chapuel");
    expect(result[0].hora).toBe("15/01/2026 08:30");
  });

  it("copies item fields with empty-string fallback for missing flags", () => {
    const noFlags = { ...flat[1], neps: undefined, mall: undefined, emss: undefined };
    const result = migrateFlatToGrouped([noFlags]);
    expect(result[0].items[0]).toEqual({
      cod: "903016",
      nom: "Ferritina",
      neps: "",
      mall: "",
      emss: "",
      cantidad: 1,
    });
  });

  it("initializes grouped items with cantidad 1 (EX-23 migration)", () => {
    const result = migrateFlatToGrouped([flat[0]]);
    expect(result[0].items[0]).toEqual(
      expect.objectContaining({ cod: "903859", cantidad: 1 }),
    );
  });

  it("generates unique pf ids in pf-<ts>-<rand> format", () => {
    const result = migrateFlatToGrouped(flat);
    for (const pf of result) {
      expect(pf.id).toMatch(/^pf-\d+-[a-z0-9]{4}$/);
    }
    expect(new Set(result.map((p) => p.id)).size).toBe(result.length);
  });

  it("returns empty array for empty input", () => {
    expect(migrateFlatToGrouped([])).toEqual([]);
  });
});

// ─── listadoFechaInfo / groupMonths / filterByMonth (EX-11) ───────────────

describe("listadoFechaInfo", () => {
  it("parses dd/mm/yyyy with time into month/day keys", () => {
    const info = listadoFechaInfo("15/01/2026 08:30");
    expect(info.monthKey).toBe("2026-01");
    expect(info.dayKey).toBe("2026-01-15");
    expect(info.sortKey).toBe(new Date(2026, 0, 15).getTime());
    expect(info.monthLabel).toBe("Enero de 2026");
    expect(info.dayLabel).toContain("15");
  });

  it("parses dd/mm/yyyy without time", () => {
    const info = listadoFechaInfo("05/05/2026");
    expect(info.monthKey).toBe("2026-05");
    expect(info.dayKey).toBe("2026-05-05");
  });

  it("capitalizes the first letter of labels", () => {
    const info = listadoFechaInfo("28/08/2026");
    expect(info.monthLabel).toBe("Agosto de 2026");
  });

  it("returns sin-fecha for unparseable horas (never drops the record)", () => {
    const info = listadoFechaInfo("n/a");
    expect(info.monthKey).toBe("sin-fecha");
    expect(info.dayKey).toBe("sin-fecha");
    expect(info.sortKey).toBe(-Infinity);
    expect(info.monthLabel).toBe("Fecha no disponible");
    expect(info.dayLabel).toBe("Fecha no disponible");
  });

  it("returns sin-fecha for null/empty hora", () => {
    expect(listadoFechaInfo(null).monthKey).toBe("sin-fecha");
    expect(listadoFechaInfo(undefined).monthKey).toBe("sin-fecha");
    expect(listadoFechaInfo("").monthKey).toBe("sin-fecha");
  });

  it("rejects impossible dates via round-trip validation (31/02)", () => {
    expect(listadoFechaInfo("31/02/2026").monthKey).toBe("sin-fecha");
  });

  it("rejects malformed day/month segments", () => {
    expect(listadoFechaInfo("2026-01-15").monthKey).toBe("sin-fecha");
    expect(listadoFechaInfo("15/13/2026").monthKey).toBe("sin-fecha");
  });
});

describe("groupMonths", () => {
  it("returns unique months sorted newest-first", () => {
    const listado = [
      { id: "a", paciente: "A", cedula: "", facturador: "", hora: "15/01/2026", items: [] },
      { id: "b", paciente: "B", cedula: "", facturador: "", hora: "28/08/2026", items: [] },
      { id: "c", paciente: "C", cedula: "", facturador: "", hora: "05/01/2026", items: [] },
      { id: "d", paciente: "D", cedula: "", facturador: "", hora: "n/a", items: [] },
    ] as never[];
    const months = groupMonths(listado);
    expect(months.map((m) => m.monthKey)).toEqual(["2026-08", "2026-01", "sin-fecha"]);
    expect(months[0].monthLabel).toBe("Agosto de 2026");
    expect(months[2].monthLabel).toBe("Fecha no disponible");
  });

  it("returns empty array for empty listado", () => {
    expect(groupMonths([])).toEqual([]);
  });
});

describe("filterByMonth", () => {
  const listado = [
    { id: "a", paciente: "A", hora: "15/01/2026", items: [] },
    { id: "b", paciente: "B", hora: "28/08/2026", items: [] },
  ] as never[];

  it("returns all records for 'todos'", () => {
    expect(filterByMonth(listado, "todos")).toHaveLength(2);
  });

  it("returns only records of the selected month", () => {
    const result = filterByMonth(listado, "2026-08");
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("b");
  });

  it("includes sin-fecha records under the sin-fecha filter", () => {
    const mixed = [...listado, { id: "c", paciente: "C", hora: "n/a", items: [] }] as never[];
    expect(filterByMonth(mixed, "sin-fecha")).toHaveLength(1);
    expect(filterByMonth(mixed, "sin-fecha")[0].id).toBe("c");
  });

  it("returns empty array for a month with no records", () => {
    expect(filterByMonth(listado, "2026-12")).toEqual([]);
  });
});

// ─── buildPrefactura (EX-10) ──────────────────────────────────────────────

describe("buildPrefactura", () => {
  const now = new Date(2026, 7, 28, 14, 5);

  it("builds a prefactura with trimmed values and item flags", () => {
    const pf = buildPrefactura({
      paciente: "  Juan Perez  ",
      cedula: " 111 ",
      facturador: " Angie Chapuel ",
      items: [{ cod: "903859", nom: "Potasio", neps: "X", mall: "X", emss: "X" }],
      now,
    });
    expect(pf.paciente).toBe("Juan Perez");
    expect(pf.cedula).toBe("111");
    expect(pf.facturador).toBe("Angie Chapuel");
    expect(pf.hora).toBe("28/08/2026 14:05");
    expect(pf.items).toHaveLength(1);
    expect(pf.id).toMatch(/^pf-\d+-[a-z0-9]{4}$/);
  });

  it("applies source defaults for blank patient/facturador", () => {
    const pf = buildPrefactura({ paciente: "", cedula: "", facturador: "", items: [], now });
    expect(pf.paciente).toBe("Sin nombre");
    expect(pf.cedula).toBe("—");
    expect(pf.facturador).toBe("—");
  });

  it("normalizes missing item flags to empty strings", () => {
    const pf = buildPrefactura({
      paciente: "A",
      cedula: "1",
      facturador: "F",
      items: [{ cod: "906131", nom: "Trypanosoma" } as never],
      now,
    });
    expect(pf.items[0]).toEqual({ cod: "906131", nom: "Trypanosoma", neps: "", mall: "", emss: "", cantidad: 1 });
  });

  it("carries each item's cantidad (normalized) into the prefactura (EX-23)", () => {
    const pf = buildPrefactura({
      paciente: "A",
      cedula: "1",
      facturador: "F",
      items: [{ cod: "903859", nom: "Potasio", neps: "X", mall: "X", emss: "X", cantidad: 2 }],
      now,
    });
    expect(pf.items[0]).toEqual(
      expect.objectContaining({ cod: "903859", cantidad: 2 }),
    );
  });
});

// ─── normalizeItem (EX-21/EX-27) ──────────────────────────────────────────

describe("normalizeItem", () => {
  const base = { cod: "903859", nom: "Potasio", neps: "X", mall: "X", emss: "X" };

  it("defaults missing cantidad to 1 (legacy 5-field items)", () => {
    expect(normalizeItem(base).cantidad).toBe(1);
  });

  it("clamps NaN to 1", () => {
    expect(normalizeItem({ ...base, cantidad: Number.NaN }).cantidad).toBe(1);
  });

  it("clamps 0 and negative values to 1", () => {
    expect(normalizeItem({ ...base, cantidad: 0 }).cantidad).toBe(1);
    expect(normalizeItem({ ...base, cantidad: -2 }).cantidad).toBe(1);
  });

  it("truncates fractional quantities (2.9 → 2)", () => {
    expect(normalizeItem({ ...base, cantidad: 2.9 }).cantidad).toBe(2);
  });

  it("passes valid integers through unchanged", () => {
    expect(normalizeItem({ ...base, cantidad: 4 }).cantidad).toBe(4);
  });

  it("preserves the other item fields while clamping", () => {
    expect(normalizeItem({ ...base, cantidad: 0 })).toEqual({ ...base, cantidad: 1 });
  });
});

// ─── Date/time formatters ─────────────────────────────────────────────────

describe("formatFechaEsCo / formatHoraEsCo", () => {
  it("formats dd/mm/yyyy with zero padding", () => {
    expect(formatFechaEsCo(new Date(2026, 0, 5))).toBe("05/01/2026");
    expect(formatFechaEsCo(new Date(2026, 7, 28))).toBe("28/08/2026");
  });

  it("formats hora as dd/mm/yyyy hh:mm (24h, zero padded)", () => {
    expect(formatHoraEsCo(new Date(2026, 7, 28, 9, 7))).toBe("28/08/2026 09:07");
    expect(formatHoraEsCo(new Date(2026, 7, 28, 23, 59))).toBe("28/08/2026 23:59");
  });
});

// ─── tcDisplay (EX-11 sub-table) ──────────────────────────────────────────

describe("tcDisplay", () => {
  it("maps X→SI, AUTH→AUTH, empty→—", () => {
    expect(tcDisplay("X")).toBe("SI");
    expect(tcDisplay("AUTH")).toBe("AUTH");
    expect(tcDisplay("")).toBe("—");
    expect(tcDisplay(undefined)).toBe("—");
    expect(tcDisplay(null)).toBe("—");
  });
});

// ─── genPrefacturaId ──────────────────────────────────────────────────────

describe("genPrefacturaId", () => {
  it("generates pf-<timestamp>-<4 char> ids and unique across calls", () => {
    const a = genPrefacturaId();
    const b = genPrefacturaId();
    expect(a).toMatch(/^pf-\d+-[a-z0-9]{4}$/);
    expect(a).not.toBe(b);
  });
});

// ─── resolveUiActions (EX-17 / EX-20) ─────────────────────────────────────

describe("resolveUiActions", () => {
  it("grants all write actions when can_write is true", () => {
    const actions = resolveUiActions(true);
    expect(actions).toEqual({ admin: true, save: true, edit: true, delete: true, clear: true });
  });

  it("hides admin tab and all write controls for read-only users", () => {
    const actions = resolveUiActions(false);
    expect(actions).toEqual({ admin: false, save: false, edit: false, delete: false, clear: false });
  });
});

// ─── baseHash / postArray (R4-001) ───────────────────────────────────────

describe("canonicalJson / baseHash", () => {
  it("serializes compact with sorted keys (backend-compatible) and is deterministic", async () => {
    expect(canonicalJson([{ b: 1, a: "x" }])).toBe('[{"a":"x","b":1}]');
    const a = await baseHash(CATALOG);
    expect(a).toMatch(/^[0-9a-f]{64}$/);
    expect(a).toBe(await baseHash(JSON.parse(canonicalJson(CATALOG))));
  });

  it("differs for different arrays (detects stale copies)", async () => {
    expect(await baseHash([{ cod: "1" }])).not.toBe(await baseHash([{ cod: "2" }]));
  });
});

describe("postArray conflict handling", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends {data, base_hash} and maps 409 to conflict", async () => {
    const capture: { url: string; body: unknown } = { url: "", body: null };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        capture.url = String(url);
        capture.body = JSON.parse(String(init?.body));
        return new Response(JSON.stringify({ status: "error", data: {}, errors: ["Conflicto"] }), { status: 409 });
      }),
    );

    const result = await postArray("/api/listado", [{ id: "x" }], [{ id: "y" }]);

    expect(result).toBe("conflict");
    expect(capture.url).toBe("/api/listado");
    expect((capture.body as Record<string, unknown>).data).toEqual([{ id: "x" }]);
    expect(typeof (capture.body as Record<string, unknown>).base_hash).toBe("string");
  });

  it("returns ok on 200, error on non-409 and on network failure", async () => {
    const stub = (status: number, body?: unknown, fail = false) =>
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => {
          if (fail) throw new Error("offline");
          return new Response(JSON.stringify(body ?? { status: "success", data: {}, errors: [] }), { status });
        }),
      );
    stub(200);
    expect(await postArray("/api/listado", [{ id: "x" }], [{ id: "y" }])).toBe("ok");
    stub(500);
    expect(await postArray("/api/listado", [{ id: "x" }])).toBe("error");
    stub(500, undefined, true);
    expect(await postArray("/api/listado", [{ id: "x" }])).toBe("error");
  });

  it("falls back to a plain array when no base is provided (legacy)", async () => {
    let sentBody = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        sentBody = String(init?.body);
        return new Response(JSON.stringify({ status: "success", data: {}, errors: [] }));
      }),
    );

    await postArray("/api/listado", [{ id: "x" }]);

    expect(JSON.parse(sentBody)).toEqual([{ id: "x" }]);
  });
});

// ─── Listado search (EX-29) ─────────────────────────────────────────────

/** Prefactura fixture: items carry normalized-cantidad defaults. */
function mkPf(
  id: string,
  paciente: string,
  hora: string,
  items: Array<{ cod: string; nom: string; cantidad?: number }>,
): Prefactura {
  return {
    id,
    paciente,
    cedula: "111",
    facturador: "Angie Chapuel",
    hora,
    items: items.map((i) => ({
      cod: i.cod,
      nom: i.nom,
      neps: "",
      mall: "",
      emss: "",
      ...(i.cantidad !== undefined ? { cantidad: i.cantidad } : {}),
    })),
  };
}

describe("normalizeListadoQuery", () => {
  it("strips combining marks (NFD) and uppercases (ñ/ü/á)", () => {
    expect(normalizeListadoQuery("Álvaro Ñúñez")).toBe("ALVARO NUNEZ");
    expect(normalizeListadoQuery("código")).toBe("CODIGO");
    expect(normalizeListadoQuery("müller")).toBe("MULLER");
  });

  it("trims surrounding whitespace", () => {
    expect(normalizeListadoQuery("  Potasio  ")).toBe("POTASIO");
  });

  it("returns empty string for blank input", () => {
    expect(normalizeListadoQuery("")).toBe("");
    expect(normalizeListadoQuery("   ")).toBe("");
  });
});

describe("searchListado", () => {
  const listado: Prefactura[] = [
    mkPf("a", "Álvaro Ñúñez", "15/01/2026 08:30", [{ cod: "903859", nom: "Potasio En Suero" }]),
    mkPf("b", "Maria Lopez", "n/a", [{ cod: "903016", nom: "Ferritina" }]),
    mkPf(
      "c",
      "Juan Perez",
      "28/08/2026 09:00",
      [
        { cod: "903810", nom: "Calcio Semiautomatizado", cantidad: 2 },
        { cod: "906131", nom: "Trypanosoma Cruzi Ig G" },
      ],
    ),
  ];

  it("folds accents on BOTH query and fields (Álvaro Ñúñez ≈ 'alvaro nunez')", () => {
    const results = searchListado(listado, "alvaro nunez");
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe("a");
  });

  it("matches an item cod (substring, folded)", () => {
    const results = searchListado(listado, "9061");
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe("c");
  });

  it("matches an item nom case-insensitively ('potasio')", () => {
    const results = searchListado(listado, "potasio");
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe("a");
  });

  it("includes sin-fecha records when their paciente matches", () => {
    const results = searchListado(listado, "maria");
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe("b");
  });

  it("matches facturador and cedula fields", () => {
    expect(searchListado(listado, "chapuel")).toHaveLength(3);
    const byCedula = searchListado(listado, "111");
    expect(byCedula).toHaveLength(3);
  });

  it("returns the input unchanged (same reference) for a blank query", () => {
    expect(searchListado(listado, "")).toBe(listado);
    expect(searchListado(listado, "   ")).toBe(listado);
  });

  it("returns empty array when nothing matches", () => {
    expect(searchListado(listado, "zzz")).toEqual([]);
  });

  it("returns empty array for an empty listado", () => {
    expect(searchListado([], "potasio")).toEqual([]);
  });
});

// ─── Date-range filter (EX-30) ──────────────────────────────────────────

describe("inRange", () => {
  const dated = mkPf("a", "A", "15/08/2026 08:30", [{ cod: "903859", nom: "Potasio" }]);
  const onBound = mkPf("b", "B", "01/08/2026", [{ cod: "903016", nom: "Ferritina" }]);
  const noFecha = mkPf("c", "C", "n/a", [{ cod: "903810", nom: "Calcio" }]);

  it("keeps records within inclusive [from, to] bounds", () => {
    expect(inRange(dated, "2026-08-01", "2026-08-15")).toBe(true);
    expect(inRange(onBound, "2026-08-01", "2026-08-15")).toBe(true);
    expect(inRange(mkPf("d", "D", "16/08/2026", [{ cod: "903859", nom: "Potasio" }]), "2026-08-01", "2026-08-15")).toBe(false);
  });

  it("treats sin-fecha as never in range (A5)", () => {
    expect(inRange(noFecha, "2026-08-01", "2026-08-15")).toBe(false);
    expect(inRange(noFecha, null, null)).toBe(false);
  });

  it("supports one-sided bounds (from-only, to-only)", () => {
    expect(inRange(dated, "2026-08-10", null)).toBe(true);
    expect(inRange(mkPf("e", "E", "05/08/2026", [{ cod: "903859", nom: "Potasio" }]), "2026-08-10", null)).toBe(false);
    expect(inRange(mkPf("f", "F", "05/08/2026", [{ cod: "903859", nom: "Potasio" }]), null, "2026-08-10")).toBe(true);
    expect(inRange(dated, null, "2026-08-10")).toBe(false);
  });

  it("returns true for dated records when both bounds are null", () => {
    expect(inRange(dated, null, null)).toBe(true);
  });

  it("returns false for an inverted range (to < from)", () => {
    expect(inRange(dated, "2026-08-20", "2026-08-10")).toBe(false);
  });
});

describe("filterByDateRange", () => {
  const listado: Prefactura[] = [
    mkPf("a", "A", "01/08/2026", [{ cod: "903859", nom: "Potasio" }]),
    mkPf("b", "B", "15/08/2026", [{ cod: "903016", nom: "Ferritina" }]),
    mkPf("c", "C", "28/08/2026", [{ cod: "903810", nom: "Calcio" }]),
    mkPf("d", "D", "n/a", [{ cod: "906131", nom: "Trypanosoma" }]),
  ];

  it("keeps only records dated within the window (inclusive)", () => {
    const result = filterByDateRange(listado, "2026-08-01", "2026-08-15");
    expect(result.map((p) => p.id)).toEqual(["a", "b"]);
  });

  it("excludes sin-fecha records from range results (assumption 5)", () => {
    const result = filterByDateRange(listado, "2026-08-01", "2026-08-31");
    expect(result.map((p) => p.id)).toEqual(["a", "b", "c"]);
  });

  it("supports one-sided ranges", () => {
    expect(filterByDateRange(listado, "2026-08-10", null).map((p) => p.id)).toEqual(["b", "c"]);
    expect(filterByDateRange(listado, null, "2026-08-20").map((p) => p.id)).toEqual(["a", "b"]);
  });

  it("returns zero records for an inverted range (to < from)", () => {
    expect(filterByDateRange(listado, "2026-08-20", "2026-08-10")).toEqual([]);
  });

  it("with both bounds null keeps dated records but still excludes sin-fecha", () => {
    const result = filterByDateRange(listado, null, null);
    expect(result.map((p) => p.id)).toEqual(["a", "b", "c"]);
  });
});

// ─── Pagination (EX-31) ─────────────────────────────────────────────────

describe("paginate", () => {
  const records = Array.from({ length: 60 }, (_, i) =>
    mkPf(`pf-${i}`, `Paciente ${i}`, "01/08/2026", [{ cod: "903859", nom: "Potasio" }]),
  );

  it("slices 60 records at size 25 into 25/25/10 across 3 pages", () => {
    const p1 = paginate(records, 1, 25);
    expect(p1.items).toHaveLength(25);
    expect(p1.page).toBe(1);
    expect(p1.total).toBe(60);
    expect(p1.totalPages).toBe(3);
    expect(p1.items[0].id).toBe("pf-0");
    const p2 = paginate(records, 2, 25);
    expect(p2.items).toHaveLength(25);
    expect(p2.items[0].id).toBe("pf-25");
    const p3 = paginate(records, 3, 25);
    expect(p3.items).toHaveLength(10);
    expect(p3.items[0].id).toBe("pf-50");
  });

  it("clamps out-of-range pages into 1..totalPages", () => {
    expect(paginate(records, 0, 25).page).toBe(1);
    expect(paginate(records, 99, 25).page).toBe(3);
    expect(paginate(records, -5, 25).items[0].id).toBe("pf-0");
  });

  it("returns an empty page with totalPages 0 for empty input", () => {
    const empty = paginate<Prefactura>([], 1, 25);
    expect(empty.items).toEqual([]);
    expect(empty.total).toBe(0);
    expect(empty.totalPages).toBe(0);
    expect(empty.page).toBe(1);
  });

  it("produces a single page for an exact multiple of pageSize (25/25)", () => {
    const exact = paginate(records.slice(0, 25), 1, 25);
    expect(exact.totalPages).toBe(1);
    expect(exact.items).toHaveLength(25);
  });

  it("honors the pageSize selector (50 and 100)", () => {
    const p50 = paginate(records, 2, 50);
    expect(p50.totalPages).toBe(2);
    expect(p50.items).toHaveLength(10);
    expect(p50.items[0].id).toBe("pf-50");
    const p100 = paginate(records, 1, 100);
    expect(p100.totalPages).toBe(1);
    expect(p100.items).toHaveLength(60);
  });

  it("guards non-positive pageSize (treats 0 as 1)", () => {
    const p = paginate(records.slice(0, 5), 1, 0);
    expect(p.totalPages).toBe(5);
    expect(p.items).toHaveLength(1);
  });
});

// ─── Numbering / totals / tooltip (EX-11) ───────────────────────────────

import { buildCsv } from "./csv";

describe("listadoRowNumbers", () => {
  it("assigns continuous 1-based numbers = first-item CSV index (multi-item parity #1682)", () => {
    const listado: Prefactura[] = [
      mkPf("A", "Ana", "01/08/2026", [
        { cod: "903859", nom: "Potasio" },
        { cod: "903016", nom: "Ferritina" },
        { cod: "903810", nom: "Calcio" },
      ]),
      mkPf("B", "Beto", "02/08/2026", [{ cod: "906131", nom: "Trypanosoma" }]),
      mkPf("C", "Caro", "03/08/2026", [
        { cod: "903859", nom: "Potasio" },
        { cod: "906131", nom: "Trypanosoma" },
      ]),
    ];
    const rowNumbers = listadoRowNumbers(listado);
    expect(rowNumbers.get("A")).toBe(1);
    expect(rowNumbers.get("B")).toBe(4);
    expect(rowNumbers.get("C")).toBe(5);
    expect(rowNumbers.size).toBe(3);

    // Cross-check against the REAL buildCsv output (one row per item).
    const { csv } = buildCsv(listado, null);
    const lines = csv.replace("\uFEFF", "").trim().split("\n");
    expect(lines).toHaveLength(7); // header + 3 + 1 + 2 item rows
    const nums = lines.slice(1).map((line) => Number(line.split(",")[0]));
    expect(nums).toEqual([1, 2, 3, 4, 5, 6]);
    // First-item CSV N° per prefactura (offsets 0, 3, 4) == screen N°.
    expect(nums[0]).toBe(rowNumbers.get("A"));
    expect(nums[3]).toBe(rowNumbers.get("B"));
    expect(nums[4]).toBe(rowNumbers.get("C"));
  });

  it("is stable across pagination (same map for the full filtered set)", () => {
    const listado = Array.from({ length: 30 }, (_, i) =>
      mkPf(`p${i}`, `P ${i}`, "01/08/2026", [{ cod: "903859", nom: "Potasio" }]),
    );
    const rowNumbers = listadoRowNumbers(listado);
    const page2 = paginate(listado, 2, 25);
    for (const pf of page2.items) {
      expect(rowNumbers.get(pf.id)).toBe(Number(pf.id.slice(1)) + 1);
    }
  });
});

describe("daySectionTotals", () => {
  it("sums records, items and normalized cantidad for a day slice", () => {
    const entries: Prefactura[] = [
      mkPf("a", "A", "01/08/2026", [
        { cod: "903859", nom: "Potasio", cantidad: 3 },
        { cod: "903016", nom: "Ferritina", cantidad: 1 },
      ]),
      mkPf("b", "B", "01/08/2026", [{ cod: "903810", nom: "Calcio", cantidad: 5 }]),
      mkPf("c", "C", "01/08/2026", [{ cod: "906131", nom: "Trypanosoma" }]), // cantidad absent → 1
    ];
    const totals = daySectionTotals(entries);
    expect(totals.records).toBe(3);
    expect(totals.items).toBe(4);
    expect(totals.cantidad).toBe(10);
  });

  it("returns zeros for an empty slice", () => {
    expect(daySectionTotals([])).toEqual({ records: 0, items: 0, cantidad: 0 });
  });

  it("normalizes fractional item cantidad before summing (2.9 → 2)", () => {
    const entries = [mkPf("a", "A", "01/08/2026", [{ cod: "903859", nom: "Potasio", cantidad: 2.9 }])];
    expect(daySectionTotals(entries).cantidad).toBe(2);
  });
});

describe("badgeTooltip", () => {
  const item = (cod: string, nom: string, cantidad?: number) => ({ cod, nom, neps: "", mall: "", emss: "", ...(cantidad !== undefined ? { cantidad } : {}) });

  it("lists up to 8 items as 'cod — nom (x cantidad)' without cap suffix", () => {
    const items = [item("903859", "Potasio", 2), item("903016", "Ferritina")];
    expect(badgeTooltip(items)).toBe("903859 — Potasio (x 2)\n903016 — Ferritina (x 1)");
  });

  it("caps at 8 items and appends '+N más'", () => {
    const items = Array.from({ length: 10 }, (_, i) => item(`903${i}`, `Examen ${i}`));
    const tooltip = badgeTooltip(items);
    const lines = tooltip.split("\n");
    expect(lines).toHaveLength(9);
    expect(lines[0]).toMatch(/^9030 — Examen 0 \(x 1\)$/);
    expect(lines[7]).toMatch(/^9037 — Examen 7 \(x 1\)$/);
    expect(lines[8]).toBe("+2 más");
  });

  it("returns empty string for a prefactura without items", () => {
    expect(badgeTooltip([])).toBe("");
  });
});