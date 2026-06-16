import { describe, it, expect } from "vitest";
import {
  parseScheduleText,
  autoDetectColumns,
  calcularResponsable,
  escapeHtml,
  getUniqueResponsables,
  filterResultsByResponsable,
  getSinEgresoButtonConfig,
  masDeDosTurnosMismoResponsable,
  type ScheduleDay,
  type FacturaResult,
} from "../utils";

// ─── parseScheduleText ────────────────────────────────────────────────

describe("parseScheduleText", () => {
  it("returns parsed days on happy path with DÍA header and tab-separated rows", () => {
    const input =
      "DÍA\tMañana\tTarde\tNoche\n" +
      "1\tCARLOS\tALEJANDRA\tYULIETH\n" +
      "2\tCAROLINA\tCARLOS\tALEJANDRA\n";

    const result = parseScheduleText(input);

    expect(result).not.toBeNull();
    expect(result).toHaveLength(2);
    expect(result![0]).toEqual({
      dia: 1,
      manana: "CARLOS",
      tarde: "ALEJANDRA",
      noche: "YULIETH",
    });
    expect(result![1]).toEqual({
      dia: 2,
      manana: "CAROLINA",
      tarde: "CARLOS",
      noche: "ALEJANDRA",
    });
  });

  it("handles DIA (without accent) header variant", () => {
    const input = "DIA\tA\tB\tC\n1\tX\tY\tZ\n";
    const result = parseScheduleText(input);
    expect(result).not.toBeNull();
    expect(result).toHaveLength(1);
    expect(result![0].dia).toBe(1);
  });

  it("returns null when no DIA/DÍA/DI header is found and data < 4 cols", () => {
    const input = "Fecha\tValor\tNota\n1\tA\tB\n2\tC\tD\n";
    const result = parseScheduleText(input);
    expect(result).toBeNull();
  });

  it("parses data without DIA header when rows have 4 cols and day numbers", () => {
    // Format like the schedule export: no header row, data starts directly
    const input =
      "1\tCARLOS\tALEJANDRA\tYULIETH\n" +
      "2\tCAROLINA\tCARLOS\tALEJANDRA\n";
    const result = parseScheduleText(input);
    expect(result).not.toBeNull();
    expect(result).toHaveLength(2);
    expect(result![0]).toEqual({
      dia: 1,
      manana: "CARLOS",
      tarde: "ALEJANDRA",
      noche: "YULIETH",
    });
    expect(result![1]).toEqual({
      dia: 2,
      manana: "CAROLINA",
      tarde: "CARLOS",
      noche: "ALEJANDRA",
    });
  });

  it("parses data with title row and multi-line quoted headers (URGENCIAS format)", () => {
    // Simulates the actual schedule export format
    const input =
      "URGENCIAS\t\t\t\n" +
      '"07:00 AM-01:00\n' +
      'PM"\t\t"01:00 PM-\n' +
      '07:00\n' +
      'PM"\t"07:00 PM-\n' +
      '07:00\n' +
      'AM"\n' +
      "1\tCARLOS\tCAROLINA\tYULIETH\n" +
      "2\tCAROLINA\tALEJANDRA\tCARLOS\n";
    const result = parseScheduleText(input);
    expect(result).not.toBeNull();
    expect(result).toHaveLength(2);
    expect(result![0]).toEqual({
      dia: 1,
      manana: "CARLOS",
      tarde: "CAROLINA",
      noche: "YULIETH",
    });
    expect(result![1]).toEqual({
      dia: 2,
      manana: "CAROLINA",
      tarde: "ALEJANDRA",
      noche: "CARLOS",
    });
  });

  it("returns null for empty input", () => {
    expect(parseScheduleText("")).toBeNull();
    expect(parseScheduleText("   ")).toBeNull();
  });

  it("handles line-internal quotes as literal text when not at line start", () => {
    // The legacy code only merges quoted fields when the opening " is at
    // the start of a line. Mid-line quotes in TSV (e.g. "Multi\nLine" as
    // a cell value) are NOT merged — the line is split and non-tabular
    // rows are skipped. This is a known legacy limitation.
    const input =
      'DÍA\tMañana\tTarde\tNoche\n' +
      '1\tCARLOS\t"Multi\n' +
      'Line"\tYULIETH\n';
    const result = parseScheduleText(input);
    // Data row is split by newline inside the quoted cell, producing
    // malformed tab rows that get filtered out.
    expect(result).toBeNull();
  });

  it("skips rows with fewer than 4 columns after header", () => {
    const input = "DÍA\tA\tB\tC\n1\tX\tY\tZ\n2\tW\n";
    const result = parseScheduleText(input);
    expect(result).not.toBeNull();
    expect(result).toHaveLength(1);
  });

  it("skips rows where first column is not a number", () => {
    const input = "DÍA\tA\tB\tC\nX\tY\tZ\tW\n1\tA\tB\tC\n";
    const result = parseScheduleText(input);
    expect(result).not.toBeNull();
    expect(result).toHaveLength(1);
    expect(result![0].dia).toBe(1);
  });

  it("normalizes \\r\\n and \\r line endings to \\n", () => {
    const input = "DÍA\tA\tB\tC\r\n1\tX\tY\tZ\r\n2\tW\tV\tU\r";
    const result = parseScheduleText(input);
    expect(result).not.toBeNull();
    expect(result).toHaveLength(2);
  });

  it("returns null when only header row is present (no data)", () => {
    const input = "DÍA\tA\tB\tC\n";
    const result = parseScheduleText(input);
    expect(result).toBeNull();
  });
});

