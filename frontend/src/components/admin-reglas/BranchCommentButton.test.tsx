import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AtomicNode } from "./AtomicNode";
import { BranchCommentButton } from "./BranchCommentButton";

const baseNode = {
  id: 11,
  regla_id: 1,
  padre_id: null,
  tipo: "atomic",
  operador: "eq",
  fuente_datos: "invoice.codigo",
  valor_esperado: "X",
  orden: 0,
};

describe("BranchCommentButton", () => {
  it("ghost style without memo, amber style with memo", () => {
    const plain = renderToStaticMarkup(
      <BranchCommentButton comentario={null} onSave={vi.fn()} />,
    );
    expect(plain).toContain('title="Agregar memo');
    expect(plain).not.toContain("bg-amber-400");

    const withMemo = renderToStaticMarkup(
      <BranchCommentButton comentario="revisar este caso" onSave={vi.fn()} />,
    );
    expect(withMemo).toContain("bg-amber-400");
    expect(withMemo).toContain("Memo: revisar este caso");
  });
});

describe("AtomicNode branch memo button", () => {
  it("shows the memo button only on branches", () => {
    const branch = renderToStaticMarkup(
      <AtomicNode node={{ ...baseNode }} branchLabel="Rama 2" onUpdate={vi.fn()} onRemove={vi.fn()} />,
    );
    // "+" button present (lucide Plus svg)
    expect(branch).toContain("<svg");

    const inner = renderToStaticMarkup(
      <AtomicNode node={{ ...baseNode, comentario: "hola" }} onUpdate={vi.fn()} onRemove={vi.fn()} />,
    );
    // no branch => no memo button (only operator/value svg-less markup)
    expect(inner).not.toContain("Memo");
  });
});
