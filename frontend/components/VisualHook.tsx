"use client";

import Link from "next/link";

export function VisualHook() {
  return (
    <section id="analyse" className="px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
      <div className="max-w-4xl mx-auto">
        <div className="relative">
          {/* Card mockup with security score */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="p-8 lg:p-12">
              <div className="flex flex-col md:flex-row items-center gap-8 lg:gap-16">
                <div className="flex-1 text-center md:text-left">
                  <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                    Score de sécurité
                  </p>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-5xl lg:text-6xl font-semibold text-primary-500">
                      98
                    </span>
                    <span className="text-2xl text-slate-400">/100</span>
                  </div>
                  <p className="mt-4 text-sm text-slate-600">
                    Analyse instantanée de vos contrats avec détection des
                    vulnérabilités critiques.
                  </p>
                </div>
                <div className="flex-1 w-full min-h-[200px] rounded-lg border border-slate-200 bg-slate-50/50 flex items-center justify-center">
                  <div className="text-center">
                    <div className="w-16 h-2 bg-slate-200 rounded mx-auto mb-3" />
                    <div className="space-y-2 w-48 mx-auto">
                      <div className="h-2 bg-slate-200 rounded" />
                      <div className="h-2 bg-slate-200 rounded w-4/5 mx-auto" />
                      <div className="h-2 bg-slate-200 rounded w-3/5 mx-auto" />
                    </div>
                    <p className="mt-4 text-xs text-slate-400">
                      Aperçu du tableau de bord
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          {/* CTA overlay */}
          <div className="mt-8 text-center">
            <Link
              href="#analyse"
              className="inline-flex items-center px-6 py-3 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 rounded-md transition-colors border border-primary-500"
            >
              Accéder à l&apos;analyse
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