// ─── autoDetectColumns ────────────────────────────────────────────────

describe("autoDetectColumns", () => {
  it("detects columns by header labels", () => {
    const headers = [
      "Fecha Crea",
      "Fecha Egreso",
      "N° Factura",
      "Estado",
      "Área",
      "Paciente",
      "HC Pendiente",
    ];
    const primeraFila = [
      "10/05/2026  08:30:00",
      "10/05/2026  10:15:00",
      "FEV416009",
      "Abierta",
      "Urgencias",
      "JUAN PÉREZ LÓPEZ",
      "No",
    ];

    const { cols, foundLabels } = autoDetectColumns(headers, primeraFila);

    expect(cols.fechaCreaIdx).toBe(0);
    expect(cols.fechaEgresoIdx).toBe(1);
    expect(cols.facturaIdx).toBe(2);
    expect(cols.estadoIdx).toBe(3);
    expect(cols.areaIdx).toBe(4);
    expect(cols.pacienteIdx).toBe(5);
    expect(cols.hcPendienteIdx).toBe(6);
    expect(foundLabels[0]).toBe("Fecha Crea");
    expect(foundLabels[1]).toBe("Fecha Egreso");
    expect(foundLabels[2]).toBe("N° Factura");
  });

  it("detects columns by value pattern when no headers", () => {
    const headers: string[] = [];
    const primeraFila = [
      "10/05/2026  08:30:00",
      "10/05/2026  10:15:00",
      "FEV416009",
      "Urgencias",
      "Juán Pérez López",
      "Abierta",
      "No",
    ];

    const { cols } = autoDetectColumns(headers, primeraFila);

    expect(cols.fechaCreaIdx).toBe(0);
    expect(cols.fechaEgresoIdx).toBe(1);
    expect(cols.facturaIdx).toBe(2);
    expect(cols.areaIdx).toBe(3);
    expect(cols.pacienteIdx).toBe(4);
    expect(cols.estadoIdx).toBe(5);
    expect(cols.hcPendienteIdx).toBe(6);
  });

  it("detects FEV standalone prefix with next column digits", () => {
    const headers: string[] = [];
    const primeraFila = [
      "10/05/2026  08:30:00",
      "10/05/2026  10:15:00",
      "FEV",
      "416009",
      "Urgencias",
      "JUAN PÉREZ LÓPEZ",
    ];

    const { cols } = autoDetectColumns(headers, primeraFila);

    expect(cols.facturaIdx).toBe(2); // "FEV" column, not the digits column
    expect(cols.fechaCreaIdx).toBe(0);
    expect(cols.fechaEgresoIdx).toBe(1);
  });

  it("returns -1 for undetected columns", () => {
    const headers: string[] = [];
    const primeraFila = ["foo", "bar", "baz"];
    const { cols } = autoDetectColumns(headers, primeraFila);

    expect(cols.fechaCreaIdx).toBe(-1);
    expect(cols.fechaEgresoIdx).toBe(-1);
    expect(cols.facturaIdx).toBe(-1);
  });

  it("detects CAP-prefixed factura values", () => {
    const headers: string[] = [];
    const primeraFila = [
      "10/05/2026  08:30:00",
      "10/05/2026  10:15:00",
      "CAP123456",
    ];

    const { cols } = autoDetectColumns(headers, primeraFila);

    expect(cols.facturaIdx).toBe(2);
  });

  it("detects Fecha Cierre header variant", () => {
    const headers = ["Fec. Cierre", "N° Factura"];
    const primeraFila = ["10/05/2026", "FEV001"];

    const { cols } = autoDetectColumns(headers, primeraFila);

    expect(cols.fechaCierreIdx).toBe(0);
  });

  it("detects HC Pendiente by value Si/No", () => {
    const headers: string[] = [];
    const primeraFila = [
      "10/05/2026  08:30:00",
      "10/05/2026  10:15:00",
      "FEV416009",
      "Sí",
    ];

    const { cols } = autoDetectColumns(headers, primeraFila);

    expect(cols.hcPendienteIdx).toBe(3);
  });

  it("detects col as paciente when it looks like a full name", () => {
    const headers: string[] = [];
    const primeraFila = [
      "10/05/2026  08:30:00",
      "10/05/2026  10:15:00",
      "FEV416009",
      "Juan Carlos Pérez López",
    ];

    const { cols } = autoDetectColumns(headers, primeraFila);

    expect(cols.pacienteIdx).toBe(3);
  });
});

