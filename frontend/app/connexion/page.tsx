"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, ShieldCheck } from "lucide-react";

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

function SSOIcon() {
  return (
    <ShieldCheck className="w-4 h-4 text-slate-500" />
  );
}

export default function ConnexionPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (identifier === "admin" && password === "admin") {
      localStorage.setItem("sc_auth", "admin");
      router.push("/dashboard");
    } else {
      setError("Identifiant ou mot de passe incorrect.");
    }
  }

  function handleOAuth(provider: string) {
    // factice
    alert(`Connexion ${provider} — non implémentée`);
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#091628" }}>
      {/* Header minimal */}
      <header className="h-16 flex items-center px-6">
        <Link href="/" className="flex items-center shrink-0">
          <img src="/images/SafeContract-Logo.png" alt="SafeContract" className="h-8 w-auto" />
        </Link>
      </header>

      {/* Carte centrale */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-semibold text-white">Connexion</h1>
            <p className="mt-2 text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>
              Accédez à votre espace SafeContract
            </p>
          </div>

          {/* OAuth */}
          <div className="space-y-2.5 mb-6">
            {[
              { label: "Continuer avec GitHub", icon: <GitHubIcon />, id: "GitHub" },
              { label: "Continuer avec Google", icon: <GoogleIcon />, id: "Google" },
              { label: "Connexion SSO entreprise", icon: <SSOIcon />, id: "SSO" },
            ].map(({ label, icon, id }) => (
              <button
                key={id}
                type="button"
                onClick={() => handleOAuth(id)}
                className="w-full flex items-center justify-center gap-2.5 px-4 py-2.5 text-sm font-semibold text-white rounded-md transition-all hover:opacity-90"
                style={{ background: "linear-gradient(135deg, #2cbe88 0%, #1a6e5a 100%)", border: "1px solid rgba(44,190,136,0.3)" }}
              >
                {icon}
                {label}
              </button>
            ))}
          </div>

          {/* Séparateur */}
          <div className="relative flex items-center mb-6">
            <div className="flex-1" style={{ borderTop: "1px solid rgba(255,255,255,0.1)" }} />
            <span className="mx-3 text-xs uppercase tracking-wide" style={{ color: "rgba(255,255,255,0.35)" }}>ou</span>
            <div className="flex-1" style={{ borderTop: "1px solid rgba(255,255,255,0.1)" }} />
          </div>

          {/* Formulaire identifiant / mot de passe */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="identifier" className="block text-sm font-medium mb-1.5" style={{ color: "rgba(255,255,255,0.8)" }}>
                Identifiant
              </label>
              <input
                id="identifier"
                type="text"
                autoComplete="username"
                placeholder="email ou nom d'utilisateur"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                className="w-full px-3 py-2.5 text-sm text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent"
                style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.12)", caretColor: "#2cbe88" }}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="password" className="block text-sm font-medium" style={{ color: "rgba(255,255,255,0.8)" }}>
                  Mot de passe
                </label>
                <button type="button" className="text-xs text-primary-500 hover:text-primary-400 transition-colors">
                  Mot de passe oublié ?
                </button>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2.5 pr-10 text-sm text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent"
                  style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.12)", caretColor: "#2cbe88" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-3 flex items-center hover:text-white transition-colors"
                  style={{ color: "rgba(255,255,255,0.4)" }}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-400 rounded-md px-3 py-2" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={!identifier.trim() || !password.trim()}
              className="w-full py-2.5 text-sm font-semibold text-white rounded-md transition-all hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: "linear-gradient(135deg, #2cbe88 0%, #1a6e5a 100%)" }}
            >
              Se connecter
            </button>
          </form>

          <p className="mt-6 text-center text-sm" style={{ color: "rgba(255,255,255,0.45)" }}>
            Pas encore de compte ?{" "}
            <Link href="/free-analyse" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
              Essai gratuit
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
