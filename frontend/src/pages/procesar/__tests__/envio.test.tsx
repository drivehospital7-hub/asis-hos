// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { ProcesarPage } from "../page";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// jsdom no implementa scrollIntoView (usado por toggleArea en page.tsx)
Element.prototype.scrollIntoView = vi.fn() as unknown as typeof Element.prototype.scrollIntoView;

function jsonOk(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

interface Row {
  factura: string;
  descripcion?: string;
  regla?: string;
  responsable_cierra?: string;
  tipo_error?: string;
}

function makeRow(factura: string, over: Partial<Row> = {}) {
  return {
    tipo_error: "X",
    factura,
    fec_factura: "2026-01-01",
    responsable_cierra: "R",
    descripcion: "D",
    procedimiento: "P",
    detalle: "DET",
    regla: "R1",
    ...over,
  };
}

function uploadResultFor(rows: ReturnType<typeof makeRow>[]) {
  return {
    errores: [
      {
        tipo_factura: "ODONTO",
        total: rows.length,
        tipos: [
          { tipo: "T1", tipo_key: "t1", cantidad: rows.length, facturas: rows },
        ],
      },
    ],
    total_errores: rows.length,
    tipos_procesados: ["ODONTO"],
  };
}

function routeFetch(preload: unknown[], uploadData: unknown) {
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    const method = (init?.method ?? "GET").toUpperCase();
    if (url === "/api/control-errores" && method === "GET") {
      return jsonOk({ status: "success", data: { errores: preload }, errors: [] });
    }
    if (url === "/procesar/" && method === "POST") {
      return jsonOk({ status: "success", data: uploadData, errors: [] });
    }
    if (url === "/api/control-errores" && method === "POST") {
      return jsonOk({ status: "success", data: {}, errors: [] });
    }
    return jsonOk({ status: "success", data: {}, errors: [] });
  });
}

function postCalls() {
  return fetchMock.mock.calls.filter((call: unknown[]) => {
    const [url, init] = call as [string, RequestInit | undefined];
    return (
      url === "/api/control-errores" &&
      (init?.method ?? "").toUpperCase() === "POST"
    );
  });
}

function getCalls() {
  return fetchMock.mock.calls.filter((call: unknown[]) => {
    const [url, init] = call as [string, RequestInit | undefined];
    return (
      url === "/api/control-errores" &&
      (init?.method ?? "GET").toUpperCase() === "GET"
    );
  });
}

