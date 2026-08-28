import { describe, it, expect } from "vitest";
import { CSV_HEADERS, buildCsv, csvLabelFor, tcCsv } from "./csv";
import type { Prefactura } from "./examenes";

const LISTADO: Prefactura[] = [
  {
    id: "pf-1",
    paciente: "Juan Perez",
    cedula: "111",
    facturador: "Angie Chapuel",
    hora: "15/01/2026 08:30",
    items: [
      { cod: "903859", nom: "Potasio", neps: "X", mall: "X", emss: "X" },
      { cod: "903016", nom: "Ferritina", neps: "AUTH", mall: "AUTH", emss: "AUTH" },
    ],
  },
  {
    id: "pf-2",
    paciente: "Maria Lopez",
    cedula: "222",
    facturador: "Cataleya Tapia",
    hora: "28/08/2026 09:00",
    items: [{ cod: "906131", nom: "Trypanosoma", neps: "", mall: "", emss: "" }],
  },
];

describe("CSV_HEADERS", () => {
  it("has the exact EX-14 header", () => {
    expect(CSV_HEADERS).toEqual([
      "N°",
      "Paciente",
      "Cedula",
      "Codigo",
      "Examen",
      "NEPS",
      "MALLAM",
      "EMSS",
      "Facturador",
      "Fecha/Hora",
    ]);
  });
});

describe("tcCsv", () => {
  it("maps X→SI, AUTH→AUTH, anything else→empty (EX-14)", () => {
    expect(tcCsv("X")).toBe("SI");
    expect(tcCsv("AUTH")).toBe("AUTH");
    expect(tcCsv("")).toBe("");
    expect(tcCsv(undefined)).toBe("");
    expect(tcCsv(null)).toBe("");
  });
});

describe("csvLabelFor", () => {
  it("uses Todos_los_meses when no month is selected", () => {
    expect(csvLabelFor(null)).toBe("Todos_los_meses");
  });

  it("sanitizes the month label into filename-safe tokens", () => {
    expect(csvLabelFor("Enero de 2026")).toBe("Enero_de_2026");
    expect(csvLabelFor("Agosto de 2026")).toBe("Agosto_de_2026");
    expect(csvLabelFor("Fecha no disponible")).toBe("Fecha_no_disponible");
  });

  it("strips leading/trailing separators from sanitization", () => {
    expect(csvLabelFor("  Mes  2026 ")).toBe("Mes_2026");
  });
});

describe("buildCsv", () => {
  it("prepends the BOM so Excel renders accents (EX-14)", () => {
    const { csv } = buildCsv(LISTADO, null);
    expect(csv.charCodeAt(0)).toBe(0xfeff);
  });

  it("emits the exact header line first (after BOM)", () => {
    const { csv } = buildCsv(LISTADO, null);
    const body = csv.slice(1);
    expect(body.startsWith("N°,Paciente,Cedula,Codigo,Examen,NEPS,MALLAM,EMSS,Facturador,Fecha/Hora\n")).toBe(true);
  });

  it("emits one row per item with sequential numbering", () => {
    const { csv } = buildCsv(LISTADO, null);
    const lines = csv.slice(1).trimEnd().split("\n");
    // header + 3 items
    expect(lines).toHaveLength(4);
    expect(lines[1]).toBe('1,"Juan Perez","111","903859","Potasio","SI","SI","SI","Angie Chapuel","15/01/2026 08:30"');
    expect(lines[2]).toBe('2,"Juan Perez","111","903016","Ferritina","AUTH","AUTH","AUTH","Angie Chapuel","15/01/2026 08:30"');
    expect(lines[3]).toBe('3,"Maria Lopez","222","906131","Trypanosoma","","","","Cataleya Tapia","28/08/2026 09:00"');
  });

  it("maps X→SI, AUTH→AUTH and leaves empties blank", () => {
    const { csv } = buildCsv(LISTADO, null);
    expect(csv).toContain('"SI","SI","SI"');
    expect(csv).toContain('"AUTH","AUTH","AUTH"');
    expect(csv).toContain('"","",""');
  });

  it("exports ONLY the records passed (filtered view) (EX-14)", () => {
    const filtered = LISTADO.slice(1);
    const { csv } = buildCsv(filtered, "Agosto de 2026");
    const lines = csv.slice(1).trimEnd().split("\n");
    expect(lines).toHaveLength(2);
    expect(lines[1]).toContain("Maria Lopez");
    expect(csv).not.toContain("Juan Perez");
  });

  it("builds the month-scoped filename", () => {
    const { filename } = buildCsv(LISTADO, "Agosto de 2026");
    expect(filename).toBe("Listado_Lab_HospitalOrito_Agosto_de_2026.csv");
    const all = buildCsv(LISTADO, null);
    expect(all.filename).toBe("Listado_Lab_HospitalOrito_Todos_los_meses.csv");
  });

  it("returns header-only csv for an empty filtered listado", () => {
    const { csv } = buildCsv([], null);
    expect(csv).toBe("\uFEFFN°,Paciente,Cedula,Codigo,Examen,NEPS,MALLAM,EMSS,Facturador,Fecha/Hora\n");
  });
});