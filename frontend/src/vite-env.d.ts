/// <reference types="vite/client" />

/* Global helpers exposed by AppLayout for confirm/alert dialogs */
interface Window {
  __showConfirm?: (message: string) => Promise<boolean>;
}

/* Modal helper loaded globally via modal.js in react_shell.html */
interface Modal {
  confirm(message: string): Promise<boolean>;
  alert(message: string): Promise<void>;
  toast(message: string, duration?: number): Promise<void>;
}

declare var Modal: Modal;
