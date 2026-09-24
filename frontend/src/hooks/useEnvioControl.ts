import { useCallback, useEffect, useRef, useState } from "react";
import {
  buildEnvioSet,
  buildObservacion,
  canShowEnvio,
  norm,
} from "@/pages/procesar/utils";

interface UseEnvioControlOptions {
  can_write: boolean;
  canControl: boolean;
  /** Called after a successful POST so the page can flag the row as sent. */
  onEnviada?: (factura: string) => void;
}

/**
 * Shared send-to-control logic (preload + per-row POST + toast).
 * Same behavior as /procesar: sends as "Otros" with duplicate confirm.
 */
export function useEnvioControl({
  can_write,
  canControl,
  onEnviada,
}: UseEnvioControlOptions) {
  const envioExistentes = useRef<Set<string>>(new Set());
  const envioEnviadas = useRef<Set<string>>(new Set());
  const [envioVersion, setEnvioVersion] = useState(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
  }, []);

  const showEnvio = canShowEnvio(can_write, canControl);

  // Preload único: GET /api/control-errores → Set global normalizado
  useEffect(() => {
    if (!showEnvio) return;
    fetch("/api/control-errores")
      .then((res) => res.json())
      .then((data) => {
        const errores =
          data.status === "success" && data.data?.errores
            ? (data.data.errores as Array<{
                factura?: string;
                tipo_error?: string;
              }>)
            : [];
        envioExistentes.current = buildEnvioSet(errores);
        setEnvioVersion((v) => v + 1);
      })
      .catch(() => {
        envioExistentes.current = new Set();
      });
  }, [showEnvio]);

  const handleSendToControl = useCallback(
    async (
      factura: string,
      descripcion: string,
      responsable: string,
      detalleA = "",
      detalleB = "",
    ) => {
      if (!can_write || !canControl) {
        showToast("Iniciá sesión para enviar");
        return;
      }
      if (!factura) return;

      const alreadyExists = envioExistentes.current.has(norm(factura));
      if (alreadyExists) {
        if (
          !(await window.__showConfirm!(
            `La factura "${factura}" ya existe en la tabla de Control de Errores.\n¿Querés duplicarla de todas formas?`,
          ))
        ) {
          return;
        }
      } else {
        if (
          !(await window.__showConfirm!(
            `¿Enviar factura "${factura}" a Control de Errores como "Otros"?`,
          ))
        ) {
          return;
        }
      }

      const observacion = buildObservacion(descripcion, detalleA, detalleB);

      try {
        const res = await fetch("/api/control-errores", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tipo_error: "Otros",
            factura,
            observacion,
            estado: "S",
            responsable: responsable || "",
          }),
        });
        const json = await res.json();
        if (json.status === "success") {
          envioEnviadas.current.add(norm(factura));
          envioExistentes.current.add(norm(factura));
          onEnviada?.(factura);
          setEnvioVersion((v) => v + 1);
          showToast(`✅ Factura "${factura}" enviada a Control de Errores`);
        } else {
          const errs = json.errors || ["Error desconocido"];
          showToast("Error: " + errs.join(", "));
        }
      } catch {
        showToast("Error de conexión al enviar");
      }
    },
    [can_write, canControl, onEnviada, showToast],
  );

  return {
    showEnvio,
    envioExistentes,
    envioEnviadas,
    envioVersion,
    toastMessage,
    setToastMessage,
    showToast,
    handleSendToControl,
  };
}
