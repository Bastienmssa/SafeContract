import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import Link from "next/link";

const TEAM = [
  { name: "Bastien", role: "Apprenti ingénieur cybersécurité" },
  { name: "Géraud", role: "Apprenti ingénieur cybersécurité" },
  { name: "Pierre-Henri", role: "Apprenti ingénieur cybersécurité" },
];

const STACK = [
  { label: "Frontend", value: "Next.js 14 · Tailwind CSS · TypeScript" },
  { label: "Backend", value: "Python · FastAPI · Mythril" },
  { label: "Gateway", value: "Zuplo · OpenAPI 3.1" },
  { label: "Base de données", value: "MongoDB · Motor (async)" },
  { label: "Infrastructure", value: "VPS · Caddy · PM2" },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#091628" }}>
      <Navbar />

      <main className="flex-1">

        {/* Hero */}
        <section className="max-w-3xl mx-auto px-6 pt-20 pb-16 text-center">
          <span className="inline-block text-xs font-semibold tracking-widest uppercase text-primary-500 mb-4">
            À propos
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-6" style={{ color: "rgba(255,255,255,0.95)" }}>
            La sécurité des smart contracts,{" "}
            <span
              className="inline-block"
              style={{
                background: "linear-gradient(135deg, #2cbe88 0%, #7dd8b8 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              rendue accessible.
            </span>
          </h1>
          <p className="text-lg leading-relaxed max-w-2xl mx-auto" style={{ color: "rgba(255,255,255,0.55)" }}>
            SafeContract est un projet académique développé à l'ESME Sudria. Notre mission : rendre
            l'audit de contrats Solidity automatique, lisible et accessible à tous les développeurs Web3.
          </p>
        </section>

        {/* Séparateur */}
        <div className="max-w-3xl mx-auto px-6">
          <div className="h-px" style={{ background: "rgba(255,255,255,0.08)" }} />
        </div>

        {/* Contexte */}
        <section className="max-w-3xl mx-auto px-6 py-16">
          <h2 className="text-xl font-bold mb-4" style={{ color: "rgba(255,255,255,0.9)" }}>Le projet</h2>
          <div className="space-y-4 leading-relaxed" style={{ color: "rgba(255,255,255,0.55)" }}>
            <p>
              Les smart contracts gèrent aujourd'hui des milliards de dollars d'actifs sur des blockchains
              publiques. Une seule vulnérabilité — réentrance, dépassement d'entier, contrôle d'accès défaillant —
              peut entraîner des pertes irréversibles.
            </p>
            <p>
              SafeContract automatise l'analyse statique via{" "}
              <span className="font-semibold" style={{ color: "rgba(255,255,255,0.85)" }}>Mythril</span>, un moteur de vérification symbolique
              développé par ConsenSys. Les résultats sont présentés dans une interface claire avec score de sécurité,
              timeline d'évolution, et diagnostic ligne par ligne.
            </p>
            <p>
              Les analyses sont persistées dans une base MongoDB pour permettre le suivi dans le temps de chaque
              contrat.
            </p>
          </div>
        </section>

        {/* Stack */}
        <section className="max-w-3xl mx-auto px-6 pb-16">
          <h2 className="text-xl font-bold mb-6" style={{ color: "rgba(255,255,255,0.9)" }}>Stack technique</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {STACK.map(({ label, value }) => (
              <div
                key={label}
                className="flex items-start gap-3 p-4 rounded-xl"
                style={{ background: "#0f2040", border: "1px solid rgba(255,255,255,0.08)" }}
              >
                <div
                  className="mt-0.5 w-2 h-2 rounded-full shrink-0"
                  style={{ background: "linear-gradient(135deg, #2cbe88, #152d5b)" }}
                />
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide mb-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>{label}</p>
                  <p className="text-sm font-medium" style={{ color: "rgba(255,255,255,0.85)" }}>{value}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Équipe */}
        <section className="max-w-3xl mx-auto px-6 pb-16">
          <h2 className="text-xl font-bold mb-6" style={{ color: "rgba(255,255,255,0.9)" }}>L'équipe</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {TEAM.map(({ name, role }) => (
              <div
                key={name}
                className="p-5 rounded-xl text-center"
                style={{ background: "#0f2040", border: "1px solid rgba(255,255,255,0.08)" }}
              >
                <div
                  className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center text-white font-bold text-lg"
                  style={{ background: "linear-gradient(135deg, #2cbe88 0%, #152d5b 100%)" }}
                >
                  {name[0]}
                </div>
                <p className="font-semibold" style={{ color: "rgba(255,255,255,0.9)" }}>{name}</p>
                <p className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.45)" }}>{role}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="max-w-3xl mx-auto px-6 pb-20 text-center">
          <div className="p-8 rounded-2xl" style={{ background: "#0f2040", border: "1px solid rgba(255,255,255,0.08)" }}>
            <p className="text-lg font-semibold mb-2" style={{ color: "rgba(255,255,255,0.9)" }}>Prêt à auditer votre contrat ?</p>
            <p className="text-sm mb-6" style={{ color: "rgba(255,255,255,0.45)" }}>Analysez gratuitement — sans compte requis.</p>
            <div className="flex items-center justify-center gap-3 flex-wrap">
              <Link
                href="/free-analyse"
                className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white hover:opacity-90 transition-all"
                style={{ background: "linear-gradient(135deg, #2cbe88 0%, #1a6e5a 100%)" }}
              >
                Essai gratuit
              </Link>
              <Link
                href="/connexion"
                className="px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-white/10 transition-all"
                style={{ color: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.15)" }}
              >
                Se connecter
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
