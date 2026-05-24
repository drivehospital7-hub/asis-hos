import { useState } from "react";
import { LogIn, User, Lock, Eye, EyeOff } from "lucide-react";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Usuario y contraseña son requeridos");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/auth/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user: username, pass: password }),
      });
      const data = await res.json();

      if (data.status === "success") {
        window.location.href = "/dashboard";
      } else {
        setError(data.errors?.[0] || "Usuario o contraseña incorrectos");
      }
    } catch {
      setError("Error de conexión. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex"
         style={{ background: "oklch(0.96 0.01 80)", fontFamily: "'Manrope', system-ui, sans-serif" }}>

      {/* Lado izquierdo: imagen 16:9 */}
      <div className="hidden md:flex w-1/2 items-center justify-center p-8"
           style={{ background: "oklch(0.28 0.045 165)" }}>
        <img
          src="/static/img/login-logo.jpeg"
          alt="Hospital Orito"
          className="max-w-full max-h-full rounded-2xl shadow-lg object-contain"
          style={{ maxHeight: "70vh" }}
        />
      </div>

      {/* Lado derecho: formulario */}
      <div className="w-full md:w-1/2 flex items-center justify-center p-4 md:p-8">
        <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-sm">
          {/* Logo HOR (texto) */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl mb-3"
                 style={{ background: "oklch(0.25 0.06 160 / 0.1)" }}>
              <span className="text-2xl font-bold"
                    style={{ color: "oklch(0.25 0.06 160)", fontFamily: "'Sora', sans-serif" }}>
                HOR
              </span>
            </div>
            <h1 className="text-xl font-semibold"
                style={{ fontFamily: "'Sora', sans-serif", color: "oklch(0.15 0.02 160)", letterSpacing: "-0.02em" }}>
              Hospital Orito
            </h1>
            <p className="text-sm mt-1" style={{ color: "oklch(0.55 0.04 160)" }}>
              Iniciar sesión
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 px-4 py-2.5 rounded-xl text-sm font-medium text-center"
                 style={{ background: "oklch(0.45 0.18 25 / 0.15)", color: "oklch(0.45 0.18 25)" }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="username" className="block text-xs font-semibold mb-1.5 uppercase tracking-wider"
                     style={{ color: "oklch(0.55 0.04 160)" }}>
                Usuario
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4"
                      style={{ color: "oklch(0.55 0.04 160 / 0.5)" }} />
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                  className="w-full pl-10 pr-4 py-3 rounded-xl text-sm outline-none transition-all duration-150"
                  style={{
                    border: "1px solid oklch(0.55 0.04 160 / 0.2)",
                    color: "oklch(0.15 0.02 160)",
                    background: "white",
                  }}
                />
              </div>
            </div>

            <div className="mb-6">
              <label htmlFor="password" className="block text-xs font-semibold mb-1.5 uppercase tracking-wider"
                     style={{ color: "oklch(0.55 0.04 160)" }}>
                Contraseña
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4"
                      style={{ color: "oklch(0.55 0.04 160 / 0.5)" }} />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-10 py-3 rounded-xl text-sm outline-none transition-all duration-150"
                  style={{
                    border: "1px solid oklch(0.55 0.04 160 / 0.2)",
                    color: "oklch(0.15 0.02 160)",
                    background: "white",
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer border-none bg-transparent p-0"
                  style={{ color: "oklch(0.55 0.04 160 / 0.5)" }}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl text-sm font-semibold cursor-pointer transition-all duration-150 border-none flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: loading ? "oklch(0.35 0.07 160)" : "oklch(0.25 0.06 160)",
                color: "oklch(0.97 0.01 160)",
                fontFamily: "'Manrope', sans-serif",
              }}
              onMouseOver={(e) => { if (!loading) e.currentTarget.style.background = "oklch(0.35 0.07 160)"; }}
              onMouseOut={(e) => { if (!loading) e.currentTarget.style.background = "oklch(0.25 0.06 160)"; }}
            >
              {loading ? "Iniciando sesión..." : (
                <>
                  <LogIn className="h-4 w-4" />
                  Iniciar sesión
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
