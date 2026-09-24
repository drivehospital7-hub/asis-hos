import { useEffect } from "react";

/** Toast duration (matches /procesar). */
export const TOAST_DURATION = 2500;

export function Toast({
  message,
  onDone,
}: {
  message: string;
  onDone: () => void;
}) {
  useEffect(() => {
    const t = setTimeout(onDone, TOAST_DURATION);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background shadow-lg">
        {message}
      </div>
    </div>
  );
}
