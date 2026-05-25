import { ShieldAlert, ArrowLeft } from "lucide-react";

export function UnauthorizedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center"
         style={{ background: "oklch(0.96 0.01 80)", fontFamily: "'Manrope', system-ui, sans-serif" }}>

      <div className="text-center max-w-md mx-4">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-5"
             style={{ background: "oklch(0.45 0.18 25 / 0.1)" }}>
          <ShieldAlert className="h-8 w-8" style={{ color: "oklch(0.45 0.18 25)" }} />
        </div>

        <h1 className="text-2xl font-bold mb-2"
            style={{ fontFamily: "'Sora', sans-serif", color: "oklch(0.15 0.02 160)" }}>
          No autorizado
        </h1>

        <p className="text-sm mb-6 leading-relaxed" style={{ color: "oklch(0.55 0.04 160)" }}>
          No tenés permisos para acceder a esta página.
          <br />
          Si creés que esto es un error, contactá al administrador del sistema.
        </p>

        <a
          href="/login"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150"
          style={{
            background: "oklch(0.25 0.06 160)",
            color: "oklch(0.97 0.01 160)",
            fontFamily: "'Manrope', sans-serif",
          }}
          onMouseOver={(e) => e.currentTarget.style.background = "oklch(0.35 0.07 160)"}
          onMouseOut={(e) => e.currentTarget.style.background = "oklch(0.25 0.06 160)"}
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al inicio
        </a>
      </div>
    </div>
  );
}
