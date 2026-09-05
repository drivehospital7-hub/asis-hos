import { describe, it, expect } from "vitest";
import { filenameFromDisposition } from "./download";

describe("filenameFromDisposition (D9)", () => {
  it("parses a plain ASCII filename=", () => {
    expect(
      filenameFromDisposition(
        'attachment; filename=Listado_Lab_HospitalOrito_2026-08-01_2026-08-31.xlsx',
      ),
    ).toBe("Listado_Lab_HospitalOrito_2026-08-01_2026-08-31.xlsx");
  });

  it("parses a quoted filename=", () => {
    expect(filenameFromDisposition('attachment; filename="Listado.xlsx"')).toBe(
      "Listado.xlsx",
    );
  });

  it("returns null when the header is absent or has no filename", () => {
    expect(filenameFromDisposition(null)).toBeNull();
    expect(filenameFromDisposition("attachment")).toBeNull();
    expect(filenameFromDisposition("")).toBeNull();
  });
});