import { describe, it, expect, afterEach, vi } from "vitest";
import {
  normalizeSearch,
  searchExamenes,
  migrateFlatToGrouped,
  listadoFechaInfo,
  groupMonths,
  filterByMonth,
  autocompleteFacturador,
  buildPrefactura,
  formatFechaEsCo,
  formatHoraEsCo,
  tcDisplay,
  resolveUiActions,
  genPrefacturaId,
  canonicalJson,
  baseHash,
  postArray,
  type Examen,
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
    });
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

// ─── autocompleteFacturador (EX-8) ────────────────────────────────────────

const FACTURADORES = ["Angie Chapuel", "Cataleya Tapia", "Silvia Ordoñez"];

describe("autocompleteFacturador", () => {
  it("inline-completes from name start at >=2 chars with selection start", () => {
    expect(autocompleteFacturador("ang", FACTURADORES)).toEqual({
      text: "Angie Chapuel",
      inline: true,
    });
  });

  it("returns word-start completion (Tab-only) when name start does not match", () => {
    expect(autocompleteFacturador("ta", FACTURADORES)).toEqual({
      text: "Cataleya Tapia",
      inline: false,
    });
  });

  it("returns null for single-char input", () => {
    expect(autocompleteFacturador("a", FACTURADORES)).toBeNull();
  });

  it("returns null when the typed value equals a full name (nothing to complete)", () => {
    expect(autocompleteFacturador("SILVIA ORDOÑEZ", FACTURADORES)).toBeNull();
  });

  it("returns null when no name matches", () => {
    expect(autocompleteFacturador("zzz", FACTURADORES)).toBeNull();
  });

  it("returns null for empty facturadores list", () => {
    expect(autocompleteFacturador("ang", [])).toBeNull();
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
    expect(pf.items[0]).toEqual({ cod: "906131", nom: "Trypanosoma", neps: "", mall: "", emss: "" });
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