"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/about", label: "À propos" },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 flex justify-center px-4 pt-4 pb-2 pointer-events-none">
      <nav className="pointer-events-auto flex items-center gap-1 bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl shadow-lg shadow-black/[0.06] px-2 py-1.5">

        {/* Logo + nom */}
        <Link href="/" className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl hover:bg-slate-50 transition-colors mr-1">
          <img src="/images/SafeContract-Logo.png" alt="SafeContract" className="h-6 w-auto" />
          <span
            className="font-bold text-sm tracking-tight"
            style={{ background: "linear-gradient(135deg, #2cbe88 0%, #152d5b 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}
          >
            SafeContract
          </span>
        </Link>

        {/* Séparateur */}
        <div className="h-5 w-px bg-slate-200 mx-1" />

        {/* Liens nav */}
        {NAV_LINKS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
              pathname === href
                ? "bg-slate-100 text-slate-900"
                : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            {label}
          </Link>
        ))}

        {/* Séparateur */}
        <div className="h-5 w-px bg-slate-200 mx-1" />

        {/* Actions */}
        <Link
          href="/connexion"
          className="px-3 py-1.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition-all"
        >
          Se connecter
        </Link>

        <Link
          href="/free-analyse"
          className="px-4 py-1.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 shadow-sm"
          style={{ background: "linear-gradient(135deg, #2cbe88 0%, #1a6e5a 100%)" }}
        >
          Essai gratuit
        </Link>
      </nav>
    </header>
  );
}
