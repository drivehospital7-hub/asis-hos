import { describe, expect, it } from "vitest";
import { serializeTree, treeReducer, validateConditionTree } from "./ConditionTreeEditor";

describe("condition tree reverse nodes", () => {
  it("accepts a NOT node with exactly one nested condition", () => {
    const tree = [{
      id: 1,
      regla_id: 1,
      padre_id: null,
      tipo: "composite",
      operador: "NOT",
      fuente_datos: null,
      valor_esperado: null,
      orden: 0,
      condiciones: [{
        id: 2,
        regla_id: 1,
        padre_id: 1,
        tipo: "atomic",
        operador: "eq",
        fuente_datos: "invoice.centro_costo",
        valor_esperado: "TRASLADOS",
        orden: 0,
      }],
    }];

    expect(validateConditionTree(tree)).toBeNull();
    expect(serializeTree(tree)).toEqual(tree);
  });

  it("rejects a NOT node with zero or multiple children", () => {
    const base = {
      id: 1,
      regla_id: 1,
      padre_id: null,
      tipo: "composite",
      operador: "NOT",
      fuente_datos: null,
      valor_esperado: null,
      orden: 0,
    };

    expect(validateConditionTree([{ ...base, condiciones: [] }])).toMatch(
      /exactly one child/,
    );
    expect(validateConditionTree([
      { ...base, condiciones: [{ ...base, id: 2 }, { ...base, id: 3 }] },
    ])).toMatch(/exactly one child/);
  });
});

describe("condition tree insertion", () => {
  it("inserts atomic and composite children into the selected nested composite", () => {
    const tree = [{
      id: 1,
      regla_id: 1,
      padre_id: null,
      tipo: "composite",
      operador: "AND",
      fuente_datos: null,
      valor_esperado: null,
      orden: 0,
      condiciones: [{
        id: 2,
        regla_id: 1,
        padre_id: 1,
        tipo: "composite",
        operador: "AND",
        fuente_datos: null,
        valor_esperado: null,
        orden: 0,
        condiciones: [],
      }],
    }];

    const withAtomic = treeReducer(tree, {
      type: "ADD_CHILD",
      payload: { parentId: 2, tipo: "atomic" },
    });
    const withComposite = treeReducer(withAtomic, {
      type: "ADD_CHILD",
      payload: { parentId: 2, tipo: "composite" },
    });

    expect(withComposite[0].condiciones).toHaveLength(1);
    expect(withComposite[0].condiciones?.[0].condiciones).toHaveLength(2);
    expect(withComposite[0].condiciones?.[0].condiciones?.[0].tipo).toBe("atomic");
    expect(withComposite[0].condiciones?.[0].condiciones?.[1].tipo).toBe("composite");
  });
});
