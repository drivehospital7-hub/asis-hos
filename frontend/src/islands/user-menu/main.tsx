import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { UserMenu } from "../user-menu";

// NOTE: this island deliberately does NOT import globals.css. That file
// includes Tailwind preflight, which would leak a global reset into the host
// Jinja page. Utilities are compiled at runtime by the Tailwind browser build
// already present on the page; Flask design tokens are bridged via a small
// <style> block in base.html (:root --color-* aliases).
const mount = document.getElementById("user-menu-root");

if (mount) {
  // The island takes over: hide the server-rendered fallback badge.
  document.getElementById("header-auth-status")?.style.setProperty("display", "none");
  mount.style.removeProperty("display");
  createRoot(mount).render(
    <StrictMode>
      <UserMenu initialUsername={mount.getAttribute("data-username") ?? ""} />
    </StrictMode>,
  );
} else {
  console.warn("[FRONT] user-menu island skipped: #user-menu-root not found");
}
