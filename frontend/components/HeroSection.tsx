import Link from "next/link";
import { Play } from "lucide-react";

export function HeroSection() {
  return (
    <section className="px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
      <div className="max-w-3xl mx-auto text-center">
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-semibold text-slate-900 tracking-tight leading-tight">
          Déployez vos{" "}
          <span className="text-primary-500">Smart Contracts</span> en toute
          sérénité.
        </h1>
        <p className="mt-6 text-lg text-slate-600 leading-relaxed">
          L&apos;analyse automatisée par IA et moteurs de{" "}
          <span className="text-primary-500">vérification formelle</span> pour
          garantir l&apos;intégrité de vos protocoles Web3.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="#analyse"
            className="w-full sm:w-auto px-6 py-3 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 rounded-md transition-colors border border-primary-500"
          >
            Démarrer l&apos;analyse
          </Link>
          <Link
            href="#demo"
            className="w-full sm:w-auto px-6 py-3 text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 rounded-md transition-colors border border-slate-200 inline-flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" strokeWidth={2} />
            Voir la démo
          </Link>
        </div>
      </div>
    </section>
  );
}
