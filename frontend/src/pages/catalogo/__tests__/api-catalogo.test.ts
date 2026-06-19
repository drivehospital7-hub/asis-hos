import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchEps,
  fetchProcSqlite,
  fetchProcedimientosPorEps,
  createEps,
  updateEps,
  deleteEps,
  createProcSqlite,
  updateProcSqlite,
  deleteProcSqlite,
  fetchNotasHoja,
  createNotaHoja,
  updateNotaHoja,
  deleteNotaHoja,
  vincularProcedimiento,
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

// ─── NotaHoja endpoints (SQLite CRUD) ──────────────────────────────────

describe("fetchNotasHoja", () => {
  it("fetches NotaHoja list from SQLite", async () => {
    const items = [
      { id: 1, nota: "FACTURA URGENCIAS" },
      { id: 2, nota: "FACTURA ODONTOLOGIA" },
    ];
    mockFetch.mockResolvedValue(okResponse(items));

    const result = await fetchNotasHoja();
    expect(result).toEqual(items);
    expect(mockFetch).toHaveBeenCalledWith("/api/notas-hoja");
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
    await expect(fetchNotasHoja()).rejects.toThrow("DB error");
  });
});

describe("createNotaHoja", () => {
  it("posts new NotaHoja and returns created item", async () => {
    const created = { id: 10, nota: "NUEVA NOTA" };
    mockFetch.mockResolvedValue(
      Promise.resolve(
        new Response(JSON.stringify({ status: "success", data: created, errors: [] }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const result = await createNotaHoja({ nota: "NUEVA NOTA" });
    expect(result).toEqual(created);
    expect(mockFetch).toHaveBeenCalledWith("/api/notas-hoja", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nota: "NUEVA NOTA" }),
    });
  });
});

describe("updateNotaHoja", () => {
  it("updates NotaHoja by id", async () => {
    const updated = { id: 1, nota: "UPDATED NOTA" };
    mockFetch.mockResolvedValue(okResponse(updated));

    const result = await updateNotaHoja(1, { nota: "UPDATED NOTA" });
    expect(result).toEqual(updated);
    expect(mockFetch).toHaveBeenCalledWith("/api/notas-hoja/1", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nota: "UPDATED NOTA" }),
    });
  });
});

describe("deleteNotaHoja", () => {
  it("deletes NotaHoja by id", async () => {
    mockFetch.mockResolvedValue(okResponse({}));
    await deleteNotaHoja(10);
    expect(mockFetch).toHaveBeenCalledWith("/api/notas-hoja/10", { method: "DELETE" });
  });
});

// ─── Vincular Procedimiento ─────────────────────────────────────────────

describe("vincularProcedimiento", () => {
  it("POST to vincular endpoint with correct body", async () => {
    const response = {
      eps_nota: { id: 1, id_nota_hoja: 5, id_eps_contratado: 3 },
      notas_tecnicas: { id: 1, id_procedimiento: 10, id_nota_hoja: 5, tarifa: 45000 },
    };
    mockFetch.mockResolvedValue(okResponse(response));

    const body = { id_nota_hoja: 5, id_procedimiento: 10, tarifa: 45000 };
    const result = await vincularProcedimiento(3, body);
    expect(result).toEqual(response);
    expect(mockFetch).toHaveBeenCalledWith("/api/eps/3/vincular-procedimiento", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  });

  it("throws on server error", async () => {
    mockFetch.mockResolvedValue(
      Promise.resolve(
        new Response(JSON.stringify({ status: "error", data: {}, errors: ["Combinación ya existe"] }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(vincularProcedimiento(1, { id_nota_hoja: 5, id_procedimiento: 10, tarifa: 45000 }))
      .rejects.toThrow("Combinación ya existe");
  });
});
