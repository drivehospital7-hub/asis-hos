import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { ExamenesPage } from "./page";
import { AppLayout } from "@/components/app-layout";
import type { Examen } from "@/lib/examenes";
import "@/styles/globals.css";

interface InitialData {
  username?: string;
  permisos?: string[];
  can_write?: boolean;
  current_facturador?: string;
  default_examenes?: Examen[];
}

const data = (window as unknown as { __INITIAL_DATA__?: InitialData }).__INITIAL_DATA__;

const root = document.getElementById("root");
if (!root) throw new Error("Root element #root not found");

createRoot(root).render(
  <StrictMode>
    <AppLayout username={data?.username} permisos={data?.permisos}>
      <ExamenesPage
        can_write={data?.can_write ?? false}
        current_facturador={data?.current_facturador ?? ""}
        default_examenes={data?.default_examenes ?? []}
      />
    </AppLayout>
  </StrictMode>,
);