import { describe, it, expect } from "vitest";
import {
  buildPrefacturaDoc,
  buildListadoDoc,
  renderTagsPrint,
  escapeHtml,
  PRINT_STYLES,
} from "./print";
import type { Prefactura } from "./examenes";

const PF: Prefactura = {
  id: "pf-1",
  paciente: "Juan Perez",
  cedula: "111",
  facturador: "Angie Chapuel",
  hora: "15/01/2026 08:30",
  items: [
    { cod: "903859", nom: "Potasio", neps: "X", mall: "X", emss: "X" },
    { cod: "903016", nom: "Ferritina", neps: "AUTH", mall: "AUTH", emss: "AUTH" },
    { cod: "906131", nom: "Trypanosoma", neps: "", mall: "", emss: "" },
  ],
};

describe("renderTagsPrint", () => {
  it("renders NEPS/MALLAM/EMSS tags for X and AUTH flags", () => {
    const tags = renderTagsPrint({ cod: "x", nom: "y", neps: "X", mall: "AUTH", emss: "" });
    expect(tags).toContain("NEPS");
    expect(tags).toContain("MALL⚠AUTH");
    expect(tags).not.toContain("EMSS");
  });

  it("falls back to — when no payer flag is set", () => {
    expect(renderTagsPrint({ cod: "x", nom: "y", neps: "", mall: "", emss: "" })).toBe("—");
  });
});

describe("buildPrefacturaDoc (EX-13)", () => {
  const doc = buildPrefacturaDoc(PF, "28 de agosto de 2026");

  it("preserves the source print header: E.S.E. HOSPITAL ORITO + NIT", () => {
    expect(doc).toContain("E.S.E. HOSPITAL ORITO");
    expect(doc).toContain("NIT 846000474-7");
    expect(doc).toContain("Prefactura de Servicios de Laboratorio Clínico");
  });

  it("shows the display fecha, paciente and cédula", () => {
    expect(doc).toContain("28 de agosto de 2026");
    expect(doc).toContain("Juan Perez");
    expect(doc).toContain("111");
  });

  it("renders one table row per item with code and name", () => {
    expect(doc).toContain("903859");
    expect(doc).toContain("Potasio");
    expect(doc).toContain("903016");
    expect(doc).toContain("Ferritina");
  });

  it("keeps the signature and footer (source parity)", () => {
    expect(doc).toContain("Facturador(a): Angie Chapuel");
    expect(doc).toContain("Laboratorio Clínico — E.S.E. Hospital Orito");
    expect(doc).toContain("Hora:");
  });

  it("includes the green header styles used at print time", () => {
    expect(doc).toContain("pdoc-hdr");
    expect(PRINT_STYLES).toContain(".pdoc-hdr{background:#1a4731");
    expect(PRINT_STYLES).toContain("print-color-adjust:exact");
  });
});

describe("buildListadoDoc (EX-13)", () => {
  const other: Prefactura = {
    id: "pf-2",
    paciente: "Maria Lopez",
    cedula: "222",
    facturador: "Cataleya Tapia",
    hora: "28/08/2026 09:00",
    items: [{ cod: "903810", nom: "Calcio", neps: "X", mall: "", emss: "" }],
  };
  const doc = buildListadoDoc([PF, other], "28 de agosto de 2026");

  it("renders ALL prefacturas as sections (not month-filtered)", () => {
    expect(doc).toContain("Juan Perez");
    expect(doc).toContain("Maria Lopez");
  });

  it("keeps page-break-inside:avoid per section", () => {
    const sections = doc.match(/page-break-inside:avoid/g);
    expect(sections).not.toBeNull();
    expect(sections!.length).toBeGreaterThanOrEqual(2);
  });

  it("includes the listado header, NIT and total count", () => {
    expect(doc).toContain("Listado Diario de Prefacturas");
    expect(doc).toContain("NIT: 846000474-7");
    expect(doc).toContain("Total: 2 prefacturas");
  });

  it("maps payer flags to SI/AUTH/— inside sections", () => {
    expect(doc).toContain("SI");
    expect(doc).toContain("AUTH");
    expect(doc).toContain("—");
  });
});

describe("XSS escaping (R1-001)", () => {
  const payload = '<img src=x onerror="alert(1)"><script>alert("xss")</script>';
  const evil: Prefactura = {
    id: "pf-evil",
    paciente: payload,
    cedula: payload,
    facturador: payload,
    hora: payload,
    items: [{ cod: payload, nom: payload, neps: "", mall: "", emss: "" }],
  };

  it("escapeHtml neutralizes the five dangerous characters", () => {
    expect(escapeHtml(`<>&"'`)).toBe("&lt;&gt;&amp;&quot;&#39;");
    expect(escapeHtml(null)).toBe("");
  });

  it("builders render stored payloads as inert literal text", () => {
    for (const doc of [buildPrefacturaDoc(evil, payload), buildListadoDoc([evil], payload)]) {
      expect(doc).not.toContain("<img");
      expect(doc).not.toContain("<script");
      expect(doc).toContain("&lt;img");
      expect(doc).toContain("&lt;script");
      expect(doc).toContain("&quot;");
    }
  });
});