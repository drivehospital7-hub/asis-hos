import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { MonitoreoCarpetasPage } from "./page";
import { AppLayout } from "@/components/app-layout";
import "@/styles/globals.css";

const data = (window as unknown as { __INITIAL_DATA__?: { username?: string; permisos?: string[]; can_write?: boolean } }).__INITIAL_DATA__;

const root = document.getElementById("root");
if (!root) throw new Error("Root element #root not found");

createRoot(root).render(
  <StrictMode>
    <AppLayout username={data?.username} permisos={data?.permisos}>
      <MonitoreoCarpetasPage can_write={data?.can_write ?? false} />
    </AppLayout>
  </StrictMode>,
);