// ─── calcularResponsable ──────────────────────────────────────────────

describe("calcularResponsable", () => {
  const cronograma: ScheduleDay[] = [
    { dia: 4, manana: "CARLOS", tarde: "ALEJANDRA", noche: "YULIETH" },
    { dia: 5, manana: "CAROLINA", tarde: "CARLOS", noche: "ALEJANDRA" },
  ];

  it("assigns mañana shift for egreso between 06:30 and 12:29", () => {
    const result = calcularResponsable(
      "05/05/2026  08:00:00",
      "05/05/2026  10:15:00",
      cronograma,
    );
    expect(result).toBe("ANGIE ARIAS"); // day 5 manana = CAROLINA → NOMBRE_MAP
  });

  it("assigns tarde shift for egreso between 12:30 and 18:29", () => {
    const result = calcularResponsable(
      "05/05/2026  08:00:00",
      "05/05/2026  14:30:00",
      cronograma,
    );
    expect(result).toBe("CARLOS OMAR"); // day 5 tarde = CARLOS → NOMBRE_MAP
  });

  it("assigns noche shift for egreso between 18:30 and 06:29", () => {
    const result = calcularResponsable(
      "04/05/2026  08:00:00",
      "04/05/2026  22:00:00",
      cronograma,
    );
    expect(result).toBe("DANIELA PAEZ"); // day 4 noche = YULIETH → NOMBRE_MAP
  });

  it("crosses midnight for egreso before 06:30 (previous day noche)", () => {
    // Egreso at 03:00 on day 5 → should look up noche of day 4
    const result = calcularResponsable(
      "04/05/2026  08:00:00",
      "05/05/2026  03:00:00",
      cronograma,
    );
    expect(result).toBe("DANIELA PAEZ"); // day 4 noche = YULIETH → DANIELA PAEZ
  });

  it("returns Sin Egreso when egreso date is null/empty", () => {
    const result = calcularResponsable(
      "05/05/2026  08:00:00",
      "",
      cronograma,
    );
    expect(result).toBe("Sin Egreso");
  });

  it("returns Sin Egreso when egreso is before crea", () => {
    const result = calcularResponsable(
      "05/05/2026  10:00:00",
      "05/05/2026  08:00:00",
      cronograma,
    );
    expect(result).toBe("Sin Egreso");
  });

  it("respects 30-min reception boundary at 06:30 (mañana starts)", () => {
    // 06:30:00 → mañana (>= 6.5)
    const result = calcularResponsable(
      "05/05/2026  06:00:00",
      "05/05/2026  06:30:00",
      cronograma,
    );
    expect(result).toBe("ANGIE ARIAS"); // day 5 manana = CAROLINA → ANGIE ARIAS
  });

  it("respects 30-min reception boundary at 12:29 (mañana ends)", () => {
    // 12:29:00 → mañana (< 12.5)
    const result = calcularResponsable(
      "05/05/2026  06:00:00",
      "05/05/2026  12:29:00",
      cronograma,
    );
    expect(result).toBe("ANGIE ARIAS"); // day 5 manana = CAROLINA → ANGIE ARIAS
  });

  it("respects 30-min reception boundary at 12:30 (tarde starts)", () => {
    // 12:30:00 → tarde (>= 12.5)
    const result = calcularResponsable(
      "05/05/2026  06:00:00",
      "05/05/2026  12:30:00",
      cronograma,
    );
    expect(result).toBe("CARLOS OMAR"); // day 5 tarde = CARLOS → CARLOS OMAR
  });

  it("returns Sin cronograma when cronograma is empty", () => {
    const result = calcularResponsable(
      "05/05/2026  08:00:00",
      "05/05/2026  10:15:00",
      [],
    );
    expect(result).toBe("Sin cronograma");
  });

  it("returns — when fechaCrea is empty", () => {
    const result = calcularResponsable("", "05/05/2026  10:15:00", cronograma);
    expect(result).toBe("—");
  });

  it("returns full name via NOMBRE_MAP mapping", () => {
    const result = calcularResponsable(
      "04/05/2026  08:00:00",
      "04/05/2026  10:15:00",
      cronograma,
    );
    expect(result).toBe("CARLOS OMAR"); // day 4 manana = CARLOS
  });

  it("returns name unmapped when short name is not in NOMBRE_MAP", () => {
    const localCrono: ScheduleDay[] = [
      { dia: 1, manana: "PEPE", tarde: "", noche: "" },
    ];
    const result = calcularResponsable(
      "01/05/2026  08:00:00",
      "01/05/2026  10:15:00",
      localCrono,
    );
    expect(result).toBe("PEPE"); // not in NOMBRE_MAP, returned as-is
  });
});

