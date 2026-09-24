// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import {
  AdminReglasPage,
  DominiosBadges,
  DominioScopeEditor,
  buildDominiosPayload,
  getRuleDominios,
  ruleMatchesDominio,
} from "./page";
import type { Regla } from "@/lib/api-reglas";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function makeRegla(over: Partial<Regla> = {}): Regla {
  return {
    id: 75,
    rule_base_id: null,
    nombre: "profesional_urg_trabajadora_social",
    descripcion: null,
    dominio: "urgencias",
    dominios: ["urgencias"],
    estado: "active",
    version: 1,
    prioridad: 50,
    severidad: "error",
    activo: true,
    grupo_error: null,
    detalle_a_campo: null,
    detalle_b_campo: null,
    descripcion_template: null,
    parametros: null,
    parametros_default: null,
    creado_en: null,
    actualizado_en: null,
    cambio_que: null,
    cambio_por_que: null,
    cambio_responsable: null,
    ...over,
  };
}

function jsonOk(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function stubFetchReglas(items: Regla[]) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    calls.push({ url, init });
    return jsonOk({ status: "success", data: items, errors: [] });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

// ─── Pure scope helpers ─────────────────────────────────────────────

describe("getRuleDominios", () => {
  it("returns the stored scope as-is", () => {
    expect(getRuleDominios(makeRegla({ dominios: ["urgencias", "hospitalizacion"] }))).toEqual([
      "urgencias",
      "hospitalizacion",
    ]);
  });

  it("falls back to the legacy dominio mirror, then to []", () => {
    expect(getRuleDominios(makeRegla({ dominios: undefined, dominio: "odontologia" }))).toEqual([
      "odontologia",
    ]);
    expect(getRuleDominios({ dominios: undefined, dominio: null })).toEqual([]);
  });
});

describe("buildDominiosPayload", () => {
  it("sends the sorted array plus the legacy mirror", () => {
    expect(buildDominiosPayload(["urgencias", "hospitalizacion"])).toEqual({
      dominios: ["hospitalizacion", "urgencias"],
      dominio: "hospitalizacion",
    });
  });
});

describe("ruleMatchesDominio", () => {
  const multi = makeRegla({ dominios: ["urgencias", "hospitalizacion"] });
  const odonto = makeRegla({ dominios: ["odontologia"] });
  const transversal = makeRegla({ dominios: ["transversal"] });

  it("matches any scoped dominio (∈ semantics)", () => {
    expect(ruleMatchesDominio(multi, "hospitalizacion")).toBe(true);
    expect(ruleMatchesDominio(multi, "urgencias")).toBe(true);
    expect(ruleMatchesDominio(odonto, "hospitalizacion")).toBe(false);
  });

  it("keeps transversal rules visible under every filter", () => {
    for (const f of ["urgencias", "hospitalizacion", "odontologia", "farmacia"]) {
      expect(ruleMatchesDominio(transversal, f)).toBe(true);
    }
  });

  it("matches everything without a filter", () => {
    expect(ruleMatchesDominio(odonto, "")).toBe(true);
  });
});

// ─── Badges + editor ────────────────────────────────────────────────

describe("DominiosBadges", () => {
  it("renders one badge per scoped dominio", () => {
    const { container } = render(<DominiosBadges dominios={["urgencias", "hospitalizacion"]} />);
    expect(container.textContent).toContain("urgencias");
    expect(container.textContent).toContain("hospitalizacion");
    expect(container.querySelectorAll("span > span").length).toBe(2);
  });

  it("renders unknown stored values as-is instead of hiding them", () => {
    const { container } = render(<DominiosBadges dominios={["odontologia", "dominio_viejo"]} />);
    expect(container.textContent).toContain("dominio_viejo");
  });
});

describe("DominioScopeEditor", () => {
  it("renders unknown stored values as checked custom badges", () => {
    const onChange = vi.fn();
    render(<DominioScopeEditor selected={["odontologia", "dominio_viejo"]} onChange={onChange} />);
    const custom = screen.getByLabelText("Dominio personalizado dominio_viejo") as HTMLInputElement;
    expect(custom.checked).toBe(true);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("toggles a known dominio into the selection", () => {
    const onChange = vi.fn();
    render(<DominioScopeEditor selected={["urgencias"]} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("Dominio hospitalizacion"));
    expect(onChange).toHaveBeenCalledWith(["urgencias", "hospitalizacion"]);
  });
});

// ─── List view integration ──────────────────────────────────────────

describe("RulesListView multi-dominio", () => {
  it("shows stacked badges for every scoped dominio", async () => {
    stubFetchReglas([makeRegla({ id: 75, dominios: ["urgencias", "hospitalizacion"] })]);
    render(<AdminReglasPage />);
    await waitFor(() => expect(screen.getByText("profesional_urg_trabajadora_social")).toBeTruthy());
    expect(screen.getAllByText("urgencias").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("hospitalizacion").length).toBeGreaterThanOrEqual(1);
  });

  it("sends dominios array on create and blocks empty scope client-side", async () => {
    const calls = stubFetchReglas([]);
    render(<AdminReglasPage />);
    await waitFor(() => expect(screen.getByText("Nueva Regla")).toBeTruthy());

    fireEvent.click(screen.getByText("Nueva Regla"));
    const modal = document.querySelector("div.fixed.inset-0");
    expect(modal).toBeTruthy();
    const nombre = modal!.querySelector('input[type="text"]') as HTMLInputElement;
    fireEvent.change(nombre, { target: { value: "r-nueva" } });
    // odontologia is checked by default; add hospitalizacion
    fireEvent.click(screen.getByLabelText("Dominio hospitalizacion"));
    fireEvent.submit(modal!.querySelector("form")!);

    await waitFor(() => {
      const post = calls.find((c) => c.init?.method === "POST");
      expect(post).toBeTruthy();
    });
    const post = calls.find((c) => c.init?.method === "POST")!;
    expect(JSON.parse(post.init!.body as string)).toMatchObject({
      nombre: "r-nueva",
      dominios: ["hospitalizacion", "odontologia"],
    });
  });

  it("blocks save with an empty scope without calling the API", async () => {
    const calls = stubFetchReglas([]);
    render(<AdminReglasPage />);
    await waitFor(() => expect(screen.getByText("Nueva Regla")).toBeTruthy());

    fireEvent.click(screen.getByText("Nueva Regla"));
    const modal = document.querySelector("div.fixed.inset-0")!;
    fireEvent.change(modal.querySelector('input[type="text"]')!, { target: { value: "r-vacia" } });
    // uncheck the default odontologia → empty scope
    fireEvent.click(screen.getByLabelText("Dominio odontologia"));
    fireEvent.submit(modal.querySelector("form")!);

    await waitFor(() =>
      expect(screen.getByText("Seleccioná al menos un dominio")).toBeTruthy(),
    );
    expect(calls.some((c) => c.init?.method === "POST")).toBe(false);
  });

  it("keeps the single-select filter UI and forwards it to the server", async () => {
    const calls = stubFetchReglas([]);
    const { container } = render(<AdminReglasPage />);
    await waitFor(() => expect(screen.getByText("Nueva Regla")).toBeTruthy());

    const dominioFilter = container.querySelectorAll("select")[0];
    fireEvent.change(dominioFilter, { target: { value: "hospitalizacion" } });

    await waitFor(() => {
      expect(calls.some((c) => c.url.includes("dominio=hospitalizacion"))).toBe(true);
    });
  });
});
