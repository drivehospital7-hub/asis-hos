// @vitest-environment jsdom
/** RED tests for useMoveFacturas (monitoreo-mover-facturas).
 *
 * Strict TDD: hook does not exist yet — this suite MUST fail
 * (import error) until the GREEN phase.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";

import {
  buildMoveToast,
  toggleAllPathsFiltered,
  togglePathInSelection,
  useMoveFacturas,
} from "../../hooks/useMoveFacturas";

describe("togglePathInSelection", () => {
  it("adds a missing path", () => {
    expect(togglePathInSelection(["/a/FEV1"], "/a/FEV2")).toEqual([
      "/a/FEV1",
      "/a/FEV2",
    ]);
  });

  it("removes a present path", () => {
    expect(togglePathInSelection(["/a/FEV1", "/a/FEV2"], "/a/FEV1")).toEqual([
      "/a/FEV2",
    ]);
  });
});

describe("toggleAllPathsFiltered", () => {
  it("selects only the visible paths keeping prior selection", () => {
    expect(toggleAllPathsFiltered(["/x/OLD"], ["/a/F1", "/a/F2"])).toEqual([
      "/x/OLD",
      "/a/F1",
      "/a/F2",
    ]);
  });

  it("deselects only the visible paths when all visible selected", () => {
    expect(
      toggleAllPathsFiltered(["/x/OLD", "/a/F1", "/a/F2"], ["/a/F1", "/a/F2"]),
    ).toEqual(["/x/OLD"]);
  });
});

describe("buildMoveToast", () => {
  it("formats counts and failed names", () => {
    expect(
      buildMoveToast(["/d/F1"], [{ src: "/s/F2", error: "boom" }]),
    ).toBe("Moved 1, failed 1: /s/F2");
  });

  it("formats a clean move", () => {
    expect(buildMoveToast(["/d/F1", "/d/F2"], [])).toBe("Moved 2, failed 0");
  });
});

describe("useMoveFacturas", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("cancel is a no-op: sends no request and keeps selection", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    (window as unknown as Record<string, unknown>).__showConfirm = () =>
      Promise.resolve(false);

    const { result } = renderHook(() => useMoveFacturas());
    act(() => {
      result.current.togglePath("/a/FEV1");
      result.current.setDestDir("/dest");
    });
    await act(async () => {
      await result.current.confirmAndMove();
    });

    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current.selectedPaths).toEqual(["/a/FEV1"]);
    expect(result.current.toast).toBeNull();
  });

  it("confirm moves, toasts counts, and refreshes via GET /data", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === "/monitoreo-carpetas/move") {
        return {
          json: async () => ({
            status: "success",
            data: { moved: ["/d/F1"], failed: [] },
            errors: [],
          }),
        };
      }
      return {
        json: async () => ({ status: "success", data: {}, errors: [] }),
      };
    });
    vi.stubGlobal("fetch", fetchMock);
    (window as unknown as Record<string, unknown>).__showConfirm = () =>
      Promise.resolve(true);

    const { result } = renderHook(() => useMoveFacturas());
    act(() => {
      result.current.togglePath("/a/F1");
      result.current.setDestDir("/d");
    });
    await act(async () => {
      await result.current.confirmAndMove();
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/monitoreo-carpetas/move",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith("/monitoreo-carpetas/data");
    expect(result.current.toast).toBe("Moved 1, failed 0");
  });
});