// ─── getUniqueResponsables ───────────────────────────────────────────

describe("getUniqueResponsables", () => {
  it("returns unique sorted responsables from results", () => {
    const results: FacturaResult[] = [
      { responsable: "Luis" },
      { responsable: "Ana" },
      { responsable: "Carlos" },
      { responsable: "Ana" },
    ] as FacturaResult[];

    const result = getUniqueResponsables(results);

    expect(result).toEqual(["Ana", "Carlos", "Luis"]);
  });

  it("handles null/undefined responsable with — fallback", () => {
    const results: FacturaResult[] = [
      { responsable: "" },
      { responsable: "Ana" },
      { responsable: undefined as unknown as string },
      { responsable: "Luis" },
    ] as FacturaResult[];

    const result = getUniqueResponsables(results);

    // "—" (U+2014) sorts after ASCII letters in JS default .sort()
    expect(result).toEqual(["Ana", "Luis", "—"]);
  });

  it("returns empty array for empty results", () => {
    const result = getUniqueResponsables([]);
    expect(result).toEqual([]);
  });

  it("includes special values like Sin Egreso", () => {
    const results: FacturaResult[] = [
      { responsable: "Sin Egreso" },
      { responsable: "Ana" },
      { responsable: "—" },
    ] as FacturaResult[];

    const result = getUniqueResponsables(results);

    // "—" (U+2014) sorts after ASCII letters in JS default .sort()
    expect(result).toEqual(["Ana", "Sin Egreso", "—"]);
  });
});

