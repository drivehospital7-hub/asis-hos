import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchEps,
  fetchProcSqlite,
  fetchProcPg,
  fetchEpsDisponibles,
  fetchProcedimientosPorEps,
  createEps,
  updateEps,
  deleteEps,
  createProcSqlite,
  updateProcSqlite,
  deleteProcSqlite,
  createProcPg,
  updateProcPg,
  deleteProcPg,
} from "@/lib/api-catalogo";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

function okResponse(data: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify({ status: "success", data, errors: [] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

// ─── GET/READ endpoints ───────────────────────────────────────────────

describe("fetchEps", () => {
  it("returns EpsContratado list on success", async () => {
    const epsList = [
      { id: 1, cod_contrato: "EPS001", eps: "EMSSANAR", regimen: "SUBSIDIADO" },
    ];
    mockFetch.mockResolvedValue(okResponse({ epsList }));

    const result = await fetchEps();
    expect(result).toEqual({ epsList });
    expect(mockFetch).toHaveBeenCalledWith("/api/eps");
  });

  it("throws on error response", async () => {
    mockFetch.mockResolvedValue(
      Promise.resolve(
        new Response(JSON.stringify({ status: "error", data: {}, errors: ["DB error"] }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(fetchEps()).rejects.toThrow("DB error");
  });
});

describe("fetchProcSqlite", () => {
  it("fetches procedimientos from SQLite", async () => {
    const items = [{ id: 1, cups: "890201", procedimiento: "EXODONIA" }];
    mockFetch.mockResolvedValue(okResponse(items));

    const result = await fetchProcSqlite();
    expect(result).toEqual(items);
    expect(mockFetch).toHaveBeenCalledWith("/api/procedimientos");
  });
});

describe("fetchProcPg", () => {
  it("fetches procedimientos from PostgreSQL by EPS", async () => {
    const items = [{ id: "1", eps: "EMSSANAR", codigo_cups: "890201", descripcion: "EXODONIA", tarifa: 45000 }];
    mockFetch.mockResolvedValue(okResponse(items));

    const result = await fetchProcPg("EMSSANAR");
    expect(result).toEqual(items);
    expect(mockFetch).toHaveBeenCalledWith("/procedimientos?eps=EMSSANAR&all=true");
  });
});

describe("fetchEpsDisponibles", () => {
  it("fetches available EPS list", async () => {
    mockFetch.mockResolvedValue(okResponse({ eps_disponibles: ["EMSSANAR", "MALLAMAS"] }));
    const result = await fetchEpsDisponibles();
    expect(result).toEqual(["EMSSANAR", "MALLAMAS"]);
    expect(mockFetch).toHaveBeenCalledWith("/procedimientos/eps");
  });
});

describe("fetchProcedimientosPorEps", () => {
  it("fetches relationship chain for given EPS id", async () => {
    const chainData = {
      eps: { id: 1, cod_contrato: "EPS001", eps: "EMSSANAR", regimen: "SUBSIDIADO" },
      procedimientos: [
        { eps_nota_id: 1, nota_hoja: "FACTURA", cups: "890201", procedimiento: "EXODONIA", tarifa: 45000 },
      ],
    };
    mockFetch.mockResolvedValue(okResponse(chainData));

    const result = await fetchProcedimientosPorEps(1);
    expect(result).toEqual(chainData);
    expect(mockFetch).toHaveBeenCalledWith("/api/eps/1/procedimientos");
  });

  it("throws on 404", async () => {
    mockFetch.mockResolvedValue(
      Promise.resolve(
        new Response(
          JSON.stringify({ status: "error", data: {}, errors: ["No existe EPS con id: 999"] }),
          { status: 404, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    await expect(fetchProcedimientosPorEps(999)).rejects.toThrow("No existe EPS");
  });
});

// ─── POST/CREATE endpoints ────────────────────────────────────────────

describe("createEps", () => {
  it("posts new EPS and returns created item", async () => {
    const created = { id: 2, cod_contrato: "EPS002", eps: "NUEVA EPS", regimen: "CONTRIBUTIVO" };
    mockFetch.mockResolvedValue(
      Promise.resolve(
        new Response(JSON.stringify({ status: "success", data: created, errors: [] }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const result = await createEps({ cod_contrato: "EPS002", eps: "NUEVA EPS", regimen: "CONTRIBUTIVO" });
    expect(result).toEqual(created);
    expect(mockFetch).toHaveBeenCalledWith("/api/eps", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cod_contrato: "EPS002", eps: "NUEVA EPS", regimen: "CONTRIBUTIVO" }),
    });
  });
});

describe("createProcSqlite", () => {
  it("posts new procedimiento to SQLite", async () => {
    const created = { id: 10, cups: "999999", procedimiento: "NUEVO PROC" };
    mockFetch.mockResolvedValue(
      Promise.resolve(
        new Response(JSON.stringify({ status: "success", data: created, errors: [] }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const result = await createProcSqlite({ cups: "999999", procedimiento: "NUEVO PROC" });
    expect(result).toEqual(created);
    expect(mockFetch).toHaveBeenCalledWith("/api/procedimientos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cups: "999999", procedimiento: "NUEVO PROC" }),
    });
  });
});

describe("createProcPg", () => {
  it("posts new procedimiento to PostgreSQL", async () => {
    const created = { id: "5", eps: "MALLAMAS", codigo_cups: "890201", descripcion: "EXODONIA", tarifa: 50000 };
    mockFetch.mockResolvedValue(
      Promise.resolve(
        new Response(JSON.stringify({ status: "success", data: created, errors: [] }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const result = await createProcPg({ eps: "MALLAMAS", codigo_cups: "890201", descripcion: "EXODONIA", tarifa: 50000 });
    expect(result).toEqual(created);
    expect(mockFetch).toHaveBeenCalledWith("/procedimientos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ eps: "MALLAMAS", codigo_cups: "890201", descripcion: "EXODONIA", tarifa: 50000 }),
    });
  });
});

// ─── PUT/UPDATE endpoints ─────────────────────────────────────────────

describe("updateEps", () => {
  it("updates EPS by id", async () => {
    const updated = { id: 1, cod_contrato: "EPS001", eps: "UPDATED", regimen: "SUBSIDIADO" };
    mockFetch.mockResolvedValue(okResponse(updated));
    const result = await updateEps(1, { eps: "UPDATED" });
    expect(result).toEqual(updated);
    expect(mockFetch).toHaveBeenCalledWith("/api/eps/1", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ eps: "UPDATED" }),
    });
  });
});

describe("updateProcSqlite", () => {
  it("updates procedimiento in SQLite", async () => {
    mockFetch.mockResolvedValue(okResponse({ id: 1, cups: "890201", procedimiento: "CHANGED" }));
    const result = await updateProcSqlite(1, { procedimiento: "CHANGED" });
    expect(result).toEqual({ id: 1, cups: "890201", procedimiento: "CHANGED" });
    expect(mockFetch).toHaveBeenCalledWith("/api/procedimientos/1", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ procedimiento: "CHANGED" }),
    });
  });
});

describe("updateProcPg", () => {
  it("updates procedimiento in PostgreSQL", async () => {
    mockFetch.mockResolvedValue(okResponse({ message: "Actualizado" }));
    const result = await updateProcPg(5, { tarifa: 55000 });
    expect(result).toEqual({ message: "Actualizado" });
    expect(mockFetch).toHaveBeenCalledWith("/procedimientos/5", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tarifa: 55000 }),
    });
  });
});

// ─── DELETE endpoints ─────────────────────────────────────────────────

describe("deleteEps", () => {
  it("deletes EPS by id", async () => {
    mockFetch.mockResolvedValue(okResponse({}));
    await deleteEps(1);
    expect(mockFetch).toHaveBeenCalledWith("/api/eps/1", { method: "DELETE" });
  });
});

describe("deleteProcSqlite", () => {
  it("deletes procedimiento in SQLite", async () => {
    mockFetch.mockResolvedValue(okResponse({}));
    await deleteProcSqlite(10);
    expect(mockFetch).toHaveBeenCalledWith("/api/procedimientos/10", { method: "DELETE" });
  });
});

describe("deleteProcPg", () => {
  it("deletes procedimiento in PostgreSQL", async () => {
    mockFetch.mockResolvedValue(okResponse({}));
    await deleteProcPg(5);
    expect(mockFetch).toHaveBeenCalledWith("/procedimientos/5", { method: "DELETE" });
  });
});
