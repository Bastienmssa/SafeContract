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
    <div className="min-h-screen flex flex-col bg-white">
      <Navbar />

      <main className="flex-1">

        {/* Hero */}
        <section className="max-w-3xl mx-auto px-6 pt-20 pb-16 text-center">
          <span className="inline-block text-xs font-semibold tracking-widest uppercase text-primary-500 mb-4">
            À propos
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 leading-tight mb-6">
            La sécurité des smart contracts,{" "}
            <span
              className="inline-block"
              style={{
                background: "linear-gradient(135deg, #2cbe88 0%, #152d5b 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              rendue accessible.
            </span>
          </h1>
          <p className="text-lg text-slate-500 leading-relaxed max-w-2xl mx-auto">
            SafeContract est un projet académique développé à l'ESME Sudria. Notre mission : rendre
            l'audit de contrats Solidity automatique, lisible et accessible à tous les développeurs Web3.
          </p>
        </section>

        {/* Séparateur */}
        <div className="max-w-3xl mx-auto px-6">
          <div className="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent" />
        </div>

        {/* Contexte */}
        <section className="max-w-3xl mx-auto px-6 py-16">
          <h2 className="text-xl font-bold text-slate-900 mb-4">Le projet</h2>
          <div className="space-y-4 text-slate-600 leading-relaxed">
            <p>
              Les smart contracts gèrent aujourd'hui des milliards de dollars d'actifs sur des blockchains
              publiques. Une seule vulnérabilité — réentrance, dépassement d'entier, contrôle d'accès défaillant —
              peut entraîner des pertes irréversibles.
            </p>
            <p>
              SafeContract automatise l'analyse statique via{" "}
              <span className="font-semibold text-slate-800">Mythril</span>, un moteur de vérification symbolique
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
          <h2 className="text-xl font-bold text-slate-900 mb-6">Stack technique</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {STACK.map(({ label, value }) => (
              <div
                key={label}
                className="flex items-start gap-3 p-4 rounded-xl border border-slate-200 bg-slate-50"
              >
                <div
                  className="mt-0.5 w-2 h-2 rounded-full shrink-0"
                  style={{ background: "linear-gradient(135deg, #2cbe88, #152d5b)" }}
                />
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-0.5">{label}</p>
                  <p className="text-sm font-medium text-slate-800">{value}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Équipe */}
        <section className="max-w-3xl mx-auto px-6 pb-16">
          <h2 className="text-xl font-bold text-slate-900 mb-6">L'équipe</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {TEAM.map(({ name, role }) => (
              <div
                key={name}
                className="p-5 rounded-xl border border-slate-200 bg-white text-center"
              >
                <div
                  className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center text-white font-bold text-lg"
                  style={{ background: "linear-gradient(135deg, #2cbe88 0%, #152d5b 100%)" }}
                >
                  {name[0]}
                </div>
                <p className="font-semibold text-slate-900">{name}</p>
                <p className="text-xs text-slate-500 mt-1">{role}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="max-w-3xl mx-auto px-6 pb-20 text-center">
          <div className="p-8 rounded-2xl border border-slate-200 bg-slate-50">
            <p className="text-lg font-semibold text-slate-800 mb-2">Prêt à auditer votre contrat ?</p>
            <p className="text-sm text-slate-500 mb-6">Analysez gratuitement — sans compte requis.</p>
            <div className="flex items-center justify-center gap-3 flex-wrap">
              <Link
                href="/free-analyse"
                className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white shadow-sm hover:opacity-90 transition-all"
                style={{ background: "linear-gradient(135deg, #2cbe88 0%, #1a6e5a 100%)" }}
              >
                Essai gratuit
              </Link>
              <Link
                href="/connexion"
                className="px-6 py-2.5 rounded-xl text-sm font-semibold text-slate-700 border border-slate-200 bg-white hover:bg-slate-50 transition-all"
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