// ─── filterResultsByResponsable ─────────────────────────────────────

describe("filterResultsByResponsable", () => {
  const results: FacturaResult[] = [
    { responsable: "Ana" },
    { responsable: "Luis" },
    { responsable: "Ana" },
    { responsable: "Carlos" },
  ] as FacturaResult[];

  it("returns all results when filter is empty string (Todos)", () => {
    const result = filterResultsByResponsable(results, "");
    expect(result).toBe(results);
  });

  it("filters by responsable when filter is active", () => {
    const result = filterResultsByResponsable(results, "Ana");
    expect(result).toHaveLength(2);
    expect(result!.every((r) => r.responsable === "Ana")).toBe(true);
  });

  it("returns empty array when no results match the filter", () => {
    const result = filterResultsByResponsable(results, "Nobody");
    expect(result).toHaveLength(0);
  });

  it("returns null when results is null", () => {
    const result = filterResultsByResponsable(null, "Ana");
    expect(result).toBeNull();
  });
});

// ─── getSinEgresoButtonConfig ─────────────────────────────────────────

describe("getSinEgresoButtonConfig", () => {
  it("returns disabled config when isSinEgreso is true", () => {
    const config = getSinEgresoButtonConfig(true);
    expect(config.disabled).toBe(true);
    expect(config.title).toBe("Sin egreso — no hay responsable asignado");
  });

  it("returns enabled config when isSinEgreso is false", () => {
    const config = getSinEgresoButtonConfig(false);
    expect(config.disabled).toBe(false);
    expect(config.title).toBe("Enviar a Control de Errores");
  });

  it("returns enabled config when isSinEgreso is undefined", () => {
    const config = getSinEgresoButtonConfig(undefined as unknown as boolean);
    expect(config.disabled).toBe(false);
  });
});

// ─── escapeHtml ───────────────────────────────────────────────────────

describe("escapeHtml", () => {
  it("escapes & < > \" '", () => {
    expect(escapeHtml('&<>"\'')).toBe("&amp;&lt;&gt;&quot;&#039;");
  });

  it("handles null and undefined", () => {
    expect(escapeHtml(null)).toBe("");
    expect(escapeHtml(undefined)).toBe("");
  });

  it("returns empty string for empty input", () => {
    expect(escapeHtml("")).toBe("");
  });

  it("passes through safe strings unchanged", () => {
    expect(escapeHtml("hello world")).toBe("hello world");
    expect(escapeHtml("CARLOS OMAR")).toBe("CARLOS OMAR");
  });
});

// ─── masDeDosTurnosMismoResponsable ───────────────────────────────────

