"use client";

import Link from "next/link";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-slate-200">
      <nav className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center shrink-0">
          <img src="/images/SafeContract-Logo.png" alt="SafeContract" className="h-8 w-auto" />
        </Link>
        <div className="flex items-center gap-4 sm:gap-6">
          <Link
            href="#connexion"
            className="text-sm font-medium text-slate-600 hover:text-primary-500 transition-colors"
          >
            Se connecter
          </Link>
          <Link
            href="/free-analyse"
            className="text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 px-4 py-2 rounded-md transition-colors border border-primary-500"
          >
            Essai gratuit
          </Link>
        </div>
      </nav>
    </header>
  );
}
