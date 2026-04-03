"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  FileCode2,
  History,
  LogOut,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  ChevronRight,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  ScanSearch,
  Upload,
  X,
  Loader2,
  ArrowRight,
  Bot,
  Sparkles,
  Search,
  FileDown,
} from "lucide-react";
import { Contract, Issue, Severity, AiVerdict } from "./data";

// ─── Aggregated report → Contract mapper ─────────────────────────────────────

interface AggregatedIssue {
  tool: string;
  title: string;
  description: string;
  severity: string;
  line: number | null;
  swcId: string;
  confidence: string;
  confirmedByGnn?: boolean;
  gnnConfidence?: string;
  gnnDescription?: string;
}

interface AggregatedReport {
  score: number;
  issues: AggregatedIssue[];
  tools_used: string[];
  tools_errors: Record<string, string>;
  tools_versions?: Record<string, string>;
  summary: { critical: number; medium: number; low: number; total: number };
  ai_verdict?: AiVerdict;
}

function reportToContract(report: AggregatedReport, filename: string, code: string, dbId?: string): Contract {
  const issues: Issue[] = report.issues.map((i) => ({
    line: i.line ?? 0,
    severity: (i.severity === "critical" || i.severity === "medium" || i.severity === "low"
      ? i.severity
      : "low") as Severity,
    title: i.title,
    desc: i.description,
    swcId: i.swcId || "",
    tool: i.tool,
    confirmedByGnn: i.confirmedByGnn,
    gnnConfidence:  i.gnnConfidence,
    gnnDescription: i.gnnDescription,
  }));

  const today = new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "short" });

  return {
    id: dbId ?? String(Date.now()),
    name: filename,
    score: report.score,
    lastAnalyzed: new Date().toISOString().slice(0, 10),
    issues,
    timeline: [{ date: today, score: report.score }],
    code,
    toolsUsed: report.tools_used,
    toolsErrors: report.tools_errors,
    toolsVersions: report.tools_versions,
    aiVerdict: report.ai_verdict,
  };
}

// ─── DB analysis → Contract mapper ───────────────────────────────────────────

interface DBIssue {
  line: number | null;
  severity: string;
  title: string;
  description?: string;
  desc?: string;
  swcId?: string;
  tool?: string;
}

interface RawAnalysis {
  id: string;
  filename: string;
  code: string;
  score: number;
  issues: DBIssue[];
  tools_used: string[];
  tools_errors: Record<string, string>;
  analyzed_at: string;
  status: string;
  ai_verdict?: AiVerdict;
}