describe("masDeDosTurnosMismoResponsable", () => {
  const jun = (day: number, hour: number, min = 0) =>
    new Date(2026, 5, day, hour, min, 0);

  it("returns true when ≥2 shifts of same responsable since egreso (inclusive)", () => {
    // Scenario: egreso day 1 manana=CARLOS, same day tarde also CARLOS → count=2
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "CARLOS", tarde: "CARLOS", noche: "" },
      { dia: 2, manana: "", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2026  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(2, 14, 0),
    );
    expect(result).toBe(true);
  });

  it("returns false when only egreso shift matches (count < 2)", () => {
    // Scenario: only day 1 manana=CARLOS (egreso shift), no other CARLOS slots
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "CARLOS", tarde: "", noche: "" },
      { dia: 2, manana: "", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2026  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(2, 14, 0),
    );
    expect(result).toBe(false);
  });

  it("returns false when current in-progress shift is not counted", () => {
    // Scenario: day 1 manana=CARLOS, day 2 manana=CARLOS; now=day 2 10:00 (manana in progress)
    // If current shift were counted → 2; but current excluded → only 1
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "CARLOS", tarde: "", noche: "" },
      { dia: 2, manana: "CARLOS", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2026  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(2, 10, 0), // day 2 10:00 — manana STILL IN PROGRESS
    );
    expect(result).toBe(false);
  });

  it("returns false when egreso is in a different month", () => {
    // Egreso in May, now in June → month mismatch
    const schedule: ScheduleDay[] = [
      { dia: 25, manana: "CARLOS", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "25/05/2026  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(16, 14, 0),
    );
    expect(result).toBe(false);
  });

  it("returns false when egreso is in a different year", () => {
    // Egreso in 2025, now in 2026 → year mismatch
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "CARLOS", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2025  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(1, 14, 0),
    );
    expect(result).toBe(false);
  });

  it("handles night shift egreso before 06:30 — belongs to previous day noche", () => {
    // Scenario: egreso at 03:00 day 5 → noche of day 4 (CARLOS)
    // day 4 noche=CARLOS, day 5 manana=CARLOS → count=2
    const schedule: ScheduleDay[] = [
      { dia: 4, manana: "", tarde: "", noche: "CARLOS" },
      { dia: 5, manana: "CARLOS", tarde: "CARLOS", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "05/06/2026  03:00:00",
      "CARLOS OMAR",
      schedule,
      jun(5, 18, 30),
    );
    expect(result).toBe(true);
  });

  it("matches responsable name via NOMBRE_MAP reverse mapping", () => {
    // responsable="CARLOS OMAR" → NOMBRE_MAP says CARLOS→CARLOS OMAR
    // revMap["CARLOS OMAR"] = "CARLOS" → matches schedule's "CARLOS"
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "CARLOS", tarde: "CARLOS", noche: "" },
      { dia: 2, manana: "", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2026  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(2, 14, 0),
    );
    expect(result).toBe(true);
  });

  it("matches responsable name not in NOMBRE_MAP as-is", () => {
    // responsable="PEPE" not in NOMBRE_MAP → compared directly
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "PEPE", tarde: "PEPE", noche: "" },
      { dia: 2, manana: "", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2026  10:00:00",
      "PEPE",
      schedule,
      jun(2, 14, 0),
    );
    expect(result).toBe(true);
  });

  it("returns false when responsable has no schedule slots after egreso", () => {
    // Day 1 manana is CARLOS (egreso shift), no other CARLOS slots anywhere
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "CARLOS", tarde: "ALEJANDRA", noche: "YULIETH" },
      { dia: 2, manana: "CAROLINA", tarde: "ALEJANDRA", noche: "YULIETH" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2026  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(3, 14, 0),
    );
    expect(result).toBe(false);
  });

  it("counts egreso shift as shift #1 (inclusive counting)", () => {
    // egreso day 1 manana=CARLOS counts as 1; day 2 manana=CARLOS counts as 2
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "CARLOS", tarde: "", noche: "" },
      { dia: 2, manana: "CARLOS", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2026  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(3, 10, 0),
    );
    expect(result).toBe(true);
  });

  it("stops counting before current in-progress shift at night boundary", () => {
    // egreso day 1 manana=CARLOS; day 1 noche=CARLOS; now=day 2 05:00 (noche of day 1 in progress)
    // Current shift = day 1 noche (now before 06:30 → previous day noche) → excluded
    // Only egreso shift (day 1 manana) counted → count=1
    const schedule: ScheduleDay[] = [
      { dia: 1, manana: "CARLOS", tarde: "", noche: "CARLOS" },
      { dia: 2, manana: "", tarde: "", noche: "" },
    ];
    const result = masDeDosTurnosMismoResponsable(
      "01/06/2026  10:00:00",
      "CARLOS OMAR",
      schedule,
      jun(2, 5, 0), // day 2 at 05:00 → still in day 1's noche shift
    );
    expect(result).toBe(false);
  });
});
