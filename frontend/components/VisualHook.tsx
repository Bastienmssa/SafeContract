"use client";

const MOCK_ISSUES = [
  { severity: "critical", label: "Reentrancy", tool: "Mythril", line: 42, swc: "SWC-107" },
  { severity: "medium",   label: "Timestamp Dependence", tool: "Slither", line: 78, swc: "SWC-116" },
  { severity: "low",      label: "Floating Pragma", tool: "Solhint", line: 1,  swc: "" },
];

const SEV_COLORS: Record<string, { dot: string; badge: string; text: string }> = {
  critical: { dot: "#ef4444", badge: "rgba(239,68,68,0.12)", text: "#f87171" },
  medium:   { dot: "#f59e0b", badge: "rgba(245,158,11,0.12)", text: "#fbbf24" },
  low:      { dot: "#3b82f6", badge: "rgba(59,130,246,0.12)", text: "#60a5fa" },
};

export function VisualHook() {
  return (
    <section id="analyse" className="px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
      <div className="max-w-4xl mx-auto">

        {/* Card mockup */}
        <div className="rounded-2xl overflow-hidden" style={{ background: "#0f2040", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 24px 64px rgba(0,0,0,0.4)" }}>

          {/* Header bar */}
          <div className="flex items-center gap-3 px-6 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", background: "rgba(255,255,255,0.03)" }}>
            <div className="flex gap-1.5">
              <span className="w-3 h-3 rounded-full" style={{ background: "#ef4444" }} />
              <span className="w-3 h-3 rounded-full" style={{ background: "#f59e0b" }} />
              <span className="w-3 h-3 rounded-full" style={{ background: "#22c55e" }} />
            </div>
            <span className="text-xs font-mono ml-2" style={{ color: "rgba(255,255,255,0.3)" }}>VaultProtocol.sol — SafeContract Analysis</span>
          </div>

          <div className="p-8 lg:p-10 flex flex-col md:flex-row gap-10">

            {/* Score column */}
            <div className="flex flex-col items-center md:items-start gap-4 md:w-52 shrink-0">
              <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "rgba(255,255,255,0.4)" }}>Score de sécurité</p>

              {/* Circular score */}
              <div className="relative w-32 h-32">
                <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
                  <circle cx="50" cy="50" r="40" fill="none" stroke="#2cbe88" strokeWidth="8"
                    strokeDasharray={`${2 * Math.PI * 40 * 0.78} ${2 * Math.PI * 40}`}
                    strokeLinecap="round" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold" style={{ color: "#2cbe88" }}>78</span>
                  <span className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>/100</span>
                </div>
              </div>

              <div className="w-full space-y-2">
                {[
                  { label: "Critique", count: 1, color: "#ef4444" },
                  { label: "Moyen",   count: 1, color: "#f59e0b" },
                  { label: "Faible",  count: 1, color: "#3b82f6" },
                ].map(({ label, count, color }) => (
                  <div key={label} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                      <span style={{ color: "rgba(255,255,255,0.5)" }}>{label}</span>
                    </div>
                    <span className="font-semibold" style={{ color: "rgba(255,255,255,0.8)" }}>{count}</span>
                  </div>
                ))}
              </div>

              <div className="w-full pt-2" style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}>
                <p className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>Analysé avec Mythril · Slither · Solhint</p>
              </div>
            </div>

            {/* Issues list */}
            <div className="flex-1 flex flex-col gap-3">
              <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "rgba(255,255,255,0.4)" }}>Vulnérabilités détectées</p>
              {MOCK_ISSUES.map((issue) => {
                const c = SEV_COLORS[issue.severity];
                return (
                  <div key={issue.label} className="flex items-start gap-3 px-4 py-3 rounded-xl" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <span className="mt-1 w-2 h-2 rounded-full shrink-0" style={{ background: c.dot }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium" style={{ color: "rgba(255,255,255,0.85)" }}>{issue.label}</span>
                        {issue.swc && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.35)" }}>{issue.swc}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: c.badge, color: c.text }}>{issue.severity}</span>
                        <span className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>ligne {issue.line} · {issue.tool}</span>
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Verdict banner */}
              <div className="mt-2 flex items-center gap-3 px-4 py-3 rounded-xl" style={{ background: "rgba(44,190,136,0.08)", border: "1px solid rgba(44,190,136,0.2)" }}>
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 16 16" fill="none">
                  <path d="M8 1.5L2 4v4c0 3.31 2.58 6.41 6 7 3.42-.59 6-3.69 6-7V4L8 1.5z" fill="rgba(44,190,136,0.3)" stroke="#2cbe88" strokeWidth="1.2" />
                </svg>
                <p className="text-xs" style={{ color: "rgba(44,190,136,0.9)" }}>GNN SafeContract · Reentrancy confirmée à <strong>92%</strong> de confiance</p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
