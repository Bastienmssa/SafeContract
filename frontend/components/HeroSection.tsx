"use client";

import Link from "next/link";
import { Play } from "lucide-react";
import dynamic from "next/dynamic";

const SoftAurora = dynamic(() => import("@/components/SoftAurora"), { ssr: false });

export function HeroSection() {
  return (
    <section className="relative overflow-hidden" style={{ minHeight: "88vh", background: "#0a1628" }}>
      {/* Aurora background */}
      <div className="absolute inset-0 z-0">
        <SoftAurora
          color1="#2cbe88"
          color2="#1e4fa3"
          brightness={1.2}
          speed={0.5}
          scale={1.8}
          bandHeight={0.45}
          bandSpread={1.2}
          noiseFrequency={2.2}
          noiseAmplitude={0.9}
          octaveDecay={0.12}
          layerOffset={1.2}
          colorSpeed={0.8}
          enableMouseInteraction={true}
          mouseInfluence={0.2}
        />
      </div>

      {/* Gradient overlay — fade vers le bas pour raccorder avec le reste de la page */}
      <div
        className="absolute bottom-0 left-0 right-0 z-10 pointer-events-none"
        style={{ height: "160px", background: "linear-gradient(to bottom, transparent, #091628)" }}
      />

      {/* Content */}
      <div className="relative z-20 flex flex-col items-center text-center px-4 sm:px-6 lg:px-8" style={{ minHeight: "88vh", paddingTop: "12vh" }}>
        {/* Badge */}
        <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
          style={{ background: "rgba(44,190,136,0.15)", color: "#2cbe88", border: "1px solid rgba(44,190,136,0.3)" }}>
          Sécurité Smart Contract
        </span>

        {/* Brand name */}
        <h1 className="font-semibold tracking-tight leading-none mb-4"
          style={{
            fontSize: "clamp(3rem, 8vw, 6rem)",
            background: "linear-gradient(135deg, #2cbe88 0%, #7dd8b8 50%, #a8ecd8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}>
          Safe Contract
        </h1>

        {/* Tagline */}
        <p className="text-lg sm:text-xl font-medium mb-3" style={{ color: "rgba(255,255,255,0.85)" }}>
          Déployez vos <span style={{ color: "#2cbe88" }}>Smart Contracts</span> en toute sérénité.
        </p>
        <p className="max-w-xl text-base" style={{ color: "rgba(255,255,255,0.55)", lineHeight: 1.7 }}>
          Analyse automatisée par IA et moteurs de vérification formelle
          pour garantir l&apos;intégrité de vos protocoles Web3.
        </p>

        {/* CTA buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4" style={{ marginTop: "300px" }}>
          <Link
            href="#analyse"
            className="w-full sm:w-auto px-7 py-3 text-sm font-semibold text-white rounded-lg transition-all hover:opacity-90 hover:scale-105"
            style={{ background: "linear-gradient(135deg, #2cbe88, #1fa876)", boxShadow: "0 4px 24px rgba(44,190,136,0.35)" }}
          >
            Démarrer l&apos;analyse
          </Link>
          <Link
            href="#demo"
            className="w-full sm:w-auto px-7 py-3 text-sm font-semibold rounded-lg transition-all hover:scale-105 inline-flex items-center justify-center gap-2"
            style={{ background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.85)", border: "1px solid rgba(255,255,255,0.15)", backdropFilter: "blur(8px)" }}
          >
            <Play className="w-4 h-4" strokeWidth={2} />
            Voir la démo
          </Link>
        </div>
      </div>
    </section>
  );
}
