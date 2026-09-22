import { describe, it, expect } from "vitest";
import {
  norm,
  buildObservacion,
  buildEnvioSet,
  getEnvioEstado,
  hasControlWrite,
  canShowEnvio,
} from "../utils";

// ─── norm ───────────────────────────────────────────────────────────────

describe("norm", () => {
  it("uppercases and trims factura", () => {
    expect(norm("f123 ")).toBe("F123");
  });

  it("trims leading spaces and uppercases", () => {
    expect(norm("  FEV416009  ")).toBe("FEV416009");
  });

  it("returns empty string for empty input", () => {
    expect(norm("")).toBe("");
    expect(norm("   ")).toBe("");
  });

  it("handles null/undefined as empty string", () => {
    expect(norm(null as unknown as string)).toBe("");
    expect(norm(undefined as unknown as string)).toBe("");
  });
});

// ─── buildObservacion ───────────────────────────────────────────────────

describe("buildObservacion", () => {
  it("returns trimmed descripcion", () => {
    expect(buildObservacion("  D  ")).toBe("D");
  });

  it("ignores detalle", () => {
    expect(buildObservacion("D", "DET")).toBe("D");
  });

  it("truncates to 500 chars", () => {
    const long = "x".repeat(600);
    expect(buildObservacion(long).length).toBe(500);
  });

  it("returns empty string for empty descripcion", () => {
    expect(buildObservacion("")).toBe("");
    expect(buildObservacion("   ")).toBe("");
  });
});

// ─── buildEnvioSet ──────────────────────────────────────────────────────

describe("buildEnvioSet", () => {
  it("builds normalized Set from errores of any tipo_error", () => {
    const set = buildEnvioSet([
      { factura: "f123 ", tipo_error: "Otros" },
      { factura: "FEV1", tipo_error: "Otro Tipo" },
    ]);
    expect(set.has("F123")).toBe(true);
    expect(set.has("FEV1")).toBe(true);
  });

  it("matches fila F123 against reporte f123 (no false negative)", () => {
    const set = buildEnvioSet([{ factura: "f123 " }]);
    expect(set.has(norm("F123"))).toBe(true);
  });

  it("skips entries without factura", () => {
    const set = buildEnvioSet([
      { factura: "" },
      { factura: "   " },
      {},
    ]);
    expect(set.size).toBe(0);
  });

  it("returns empty Set for empty/null input", () => {
    expect(buildEnvioSet([]).size).toBe(0);
    expect(buildEnvioSet(null as unknown as []).size).toBe(0);
    expect(buildEnvioSet(undefined as unknown as []).size).toBe(0);
  });
});

// ─── getEnvioEstado ─────────────────────────────────────────────────────

describe("getEnvioEstado", () => {
  it("returns duplicada (⚠) when in Set even if _enviada is true", () => {
    expect(getEnvioEstado("F123", true, new Set(["F123"]))).toBe("duplicada");
  });

  it("returns duplicada (⚠) when normalized factura is in Set", () => {
    expect(getEnvioEstado("f123 ", false, new Set(["F123"]))).toBe(
      "duplicada",
    );
  });

  it("returns nueva (+) when not sent and not in Set", () => {
    expect(getEnvioEstado("F999", false, new Set(["F123"]))).toBe("nueva");
  });

  it("returns nueva (+) when Set is empty", () => {
    expect(getEnvioEstado("F999", false, new Set())).toBe("nueva");
  });
});

// ─── hasControlWrite / canShowEnvio ─────────────────────────────────────

describe("hasControlWrite", () => {
  it("returns true when permisos include control_urgencias:write", () => {
    expect(hasControlWrite(["procesar:write", "control_urgencias:write"])).toBe(
      true,
    );
  });

  it("returns true when permisos include wildcard *", () => {
    expect(hasControlWrite(["*"])).toBe(true);
  });

  it("returns false when only base control_urgencias without :write", () => {
    expect(hasControlWrite(["control_urgencias"])).toBe(false);
  });

  it("returns false for empty/null permisos", () => {
    expect(hasControlWrite([])).toBe(false);
    expect(hasControlWrite(null as unknown as string[])).toBe(false);
    expect(hasControlWrite(undefined as unknown as string[])).toBe(false);
  });
});

describe("canShowEnvio", () => {
  it("requires both can_write and canControl", () => {
    expect(canShowEnvio(true, true)).toBe(true);
    expect(canShowEnvio(true, false)).toBe(false);
    expect(canShowEnvio(false, true)).toBe(false);
    expect(canShowEnvio(false, false)).toBe(false);
  });
});
