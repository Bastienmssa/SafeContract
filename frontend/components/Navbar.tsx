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
      <nav className="pointer-events-auto flex items-center gap-1 backdrop-blur-md rounded-2xl shadow-lg px-2 py-1.5" style={{ background: "rgba(9,22,40,0.85)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>

        {/* Logo + nom */}
        <Link href="/" className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl hover:bg-white/5 transition-colors mr-1">
          <img src="/images/SafeContract-Logo.png" alt="SafeContract" className="h-6 w-auto" />
          <span
            className="font-bold text-sm tracking-tight"
            style={{ background: "linear-gradient(135deg, #2cbe88 0%, #152d5b 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}
          >
            SafeContract
          </span>
        </Link>

        {/* Séparateur */}
        <div className="h-5 w-px mx-1" style={{ background: "rgba(255,255,255,0.12)" }} />

        {/* Liens nav */}
        {NAV_LINKS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
              pathname === href
                ? "bg-white/10 text-white"
                : "text-white/60 hover:bg-white/10 hover:text-white"
            }`}
          >
            {label}
          </Link>
        ))}

        {/* Séparateur */}
        <div className="h-5 w-px mx-1" style={{ background: "rgba(255,255,255,0.12)" }} />

        {/* Actions */}
        <Link
          href="/free-analyse"
          className="px-3 py-1.5 rounded-xl text-sm font-medium text-white/60 hover:bg-white/10 hover:text-white transition-all"
        >
          Essai gratuit
        </Link>

        <Link
          href="/connexion"
          className="px-4 py-1.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 shadow-sm"
          style={{ background: "linear-gradient(135deg, #2cbe88 0%, #1a6e5a 100%)" }}
        >
          Se connecter
        </Link>
      </nav>
    </header>
  );
}
