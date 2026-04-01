"use client";

import { useState, useRef } from "react";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { Upload, FileCode, ArrowRight, CheckCircle, X, Loader2 } from "lucide-react";

type AnalysisState = "idle" | "loading" | "done" | "error";

export default function FreeAnalysePage() {
  const [contractText, setContractText] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [state, setState] = useState<AnalysisState>("idle");
  const [result, setResult] = useState<unknown>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasInput = uploadedFile !== null || contractText.trim().length > 0;

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
    if (!hasInput) return;

    setState("loading");
    setResult(null);
    setErrorMsg("");

    try {
      let file: File;

      if (uploadedFile) {
        file = uploadedFile;
      } else {
        file = new File([contractText], "contract.sol", { type: "text/plain" });
      }

      const formData = new FormData();
      formData.append("file", file);

      let res: Response;
      try {
        res = await fetch("/api/scan", {
          method: "POST",
          body: formData,
        });
      } catch {
        throw new Error("Impossible de joindre le serveur. Vérifiez que le backend est démarré.");
      }

      const raw = await res.text();
      let json: any = null;

      try {
        json = JSON.parse(raw);
      } catch {
        json = null;
      }

      if (!res.ok) {
        if (json?.detail) {
          throw new Error(json.detail);
        }
        throw new Error(`Erreur HTTP ${res.status}: ${raw.slice(0, 200)}`);
      }

      if (json === null) {
        throw new Error(
          "La route /scan n'a pas renvoye du JSON (HTML recu). Verifiez que la requete passe bien par Zuplo et que la route POST /scan est active."
        );
      }

      setResult(json);
      setState("done");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Erreur inconnue");
      setState("error");
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Navbar />
      <main className="flex-1 px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-10">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-primary-50 text-primary-600 border border-primary-100 mb-4">
              <CheckCircle className="w-3.5 h-3.5" />
              Analyse gratuite — aucune inscription requise
            </span>
            <h1 className="text-3xl sm:text-4xl font-semibold text-slate-900 tracking-tight">
              Analysez votre{" "}
              <span className="text-primary-500">Smart Contract</span>
            </h1>
            <p className="mt-4 text-base text-slate-600 leading-relaxed">
              Importez un fichier <code className="text-primary-500 font-mono">.sol</code> ou
              collez votre code Solidity. Notre moteur Mythril détecte les
              vulnérabilités connues via Mythril, Slither, Solhint et plus.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Zone d'upload fichier */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
                <Upload className="w-4 h-4 text-primary-500" />
                Importer un fichier .sol
              </label>

              {uploadedFile ? (
                <div className="flex items-center justify-between px-4 py-3 rounded-lg border border-primary-200 bg-primary-50">
                  <span className="text-sm font-medium text-primary-700 truncate">
                    {uploadedFile.name}
                  </span>
                  <button
                    type="button"
                    onClick={removeFile}
                    className="ml-3 text-slate-400 hover:text-slate-600 shrink-0"
                  >
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
                  <span className="text-sm text-slate-500">
                    Cliquer pour sélectionner un fichier{" "}
                    <span className="font-medium text-slate-600">.sol</span>
                  </span>
                </button>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept=".sol"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            {/* Séparateur */}
            {!uploadedFile && (
              <>
                <div className="relative flex items-center">
                  <div className="flex-1 border-t border-slate-200" />
                  <span className="mx-3 text-xs text-slate-400 uppercase tracking-wide">ou</span>
                  <div className="flex-1 border-t border-slate-200" />
                </div>

                {/* Textarea */}
                <div>
                  <label
                    htmlFor="contract"
                    className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2"
                  >
                    <FileCode className="w-4 h-4 text-primary-500" />
                    Coller le code Solidity
                  </label>
                  <textarea
                    id="contract"
                    value={contractText}
                    onChange={(e) => setContractText(e.target.value)}
                    rows={14}
                    placeholder={"// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\n\ncontract MonContrat {\n    // Collez votre code ici...\n}"}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent resize-y"
                  />
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={!hasInput || state === "loading"}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-md transition-colors border border-primary-500 disabled:border-slate-300"
            >
              {state === "loading" ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyse en cours…
                </>
              ) : (
                <>
                  Lancer l&apos;analyse
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Résultat JSON brut */}
          {state === "done" && result !== null && (
            <div className="mt-10">
              <h2 className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-primary-500" />
                Résultat d&apos;analyse
              </h2>
              <pre className="w-full overflow-auto rounded-lg border border-slate-200 bg-slate-950 text-slate-100 px-4 py-4 text-xs font-mono leading-relaxed">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}

          {/* Erreur */}
          {state === "error" && (
            <div className="mt-6 p-4 rounded-lg border border-red-200 bg-red-50">
              <p className="text-sm text-red-700 font-medium">Erreur</p>
              <p className="text-sm text-red-600 mt-1">{errorMsg}</p>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