function buildContracts(analyses: RawAnalysis[]): Contract[] {
  const byFilename: Record<string, RawAnalysis[]> = {};
  for (const a of analyses) {
    if (!byFilename[a.filename]) byFilename[a.filename] = [];
    byFilename[a.filename].push(a);
  }
  return Object.entries(byFilename).map(([filename, scans]) => {
    const latest = scans[0];
    const timeline = [...scans].reverse().map((s) => ({
      date: new Date(s.analyzed_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short" }),
      score: s.score,
    }));
    const issues: Issue[] = latest.issues.map((i) => ({
      line: i.line ?? 0,
      severity: (i.severity === "critical" || i.severity === "medium" || i.severity === "low"
        ? i.severity : "low") as Severity,
      title: i.title,
      desc: i.desc ?? i.description ?? "",
      swcId: i.swcId ?? "",
      tool: i.tool,
    }));

    return {
      id: latest.id,
      name: filename,
      score: latest.score,
      issues,
      lastAnalyzed: latest.analyzed_at.slice(0, 10),
      timeline,
      code: latest.code,
      toolsUsed: latest.tools_used,
      toolsErrors: latest.tools_errors,
      aiVerdict: latest.ai_verdict,
    };
  });
}

// ─── Tool packages ────────────────────────────────────────────────────────────

type PackageId = "statique" | "dynamique";

const PACKAGES: {
  id: PackageId;
  name: string;
  description: string;
  tools: string[];
  icon: React.ElementType;
  available: boolean;
}[] = [
  {
    id: "statique",
    name: "Analyse Statique",
    description: "Slither + Solhint — lecture du code source, détection de patterns dangereux et bonnes pratiques.",
    tools: ["slither", "solhint"],
    icon: Search,
    available: true,
  },
  {
    id: "dynamique",
    name: "Analyse Dynamique",
    description: "Mythril + Foundry + Echidna — exécution symbolique, fuzzing et compilation.",
    tools: ["mythril", "foundry", "echidna"],
    icon: ScanSearch,
    available: true,
  },
];

const STATIC_TOOLS = ["slither", "solhint"];
const DYNAMIC_TOOLS = ["mythril", "foundry", "echidna"];

const TOOL_LABELS: Record<string, string> = {
  mythril: "Mythril",
  slither: "Slither",
  solhint: "Solhint",
  echidna: "Echidna",
  foundry: "Foundry",
  ai: "IA SafeContract",
};

// ─── Toast ───────────────────────────────────────────────────────────────────

interface ToastData { type: "success" | "error"; msg: string; key: number; }

function Toast({ data, onDismiss }: { data: ToastData; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 5000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border max-w-sm animate-in slide-in-from-bottom-4 fade-in duration-300 ${
      data.type === "success" ? "bg-white border-emerald-200" : "bg-white border-red-200"
    }`}>
      {data.type === "success"
        ? <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
        : <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />}
      <span className={`text-sm font-medium flex-1 ${data.type === "success" ? "text-emerald-800" : "text-red-800"}`}>
        {data.msg}
      </span>
      <button onClick={onDismiss} className="text-slate-400 hover:text-slate-600 shrink-0 ml-1">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

// ─── AnalyseScan component ────────────────────────────────────────────────────

function AnalyseScan({
  onResult,
  isGloballyScanning,
  onScanStart,
  onScanError,
  onScanFinally,
}: {
  onResult: (c: Contract) => void;
  isGloballyScanning: boolean;
  onScanStart: (filename: string) => void;
  onScanError: (msg: string) => void;
  onScanFinally: () => void;
}) {
  const [selectedPackages, setSelectedPackages] = useState<Set<PackageId>>(new Set<PackageId>(["dynamique"]));
  const [aiSelected, setAiSelected] = useState(false);
  const [contractText, setContractText] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasInput = uploadedFile !== null || contractText.trim().length > 0;
  const hasTools = selectedPackages.size > 0 || aiSelected;

  function togglePackage(id: PackageId) {
    setSelectedPackages((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        // Autoriser la désélection seulement si l'IA est cochée OU si un autre package reste
        if (next.size === 1 && !aiSelected) return prev;
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function toggleAi() {
    setAiSelected((prev) => {
      const next = !prev;
      // Si on décoche l'IA et qu'aucun package n'est sélectionné, réactiver le dynamique par défaut
      if (!next && selectedPackages.size === 0) {
        setSelectedPackages(new Set<PackageId>(["dynamique"]));
      }
      return next;
    });
  }

  function getSelectedTools(): string[] {
    const tools: string[] = [];
    if (selectedPackages.has("statique")) tools.push(...STATIC_TOOLS);
    if (selectedPackages.has("dynamique")) tools.push(...DYNAMIC_TOOLS);
    if (aiSelected) tools.push("ai");
    return tools;
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFile(file);
    setContractText("");
  }

  function removeFile() {
    setUploadedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hasInput || !hasTools || isGloballyScanning) return;
    setErrorMsg("");

    const file = uploadedFile ?? new File([contractText], "contract.sol", { type: "text/plain" });
    const filename = file.name;
    const code = uploadedFile ? await file.text() : contractText;

    onScanStart(filename);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("tools", JSON.stringify(getSelectedTools()));

      let res: Response;
      try {
        res = await fetch("/api/scan", { method: "POST", body: formData });
      } catch {
        throw new Error("Impossible de joindre le backend.");
      }

      const json = await res.json();
      if (res.status === 409) {
        throw new Error("Une analyse est déjà en cours sur le serveur. Attendez qu'elle se termine.");
      }
      if (!res.ok) throw new Error(json.detail ?? `Erreur HTTP ${res.status}`);

      const contract = reportToContract(json.report ?? json, filename, code, json.id ?? undefined);
      onResult(contract);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur inconnue";
      setErrorMsg(msg);
      onScanError(msg);
    } finally {
      onScanFinally();
    }
  }

  return (
    <form onSubmit={handleSubmit} className={`space-y-5 transition-opacity ${isGloballyScanning ? "opacity-60 pointer-events-none select-none" : ""}`}>

      {/* Package selector */}
      <div>
        <p className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-3">
          <Sparkles className="w-4 h-4 text-primary-500" />
          Type d&apos;analyse
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {PACKAGES.map(({ id, name, description, tools, icon: Icon, available }) => {
            const checked = selectedPackages.has(id);
            return (
              <button
                key={id}
                type="button"
                disabled={!available || isGloballyScanning}
                onClick={() => togglePackage(id)}
                className={`relative text-left flex items-start gap-3 px-4 py-3.5 rounded-xl border-2 transition-all ${
                  !available
                    ? "opacity-50 cursor-not-allowed border-slate-200 bg-slate-50"
                    : checked
                    ? "border-primary-400 bg-primary-50 shadow-sm"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                {/* Checkbox */}
                <div className={`mt-0.5 w-4 h-4 rounded border-2 shrink-0 flex items-center justify-center transition-all ${
                  checked ? "border-primary-500 bg-primary-500" : "border-slate-300 bg-white"
                }`}>
                  {checked && (
                    <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 10 10" fill="none">
                      <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                    <Icon className={`w-4 h-4 shrink-0 ${checked ? "text-primary-500" : "text-slate-400"}`} />
                    <span className="text-sm font-semibold text-slate-800">{name}</span>
                    {!available && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-200 text-slate-500 uppercase tracking-wide">
                        Bientôt
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed mb-2">{description}</p>
                  <div className="flex flex-wrap gap-1">
                    {tools.map((t) => (
                      <span key={t} className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${checked ? "bg-primary-100 text-primary-600" : "bg-slate-100 text-slate-500"}`}>
                        {TOOL_LABELS[t] ?? t}
                      </span>
                    ))}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* AI toggle */}
        <button
          type="button"
          onClick={toggleAi}
          className={`mt-3 w-full text-left flex items-start gap-3 px-4 py-3.5 rounded-xl border-2 transition-all ${
            aiSelected
              ? "border-primary-400 bg-primary-50 shadow-sm"
              : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
          }`}
        >
          <div className={`mt-0.5 w-4 h-4 rounded border-2 shrink-0 flex items-center justify-center transition-all ${
            aiSelected ? "border-primary-500 bg-primary-500" : "border-slate-300 bg-white"
          }`}>
            {aiSelected && (
              <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 10 10" fill="none">
                <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5 flex-wrap">
              <Bot className={`w-4 h-4 shrink-0 ${aiSelected ? "text-primary-500" : "text-slate-400"}`} />
              <span className="text-sm font-semibold text-slate-800">Intelligence Artificielle</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 uppercase tracking-wide">Nouveau</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed mb-2">
              Modèle GNN SafeContract — analyse le graphe CFG et fusionne ses prédictions avec les outils.
            </p>
            <div className="flex flex-wrap gap-1">
              {["GNN v6", "CodeBERT", "PyTorch"].map((t) => (
                <span key={t} className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${aiSelected ? "bg-primary-100 text-primary-600" : "bg-slate-100 text-slate-500"}`}>
                  {t}
                </span>
              ))}
            </div>
          </div>
        </button>
      </div>

      {/* File upload zone */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
          <Upload className="w-4 h-4 text-primary-500" />
          Importer un fichier .sol
        </label>
        {uploadedFile ? (
          <div className="flex items-center justify-between px-4 py-3 rounded-lg border border-primary-200 bg-primary-50">
            <span className="text-sm font-medium text-primary-700 truncate">{uploadedFile.name}</span>
            <button type="button" onClick={removeFile} className="ml-3 text-slate-400 hover:text-slate-600 shrink-0">
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="w-full flex flex-col items-center justify-center gap-2 px-4 py-6 rounded-lg border-2 border-dashed border-slate-200 hover:border-primary-300 hover:bg-slate-50 transition-colors"
          >
            <Upload className="w-5 h-5 text-slate-400" />
            <span className="text-sm text-slate-500">Cliquer pour sélectionner un fichier <span className="font-medium text-slate-600">.sol</span></span>
          </button>
        )}
        <input ref={fileInputRef} type="file" accept=".sol" onChange={handleFileChange} className="hidden" />
      </div>

      {!uploadedFile && (
        <>
          <div className="relative flex items-center">
            <div className="flex-1 border-t border-slate-200" />
            <span className="mx-3 text-xs text-slate-400 uppercase tracking-wide">ou</span>
            <div className="flex-1 border-t border-slate-200" />
          </div>
          <div>
            <label htmlFor="scan-code" className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <FileCode2 className="w-4 h-4 text-primary-500" />
              Coller le code Solidity
            </label>
            <textarea
              id="scan-code"
              value={contractText}
              onChange={(e) => setContractText(e.target.value)}
              rows={12}
              placeholder={"// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\n\ncontract MonContrat {\n    // ...\n}"}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent resize-y"
            />
          </div>
        </>
      )}

      {errorMsg && !isGloballyScanning && (
        <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-sm text-red-700">{errorMsg}</div>
      )}

      {!hasTools && !isGloballyScanning && (
        <p className="text-xs text-amber-600 text-center">
          Sélectionnez au moins un type d&apos;analyse.
        </p>
      )}

      <button
        type="submit"
        disabled={!hasInput || !hasTools || isGloballyScanning}
        className="w-full flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-md transition-colors"
      >
        {isGloballyScanning ? (
          <><Loader2 className="w-4 h-4 animate-spin" />Analyse en cours…</>
        ) : (
          <>Lancer l&apos;analyse<ArrowRight className="w-4 h-4" /></>
        )}
      </button>
    </form>
  );
}

// ─── helpers ────────────────────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score >= 80) return { text: "text-emerald-600", bg: "bg-emerald-500", ring: "#10b981" };
  if (score >= 50) return { text: "text-amber-500", bg: "bg-amber-400", ring: "#f59e0b" };
  return { text: "text-red-500", bg: "bg-red-500", ring: "#ef4444" };
}

function scoreLabel(score: number) {
  if (score >= 80) return "Sûr";
  if (score >= 50) return "Risque modéré";
  return "Critique";
}

function computeToolScore(issues: Issue[]): number {
  const c = issues.filter((i) => i.severity === "critical").length;
  const m = issues.filter((i) => i.severity === "medium").length;
  const l = issues.filter((i) => i.severity === "low").length;
  return Math.max(0, Math.min(100, 100 - c * 25 - m * 10 - l * 5));
}

function SeverityBadge({ s }: { s: Severity }) {
  const map = {
    critical: "bg-red-100 text-red-700 border-red-200",
    medium: "bg-amber-100 text-amber-700 border-amber-200",
    low: "bg-blue-100 text-blue-700 border-blue-200",
  };
  const labels = { critical: "Critique", medium: "Moyen", low: "Faible" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${map[s]}`}>
      {labels[s]}
    </span>
  );
}

function SeverityIcon({ s }: { s: Severity }) {
  if (s === "critical") return <ShieldX className="w-4 h-4 text-red-500 shrink-0" />;
  if (s === "medium") return <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />;
  return <Info className="w-4 h-4 text-blue-500 shrink-0" />;
}

// ─── Health Score gauge ──────────────────────────────────────────────────────

function HealthGauge({ score }: { score: number }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const { text, ring } = scoreColor(score);

  return (
    <div className="relative flex items-center justify-center w-36 h-36">
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r} fill="none"
          stroke={ring} strokeWidth="10"
          strokeDasharray={`${filled} ${circ}`}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 0.8s ease" }}
        />
      </svg>
      <div className="text-center">
        <span className={`text-3xl font-bold ${text}`}>{score}</span>
        <span className="block text-xs text-slate-400 mt-0.5">/ 100</span>
      </div>
    </div>
  );
}

// ─── Security Timeline ───────────────────────────────────────────────────────

function SecurityTimeline({ timeline }: { timeline: { date: string; score: number }[] }) {
  const W = 520;
  const H = 120;
  const pad = { l: 36, r: 16, t: 12, b: 28 };
  const iw = W - pad.l - pad.r;
  const ih = H - pad.t - pad.b;

  const xs = timeline.length === 1
    ? [pad.l + iw / 2]
    : timeline.map((_, i) => pad.l + (i / (timeline.length - 1)) * iw);
  const ys = timeline.map((p) => pad.t + ih - (p.score / 100) * ih);

  const pathD = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x} ${ys[i]}`).join(" ");
  const areaD = `${pathD} L ${xs[xs.length - 1]} ${H - pad.b} L ${xs[0]} ${H - pad.b} Z`;

  const first = timeline[0].score;
  const last = timeline[timeline.length - 1].score;
  const delta = last - first;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-700">Évolution du score de sécurité</h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${delta >= 0 ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"}`}>
          {delta >= 0 ? "+" : ""}{delta} pts depuis le début
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="tl-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2cbe88" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#2cbe88" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Y gridlines */}
        {[0, 25, 50, 75, 100].map((v) => {
          const y = pad.t + ih - (v / 100) * ih;
          return (
            <g key={v}>
              <line x1={pad.l} y1={y} x2={W - pad.r} y2={y} stroke="#e2e8f0" strokeWidth="1" />
              <text x={pad.l - 4} y={y + 4} textAnchor="end" fontSize="9" fill="#94a3b8">{v}</text>
            </g>
          );
        })}

        {/* Area fill */}
        <path d={areaD} fill="url(#tl-fill)" />

        {/* Line */}
        <path d={pathD} fill="none" stroke="#2cbe88" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Points + labels */}
        {timeline.map((p, i) => (
          <g key={i}>
            <circle cx={xs[i]} cy={ys[i]} r="4" fill="#2cbe88" stroke="white" strokeWidth="2" />
            <text x={xs[i]} y={H - pad.b + 14} textAnchor="middle" fontSize="9" fill="#64748b">{p.date}</text>
          </g>
        ))}
      </svg>
      <p className="mt-2 text-xs text-slate-500 text-center">
        Score passé de <strong>{first}/100</strong> à <strong>{last}/100</strong> en {timeline.length - 1} analyse{timeline.length > 2 ? "s" : ""}
      </p>
    </div>
  );
}

// ─── Code & Diagnostic ───────────────────────────────────────────────────────

function ToolScoreGrid({ contract }: { contract: Contract }) {
  const tools = contract.toolsUsed ?? [];
  if (tools.length === 0) return null;

  const staticToolsUsed = tools.filter((t) => STATIC_TOOLS.includes(t));
  const dynamicToolsUsed = tools.filter((t) => DYNAMIC_TOOLS.includes(t));

  const staticIssues = contract.issues.filter((i) => STATIC_TOOLS.includes(i.tool ?? ""));
  const dynamicIssues = contract.issues.filter((i) => DYNAMIC_TOOLS.includes(i.tool ?? ""));

  const hasStatic = staticToolsUsed.length > 0;
  const hasDynamic = dynamicToolsUsed.length > 0;

  const staticScore = hasStatic ? computeToolScore(staticIssues) : null;
  const dynamicScore = hasDynamic ? computeToolScore(dynamicIssues) : null;

  const packages = [
    hasStatic && {
      id: "statique",
      label: "Analyse Statique",
      score: staticScore!,
      tools: staticToolsUsed,
      issues: staticIssues,
      icon: Search,
    },
    hasDynamic && {
      id: "dynamique",
      label: "Analyse Dynamique",
      score: dynamicScore!,
      tools: dynamicToolsUsed,
      issues: dynamicIssues,
      icon: ScanSearch,
    },
  ].filter(Boolean) as { id: string; label: string; score: number; tools: string[]; issues: Issue[]; icon: React.ElementType }[];

  return (
    <div className="mb-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Scores par type d&apos;analyse</p>
        <span className="text-xs text-slate-400">Score global : <span className={`font-bold ${scoreColor(contract.score).text}`}>{contract.score}/100</span></span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {packages.map(({ id, label, score, tools: pkgTools, issues: pkgIssues, icon: Icon }) => {
          const { text, ring } = scoreColor(score);
          return (
            <div key={id} className="flex flex-col gap-2 px-4 py-3 rounded-lg bg-white border border-slate-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Icon className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs font-semibold text-slate-600">{label}</span>
                </div>
                <span className={`text-xl font-bold ${text}`}>{score}</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, backgroundColor: ring }} />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex flex-wrap gap-1">
                  {pkgTools.map((t) => {
                    const version = contract.toolsVersions?.[t];
                    return (
                      <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-medium" title={version ? `v${version}` : undefined}>
                        {TOOL_LABELS[t] ?? t}{version ? <span className="text-slate-400 font-normal"> v{version}</span> : null}
                      </span>
                    );
                  })}
                </div>
                <span className="text-[10px] text-slate-400">{pkgIssues.length} issue{pkgIssues.length !== 1 ? "s" : ""}</span>
              </div>
            </div>
          );
        })}
      </div>
      {/* Carte verdict IA */}
      {contract.aiVerdict && (
        <div className={`mt-3 px-4 py-3 rounded-lg border flex flex-col gap-2 ${
          contract.aiVerdict.verdict === "vulnerable"
            ? "bg-red-50 border-red-200"
            : "bg-emerald-50 border-emerald-200"
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Bot className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs font-semibold text-slate-600">Intelligence Artificielle — GNN v6</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide ${
                contract.aiVerdict.verdict === "vulnerable"
                  ? "bg-red-100 text-red-600"
                  : "bg-emerald-100 text-emerald-600"
              }`}>
                {contract.aiVerdict.verdict === "vulnerable" ? "Vulnérable" : "Sain"}
              </span>
              {/* Le score GNN mesure la confiance en la vulnérabilité (≠ score de sécurité).
                  On l'affiche explicitement comme niveau de risque, pas comme note de sécurité. */}
              {contract.aiVerdict.score > 0 && (
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  contract.aiVerdict.score >= 70
                    ? "bg-red-100 text-red-700"
                    : contract.aiVerdict.score >= 40
                    ? "bg-amber-100 text-amber-700"
                    : "bg-slate-100 text-slate-500"
                }`}>
                  Risque {contract.aiVerdict.score}%
                </span>
              )}
            </div>
          </div>
          {contract.aiVerdict.explanation && (
            <p className="text-xs text-slate-500 leading-relaxed">{contract.aiVerdict.explanation}</p>
          )}
        </div>
      )}

      {contract.toolsErrors && Object.keys(contract.toolsErrors).filter(k => k !== "ai").length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-medium text-slate-400">Non disponibles :</span>
          {Object.entries(contract.toolsErrors).filter(([k]) => k !== "ai").map(([tool, err]) => (
            <span key={tool} title={err} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-400 border border-slate-200">
              {TOOL_LABELS[tool] ?? tool}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function CodeDiagnostic({ contract }: { contract: Contract }) {
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const lines = contract.code.split("\n");
  const issueLines = new Set(contract.issues.map((i) => i.line));
  const totalLines = lines.length;

  const severityLineBg: Record<Severity, string> = {
    critical: "bg-red-500/10 border-l-2 border-red-500",
    medium: "bg-amber-400/10 border-l-2 border-amber-400",
    low: "bg-blue-400/10 border-l-2 border-blue-400",
  };

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 mb-3">Code & Diagnostic</h3>
      <ToolScoreGrid contract={contract} />
      <div className="flex gap-3">
        {/* Code panel */}
        <div className="flex-1 min-w-0 rounded-lg border border-slate-200 bg-slate-950 overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-800 bg-slate-900">
            <FileCode2 className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400 font-mono">{contract.name}</span>
          </div>
          <div className="overflow-auto max-h-80">
            <table className="w-full text-xs font-mono">
              <tbody>
                {lines.map((line, idx) => {
                  const lineNo = idx + 1;
                  const issue = contract.issues.find((i) => i.line === lineNo);
                  const bg = issue ? severityLineBg[issue.severity] : "";
                  return (
                    <tr
                      key={idx}
                      className={`group cursor-default ${bg} ${issue ? "cursor-pointer" : ""}`}
                      onClick={() => issue && setSelectedIssue(issue === selectedIssue ? null : issue)}
                    >
                      <td className="select-none w-10 px-3 py-0.5 text-slate-600 text-right border-r border-slate-800">
                        {lineNo}
                      </td>
                      <td className="px-3 py-0.5 text-slate-200 whitespace-pre">
                        {line || " "}
                      </td>
                      {issue && (
                        <td className="px-2 py-0.5 shrink-0">
                          <SeverityIcon s={issue.severity} />
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Heatmap minimap */}
        <div className="w-5 rounded border border-slate-200 bg-slate-100 relative overflow-hidden shrink-0" style={{ height: 320 }}>
          {contract.issues.map((issue, i) => {
            const topPct = (issue.line / totalLines) * 100;
            const color = issue.severity === "critical" ? "#ef4444" : issue.severity === "medium" ? "#f59e0b" : "#3b82f6";
            return (
              <div
                key={i}
                title={`Ligne ${issue.line} — ${issue.title}`}
                style={{ top: `${topPct}%`, backgroundColor: color }}
                className="absolute left-0 right-0 h-1.5 opacity-80 cursor-pointer hover:opacity-100 transition-opacity"
              />
            );
          })}
        </div>
      </div>

      {contract.issues.length === 0 && (
        <div className="mt-3 flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          Aucune vulnérabilité détectée — contrat sain.
        </div>
      )}

      {/* Issues grouped by tool */}
      {contract.issues.length > 0 && (() => {
        const toolOrder = Array.from(new Set(contract.issues.map((i) => i.tool ?? "unknown")));
        return (
          <div className="mt-4 space-y-4">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Vulnérabilités par outil</p>
            {toolOrder.map((tool) => {
              const toolIssues = contract.issues.filter((i) => (i.tool ?? "unknown") === tool);
              const toolScore = computeToolScore(toolIssues);
              const { text } = scoreColor(toolScore);
              return (
                <div key={tool}>
                  {/* Tool header */}
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-px flex-1 bg-slate-100" />
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs font-semibold text-slate-500">
                        {TOOL_LABELS[tool] ?? tool}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {toolIssues.length} issue{toolIssues.length !== 1 ? "s" : ""}
                      </span>
                      <span className={`text-xs font-bold ${text}`}>{toolScore}/100</span>
                    </div>
                    <div className="h-px flex-1 bg-slate-100" />
                  </div>
                  {/* Tool issues */}
                  <div className="space-y-1.5">
                    {toolIssues.map((issue, i) => (
                      <button
                        key={i}
                        onClick={() => setSelectedIssue(issue === selectedIssue ? null : issue)}
                        className={`w-full text-left flex items-start gap-3 px-3 py-2.5 rounded-lg border text-sm transition-colors ${
                          selectedIssue === issue ? "bg-slate-100 border-slate-300" : "bg-white border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <SeverityIcon s={issue.severity} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-slate-800">{issue.title}</span>
                            <SeverityBadge s={issue.severity} />
                            {issue.confirmedByGnn && (
                              <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
                                <Bot className="w-2.5 h-2.5" />
                                GNN ✓
                              </span>
                            )}
                            {issue.tool === "ai" && (
                              <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-700 border border-violet-200">
                                <Bot className="w-2.5 h-2.5" />
                                IA seule
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 mt-0.5 truncate">{issue.desc}</p>
                        </div>
                        <span className="text-xs text-slate-400 shrink-0">L.{issue.line}</span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        );
      })()}

      {/* Issue detail panel */}
      {selectedIssue && (
        <div className={`mt-3 p-4 rounded-lg border text-sm ${
          selectedIssue.severity === "critical"
            ? "bg-red-50 border-red-200"
            : selectedIssue.severity === "medium"
            ? "bg-amber-50 border-amber-200"
            : "bg-blue-50 border-blue-200"
        }`}>
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <SeverityIcon s={selectedIssue.severity} />
              <span className="font-medium text-slate-800">{selectedIssue.title}</span>
              <SeverityBadge s={selectedIssue.severity} />
              {selectedIssue.swcId && <span className="text-xs text-slate-400">{selectedIssue.swcId}</span>}
              {selectedIssue.confirmedByGnn && (
                <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
                  <Bot className="w-2.5 h-2.5" />
                  Confirmé par le GNN{selectedIssue.gnnConfidence ? ` · ${selectedIssue.gnnConfidence}` : ""}
                </span>
              )}
              {selectedIssue.tool === "ai" && (
                <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-700 border border-violet-200">
                  <Bot className="w-2.5 h-2.5" />
                  Détecté par l&apos;IA seule{selectedIssue.gnnConfidence ? ` · ${selectedIssue.gnnConfidence}` : ""}
                </span>
              )}
            </div>
            <span className="text-xs text-slate-500 shrink-0">Ligne {selectedIssue.line}</span>
          </div>
          <p className="mt-1.5 text-slate-600 text-xs leading-relaxed">{selectedIssue.desc}</p>
          {(selectedIssue.confirmedByGnn || selectedIssue.tool === "ai") && selectedIssue.gnnDescription && (
            <div className="mt-2 pt-2 border-t border-current/10">
              <p className="text-xs font-semibold text-slate-500 mb-0.5">Analyse GNN</p>
              <p className="text-xs text-slate-600 leading-relaxed">{selectedIssue.gnnDescription}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Contract card ───────────────────────────────────────────────────────────

function ContractCard({
  contract,
  selected,
  onClick,
}: {
  contract: Contract;
  selected: boolean;
  onClick: () => void;
}) {
  const { text, bg } = scoreColor(contract.score);
  const criticals = contract.issues.filter((i) => i.severity === "critical").length;

  return (
    <button
      onClick={onClick}
      className={`w-full text-left flex items-center gap-4 px-4 py-3 rounded-xl border transition-all ${
        selected
          ? "bg-primary-50 border-primary-300 ring-1 ring-primary-300/30"
          : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${bg} bg-opacity-15`}>
        <span className={`text-sm font-bold ${text}`}>{contract.score}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate">{contract.name}</p>
        <p className="text-xs text-slate-500">{contract.issues.length} issue{contract.issues.length !== 1 ? "s" : ""}{criticals > 0 ? ` · ${criticals} critique${criticals > 1 ? "s" : ""}` : ""}</p>
      </div>
      <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
    </button>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────────────────────

const NAV = [
  { id: "overview", label: "Vue d'ensemble", icon: LayoutDashboard },
  { id: "scan", label: "Nouvelle analyse", icon: ScanSearch },
  { id: "diagnostic", label: "Code & Diagnostic", icon: FileCode2 },
  { id: "analyses", label: "Analyses", icon: History },
];

// ─── Dashboard ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();

  // ── État de base ──────────────────────────────────────────────────────────
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [downloadingReport, setDownloadingReport] = useState<"pdf" | "markdown" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  // ── État global du scan (unique à la fois) ───────────────────────────────
  const [isScanning, setIsScanning] = useState(false);
  const [scanningFileName, setScanningFileName] = useState("");
  const [toast, setToast] = useState<ToastData | null>(null);
  // true = scan détecté au chargement de la page (pas démarré par l'utilisateur)
  // → active le polling pour détecter la fin du scan
  const [isResumedScan, setIsResumedScan] = useState(false);

  // ── Helper : recharge la liste des contrats depuis la DB ─────────────────
  const refreshContracts = useCallback(async (preferName?: string) => {
    try {
      const r = await fetch("/api/analyses");
      const data: RawAnalysis[] = await r.json();
      if (Array.isArray(data)) {
        const built = buildContracts(data);
        setContracts(built);
        setSelectedContract((prev) => {
          const byName = preferName ? built.find((b) => b.name === preferName) : null;
          const current = prev ? built.find((b) => b.name === prev.name) ?? null : null;
          return byName ?? current ?? built[0] ?? null;
        });
      }
    } catch { /* réseau indisponible, on garde l'état actuel */ }
  }, []);

  // ── État persisté en sessionStorage (survit au F5, effacé à fermeture onglet) ──
  const [activeSection, setActiveSectionState] = useState("overview");
  const [scanResult, setScanResultState] = useState<Contract | null>(null);

  function setActiveSection(s: string) {
    setActiveSectionState(s);
    sessionStorage.setItem("sc_active_section", s);
    // Rafraîchir la liste des contrats quand l'utilisateur visite ces onglets
    if (s === "overview" || s === "analyses") {
      refreshContracts();
    }
  }

  function setScanResult(c: Contract | null) {
    setScanResultState(c);
    if (c) sessionStorage.setItem("sc_scan_result", JSON.stringify(c));
    else sessionStorage.removeItem("sc_scan_result");
  }

  const handleScanStart = useCallback((filename: string) => {
    setIsScanning(true);
    setScanningFileName(filename);
    setIsResumedScan(false); // Scan lancé depuis cette session → pas de polling
    setScanResult(null); // Effacer le résultat précédent pour éviter qu'il réapparaisse sur erreur
  }, [setScanResult]);

  const handleScanError = useCallback((msg: string) => {
    setToast({ type: "error", msg: `Analyse échouée — ${msg.slice(0, 80)}`, key: Date.now() });
  }, []);

  const handleScanFinally = useCallback(() => {
    setIsScanning(false);
    setScanningFileName("");
  }, []);

  // ── Chargement initial ────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window !== "undefined" && localStorage.getItem("sc_auth") !== "admin") {
      router.replace("/connexion");
      return;
    }
    // Restaurer la section active et le dernier résultat de scan
    const savedSection = sessionStorage.getItem("sc_active_section");
    if (savedSection) setActiveSectionState(savedSection);
    const savedResult = sessionStorage.getItem("sc_scan_result");
    if (savedResult) {
      try { setScanResultState(JSON.parse(savedResult)); } catch { /* JSON invalide, ignoré */ }
    }
    // Vérifier si un scan tourne déjà sur le backend (cas du refresh pendant un scan)
    fetch("/api/scan")
      .then((r) => r.json())
      .then((data: { scanning?: boolean; filename?: string }) => {
        if (data.scanning) {
          setIsScanning(true);
          setScanningFileName(data.filename || "Analyse en cours sur le serveur…");
          setIsResumedScan(true); // Active le polling
        }
      })
      .catch(() => {});
    // Charger les analyses depuis MongoDB
    refreshContracts();
  }, [router, refreshContracts]);

  // ── Polling : détecte la fin d'un scan repris après refresh ──────────────
  // Ne s'active que si isResumedScan=true (scan détecté au chargement, non lancé par l'user)
  useEffect(() => {
    if (!isResumedScan) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch("/api/scan");
        const data: { scanning?: boolean; filename?: string } = await res.json();
        if (!data.scanning) {
          clearInterval(interval);
          setIsResumedScan(false);
          setIsScanning(false);
          setScanningFileName("");
          await refreshContracts();
          setToast({ type: "success", msg: "Analyse terminée — résultats mis à jour", key: Date.now() });
        }
      } catch { /* ignore — on réessaiera dans 3s */ }
    }, 3000);

    return () => clearInterval(interval);
  }, [isResumedScan, refreshContracts]);

  function handleLogout() {
    if (isScanning && !window.confirm(`Une analyse de "${scanningFileName}" est en cours. Se déconnecter l'annulera. Continuer ?`)) {
      return;
    }
    localStorage.removeItem("sc_auth");
    sessionStorage.removeItem("sc_active_section");
    sessionStorage.removeItem("sc_scan_result");
    router.push("/");
  }

  async function downloadReport(format: "pdf" | "markdown") {
    if (!selectedContract?.id || isScanning || downloadingReport !== null) return;
    setDownloadingReport(format);
    setDownloadError(null);
    try {
      const res = await fetch(`/api/analyses/${selectedContract.id}/rapport?format=${format}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: `Erreur HTTP ${res.status}` }));
        throw new Error(body.detail ?? `Erreur ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `rapport_${selectedContract.name.replace(".sol", "").replace(".vy", "")}.${format === "pdf" ? "pdf" : "md"}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      // Révoquer après un délai pour laisser le navigateur démarrer le téléchargement
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setDownloadingReport(null);
    }
  }

  async function handleScanResult(c: Contract) {
    setScanResult(c);
    setToast({ type: "success", msg: `Analyse terminée — ${c.name}`, key: Date.now() });
    await refreshContracts(c.name);
  }

  const { text: scoreText } = scoreColor(selectedContract?.score ?? 0);
  const criticals = selectedContract?.issues.filter((i) => i.severity === "critical").length ?? 0;
  const mediums = selectedContract?.issues.filter((i) => i.severity === "medium").length ?? 0;

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-white border-r border-slate-200 flex flex-col">
        <div className="h-16 flex items-center px-4 border-b border-slate-200">
          <Link href="/" className="flex items-center gap-2">
            <img src="/images/SafeContract-Logo.png" alt="SafeContract" className="h-7 w-auto" />
            <span
              className="font-bold text-sm tracking-tight"
              style={{ background: "linear-gradient(135deg, #2cbe88 0%, #152d5b 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}
            >
              SafeContract
            </span>
          </Link>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveSection(id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeSection === id
                  ? "bg-primary-50 text-primary-600"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="flex-1 text-left">{label}</span>
              {id === "scan" && isScanning && (
                <Loader2 className="w-3 h-3 animate-spin text-primary-500 shrink-0" />
              )}
            </button>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-slate-200">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            Déconnexion
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0">
          <h1 className="text-base font-semibold text-slate-900">
            {NAV.find((n) => n.id === activeSection)?.label}
          </h1>
          <div className="flex items-center gap-3">
            {isScanning && activeSection !== "scan" && (
              <button
                onClick={() => setActiveSection("scan")}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium hover:bg-blue-100 transition-colors"
              >
                <Loader2 className="w-3 h-3 animate-spin" />
                Analyse en cours…
              </button>
            )}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-primary-500 flex items-center justify-center text-white text-xs font-bold">A</div>
              <span className="text-sm font-medium text-slate-700">admin</span>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6">

          {/* ── Vue d'ensemble ───────────────────────────────────────────── */}
          {activeSection === "overview" && !selectedContract && (
            <div className="max-w-5xl mx-auto flex flex-col items-center justify-center gap-4 py-20 text-center">
              <ShieldAlert className="w-12 h-12 text-slate-300" />
              <p className="text-slate-500 text-sm">Aucune analyse dans la base de données.<br />Rendez-vous dans <strong>Nouvelle analyse</strong> pour scanner votre premier contrat.</p>
            </div>
          )}
          {activeSection === "overview" && selectedContract && (
            <div className="space-y-6 max-w-5xl mx-auto">

              {/* Health Score + stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Big health card */}
                <div className="md:col-span-1 bg-white rounded-xl border border-slate-200 p-6 flex flex-col items-center gap-3">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Health Score</p>
                  <HealthGauge score={selectedContract.score} />
                  <span className={`text-sm font-semibold ${scoreText}`}>{scoreLabel(selectedContract.score)}</span>
                  <p className="text-xs text-slate-400 text-center">{selectedContract.name}</p>
                  {/* Boutons rapport */}
                  {selectedContract.id && (
                    <div className="flex flex-col gap-1.5 mt-1 w-full">
                      <div className="flex gap-2">
                        <button
                          onClick={() => downloadReport("pdf")}
                          disabled={downloadingReport !== null || isScanning}
                          title={isScanning ? "Analyse en cours, veuillez patienter" : undefined}
                          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-md transition-colors"
                        >
                          {downloadingReport === "pdf" ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <FileDown className="w-3 h-3" />
                          )}
                          PDF
                        </button>
                        <button
                          onClick={() => downloadReport("markdown")}
                          disabled={downloadingReport !== null || isScanning}
                          title={isScanning ? "Analyse en cours, veuillez patienter" : undefined}
                          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 disabled:bg-slate-100 disabled:cursor-not-allowed rounded-md transition-colors"
                        >
                          {downloadingReport === "markdown" ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <FileDown className="w-3 h-3" />
                          )}
                          Markdown
                        </button>
                      </div>
                      {downloadError && (
                        <p className="text-xs text-red-500 text-center">{downloadError}</p>
                      )}
                    </div>
                  )}
                </div>

                {/* Stats */}
                <div className="md:col-span-2 grid grid-cols-2 gap-4">
                  <div className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col gap-1">
                    <ShieldX className="w-5 h-5 text-red-500 mb-1" />
                    <span className="text-2xl font-bold text-slate-900">{criticals}</span>
                    <span className="text-xs text-slate-500">Vulnérabilité{criticals !== 1 ? "s" : ""} critique{criticals !== 1 ? "s" : ""}</span>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col gap-1">
                    <AlertTriangle className="w-5 h-5 text-amber-500 mb-1" />
                    <span className="text-2xl font-bold text-slate-900">{mediums}</span>
                    <span className="text-xs text-slate-500">Risque{mediums !== 1 ? "s" : ""} modéré{mediums !== 1 ? "s" : ""}</span>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col gap-1">
                    <AlertCircle className="w-5 h-5 text-blue-500 mb-1" />
                    <span className="text-2xl font-bold text-slate-900">{selectedContract.issues.length}</span>
                    <span className="text-xs text-slate-500">Issues totales</span>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col gap-1">
                    <ShieldCheck className="w-5 h-5 text-emerald-500 mb-1" />
                    <span className="text-2xl font-bold text-slate-900">{contracts.filter((c) => c.score >= 80).length}</span>
                    <span className="text-xs text-slate-500">Contrats sains</span>
                  </div>
                </div>
              </div>

              {/* Timeline */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <SecurityTimeline timeline={selectedContract.timeline} />
              </div>

              {/* Contract selector */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Contrat analysé</p>
                <div className="space-y-2">
                  {contracts.map((c) => (
                    <ContractCard
                      key={c.id}
                      contract={c}
                      selected={c.id === selectedContract.id}
                      onClick={() => setSelectedContract(c)}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Nouvelle analyse — toujours monté pour conserver l'état du formulaire ── */}
          <div className={activeSection !== "scan" ? "hidden" : ""}>
            <div className="max-w-2xl mx-auto space-y-6">

              {/* Bannière scan en cours */}
              {isScanning && (
                <div className="flex items-center gap-4 px-5 py-4 rounded-xl border border-blue-200 bg-blue-50">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                    <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-blue-900">Analyse en cours…</p>
                    <p className="text-sm text-blue-700 truncate">{scanningFileName}</p>
                    <p className="text-xs text-blue-400 mt-0.5">
                      Vous pouvez naviguer librement — l&apos;analyse se poursuit en arrière-plan.
                    </p>
                  </div>
                </div>
              )}

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="mb-6">
                  <h2 className="text-base font-semibold text-slate-900">Analyser un contrat</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Importez un fichier <code className="font-mono text-primary-500">.sol</code> ou collez votre code. Le résultat sera ajouté à vos analyses.
                  </p>
                </div>
                <AnalyseScan
                  onResult={handleScanResult}
                  isGloballyScanning={isScanning}
                  onScanStart={handleScanStart}
                  onScanError={handleScanError}
                  onScanFinally={handleScanFinally}
                />
              </div>

              {/* Résultat de la dernière analyse (caché pendant un nouveau scan) */}
              {scanResult && !isScanning && (
                <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-700">Résultat — {scanResult.name}</h3>
                    <div className="flex items-center gap-3">
                      <HealthGauge score={scanResult.score} />
                    </div>
                  </div>
                  <CodeDiagnostic contract={scanResult} />
                  <div className="pt-2 border-t border-slate-100 flex gap-3">
                    <button
                      onClick={() => { setSelectedContract(scanResult); setActiveSection("diagnostic"); }}
                      className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 hover:bg-primary-100 rounded-md transition-colors"
                    >
                      <FileCode2 className="w-4 h-4" />
                      Voir dans Code & Diagnostic
                    </button>
                    <button
                      onClick={() => { setSelectedContract(scanResult); setActiveSection("overview"); }}
                      className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
                    >
                      <LayoutDashboard className="w-4 h-4" />
                      Voir dans la vue d&apos;ensemble
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ── Code & Diagnostic ───────────────────────────────────────── */}
          {activeSection === "diagnostic" && !selectedContract && (
            <div className="max-w-5xl mx-auto flex flex-col items-center justify-center gap-4 py-20 text-center">
              <ShieldAlert className="w-12 h-12 text-slate-300" />
              <p className="text-slate-500 text-sm">Aucun contrat sélectionné.</p>
            </div>
          )}
          {activeSection === "diagnostic" && selectedContract && (
            <div className="max-w-5xl mx-auto space-y-4">
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                {/* Contract picker inline */}
                <div className="flex items-center gap-2 flex-wrap mb-5">
                  {contracts.map((c) => {
                    const { bg } = scoreColor(c.score);
                    return (
                      <button
                        key={c.id}
                        onClick={() => setSelectedContract(c)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                          c.id === selectedContract.id
                            ? "bg-primary-50 border-primary-300 text-primary-700"
                            : "bg-white border-slate-200 text-slate-600 hover:border-slate-300"
                        }`}
                      >
                        <span className={`w-2 h-2 rounded-full ${bg}`} />
                        {c.name}
                      </button>
                    );
                  })}
                </div>
                <CodeDiagnostic contract={selectedContract} />
              </div>
            </div>
          )}

          {/* ── Analyses / Historique ───────────────────────────────────── */}
          {activeSection === "analyses" && (
            <div className="max-w-5xl mx-auto space-y-6">
              {/* Contracts */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Contrats pré-stockés</p>
                <div className="space-y-3">
                  {contracts.map((c) => {
                    const { text, ring } = scoreColor(c.score);
                    return (
                      <button
                        key={c.id}
                        onClick={() => { setSelectedContract(c); setActiveSection("diagnostic"); }}
                        className="w-full text-left flex items-center gap-4 px-4 py-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:bg-slate-50 bg-white transition-colors"
                      >
                        <div className="w-12 h-12 rounded-full border-4 flex items-center justify-center shrink-0" style={{ borderColor: ring }}>
                          <span className={`text-sm font-bold ${text}`}>{c.score}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="text-sm font-semibold text-slate-800">{c.name}</p>
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${c.score >= 80 ? "bg-emerald-50 text-emerald-600" : c.score >= 50 ? "bg-amber-50 text-amber-600" : "bg-red-50 text-red-600"}`}>
                              {scoreLabel(c.score)}
                            </span>
                          </div>
                          <p className="text-xs text-slate-500">
                            {c.issues.length} issue{c.issues.length !== 1 ? "s" : ""} · Dernière analyse le {c.lastAnalyzed}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <SecurityTimeline timeline={c.timeline} />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Historique des analyses */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Historique des analyses</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100">
                        <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">Contrat</th>
                        <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">Date</th>
                        <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">Score</th>
                        <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">Issues</th>
                        <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">Statut</th>
                      </tr>
                    </thead>
                    <tbody>
                      {contracts.flatMap((c) =>
                        c.timeline.map((t, i) => ({
                          contract: c.name,
                          date: t.date,
                          score: t.score,
                          issues: i === c.timeline.length - 1 ? c.issues.length : Math.floor(c.issues.length * (1 + (c.timeline.length - 1 - i) * 0.3)),
                          key: `${c.id}-${i}`,
                        }))
                      ).sort((a, b) => b.date.localeCompare(a.date)).map((row) => (
                        <tr key={row.key} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                          <td className="py-2.5 px-3 font-medium text-slate-800">{row.contract}</td>
                          <td className="py-2.5 px-3 text-slate-500 text-xs">{row.date}</td>
                          <td className="py-2.5 px-3">
                            <span className={`font-semibold ${scoreColor(row.score).text}`}>{row.score}/100</span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-600">{row.issues}</td>
                          <td className="py-2.5 px-3">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                              row.score >= 80 ? "bg-emerald-50 text-emerald-600" : row.score >= 50 ? "bg-amber-50 text-amber-600" : "bg-red-50 text-red-600"
                            }`}>
                              {scoreLabel(row.score)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {toast && <Toast key={toast.key} data={toast} onDismiss={() => setToast(null)} />}
    </div>
  );
}