async function uploadAndExpand() {
  const input = document.getElementById("file-upload") as HTMLInputElement;
  const file = new File(["x"], "rep.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  fireEvent.change(input, { target: { files: [file] } });
  fireEvent.click(
    screen.getByRole("button", { name: /procesar archivo/i }),
  );
  await screen.findByText("ODONTO");
  fireEvent.click(screen.getByText("ODONTO").closest("button")!);
}

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(() => {
  cleanup();
  delete (window as unknown as Record<string, unknown>).__showConfirm;
});

describe("envio a control (integration)", () => {
  it("POST nuevo crea registro: fila nueva + → POST exacto → toast + ✓", async () => {
    const confirm = vi.fn(async () => true);
    (window as unknown as Record<string, unknown>).__showConfirm = confirm;
    routeFetch([], uploadResultFor([makeRow("F123")]));
    render(<ProcesarPage can_write canControl />);
    await uploadAndExpand();

    const sendBtn = await screen.findByTitle("Enviar a Control de Errores");
    fireEvent.click(sendBtn);

    await waitFor(() => expect(postCalls().length).toBe(1));
    expect(confirm).toHaveBeenCalledOnce();
    const body = JSON.parse(String(postCalls()[0][1]?.body));
    expect(body).toEqual({
      tipo_error: "Factura Abierta",
      factura: "F123",
      observacion: "D",
      estado: "S",
      responsable: "R",
    });
    expect("validador" in body).toBe(false);
    await screen.findByText('✅ Factura "F123" enviada a Control de Errores');
    await screen.findByTitle("Enviada a Control");
  });

  it("duplicado exige confirm: acepta → POST", async () => {
    const confirm = vi.fn(async () => true);
    (window as unknown as Record<string, unknown>).__showConfirm = confirm;
    routeFetch(
      [{ factura: "F123", tipo_error: "Factura Abierta" }],
      uploadResultFor([makeRow("f123 ")]),
    );
    render(<ProcesarPage can_write canControl />);
    await uploadAndExpand();

    const dupBtn = await screen.findByTitle(
      "Ya está en Control — Click para duplicar",
    );
    fireEvent.click(dupBtn);

    await waitFor(() => expect(postCalls().length).toBe(1));
    expect(confirm).toHaveBeenCalledOnce();
    const body = JSON.parse(String(postCalls()[0][1]?.body));
    expect(body.factura).toBe("f123 ");
    expect(body.tipo_error).toBe("Factura Abierta");
  });

  it("duplicado exige confirm: cancela → sin POST", async () => {
    const confirm = vi.fn(async () => false);
    (window as unknown as Record<string, unknown>).__showConfirm = confirm;
    routeFetch(
      [{ factura: "F123", tipo_error: "Factura Abierta" }],
      uploadResultFor([makeRow("F123")]),
    );
    render(<ProcesarPage can_write canControl />);
    await uploadAndExpand();

    const dupBtn = await screen.findByTitle(
      "Ya está en Control — Click para duplicar",
    );
    fireEvent.click(dupBtn);

    await waitFor(() => expect(confirm).toHaveBeenCalledOnce());
    await new Promise((r) => setTimeout(r, 50));
    expect(postCalls().length).toBe(0);
  });

  it("responsable vacío envía responsable \"\"", async () => {
    const confirm = vi.fn(async () => true);
    (window as unknown as Record<string, unknown>).__showConfirm = confirm;
    routeFetch(
      [],
      uploadResultFor([makeRow("F999", { responsable_cierra: "" })]),
    );
    render(<ProcesarPage can_write canControl />);
    await uploadAndExpand();

    fireEvent.click(await screen.findByTitle("Enviar a Control de Errores"));
    await waitFor(() => expect(postCalls().length).toBe(1));
    const body = JSON.parse(String(postCalls()[0][1]?.body));
    expect(body.responsable).toBe("");
  });

  it("cap: 200 filas → 50 botones, 1 GET preload, 0 fetch por fila", async () => {
    (window as unknown as Record<string, unknown>).__showConfirm = vi.fn(
      async () => true,
    );
    const rows = Array.from({ length: 200 }, (_, i) =>
      makeRow(`F${String(i).padStart(4, "0")}`),
    );
    routeFetch([], uploadResultFor(rows));
    const { container } = render(<ProcesarPage can_write canControl />);
    await uploadAndExpand();

    const envioBtns = container.querySelectorAll('button[title*="Control"]');
    expect(envioBtns.length).toBe(50);
    await screen.findByText("Mostrando 50 de 200 registros");
    expect(getCalls().length).toBe(1);
    expect(
      fetchMock.mock.calls.filter(([u]) => u === "/procesar/").length,
    ).toBe(1);
  });

  it("otro tipo_error avisa pero permite POST", async () => {
    const confirm = vi.fn(async () => true);
    (window as unknown as Record<string, unknown>).__showConfirm = confirm;
    routeFetch(
      [{ factura: "F123", tipo_error: "Otro Tipo" }],
      uploadResultFor([makeRow("F123")]),
    );
    render(<ProcesarPage can_write canControl />);
    await uploadAndExpand();

    const dupBtn = await screen.findByTitle(
      "Ya está en Control — Click para duplicar",
    );
    expect(dupBtn).toBeTruthy();
    fireEvent.click(dupBtn);

    await waitFor(() => expect(postCalls().length).toBe(1));
    const body = JSON.parse(String(postCalls()[0][1]?.body));
    expect(body.tipo_error).toBe("Factura Abierta");
    expect(body.factura).toBe("F123");
  });
});
