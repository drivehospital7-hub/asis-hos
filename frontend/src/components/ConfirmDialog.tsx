import {
  forwardRef,
  useImperativeHandle,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, X } from "lucide-react";

export interface ConfirmDialogHandle {
  /** Shows the dialog with a message. Resolves true on Confirm, false on Cancel/Escape. */
  show(message: string): Promise<boolean>;
}

interface ConfirmDialogProps {
  title?: string;
  children?: ReactNode;
}

export const ConfirmDialog = forwardRef<ConfirmDialogHandle, ConfirmDialogProps>(
  function ConfirmDialog({ title = "Confirmar", children }, ref) {
    const [open, setOpen] = useState(false);
    const [message, setMessage] = useState("");
    const [resolver, setResolver] = useState<((value: boolean) => void) | null>(
      null,
    );

    const show = useCallback((msg: string): Promise<boolean> => {
      setMessage(msg);
      setOpen(true);
      return new Promise<boolean>((resolve) => {
        setResolver(() => resolve);
      });
    }, []);

    useImperativeHandle(ref, () => ({ show }), [show]);

    const handleConfirm = useCallback(() => {
      setOpen(false);
      resolver?.(true);
    }, [resolver]);

    const handleCancel = useCallback(() => {
      setOpen(false);
      resolver?.(false);
    }, [resolver]);

    return (
      <Dialog.Root open={open} onOpenChange={(open) => {
        if (!open) {
          // Dialog closed via Escape or outside click → resolve false
          resolver?.(false);
          setResolver(null);
        }
        setOpen(open);
      }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-[99999] bg-[rgba(15,23,42,0.5)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <Dialog.Content
            className="fixed left-1/2 top-1/2 z-[99999] w-[90%] max-w-[400px] -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-2xl data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]"
          >
            <Dialog.Title className="flex items-center gap-2 text-lg font-bold text-[#0f172a] mb-3">
              <AlertTriangle className="h-5 w-5 text-[#f59e0b]" />
              {title}
            </Dialog.Title>
            <p className="text-sm text-[#475569] mb-5 leading-relaxed whitespace-pre-wrap break-words">
              {message}
            </p>
            <div className="flex justify-end gap-3">
              <Dialog.Close asChild>
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-[#e2e8f0] bg-white px-4 py-2 text-sm font-semibold text-[#475569] transition-all hover:bg-[#f8fafc] hover:border-[#cbd5e1] hover:-translate-y-px"
                  onClick={handleCancel}
                >
                  Cancelar
                </button>
              </Dialog.Close>
              <button
                className="inline-flex items-center gap-2 rounded-lg border border-transparent bg-[#0f172a] px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-[#1e293b] hover:-translate-y-px hover:shadow-md"
                onClick={handleConfirm}
              >
                Aceptar
              </button>
            </div>
            <Dialog.Close asChild>
              <button
                className="absolute right-4 top-4 inline-flex h-8 w-8 items-center justify-center rounded-lg text-[#94a3b8] transition-all hover:bg-[#f1f5f9] hover:text-[#475569]"
                aria-label="Cerrar"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </Dialog.Content>
        </Dialog.Portal>
        {children}
      </Dialog.Root>
    );
  },
);
