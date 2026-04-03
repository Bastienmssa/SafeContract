import tempfile
import os
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.mythril_service import analyze_contract as mythril_analyze, get_version as mythril_version
from app.services.slither_service import analyze_contract as slither_analyze, get_version as slither_version
from app.services.solhint_service import analyze_contract as solhint_analyze, get_version as solhint_version
from app.services.echidna_service import analyze_contract as echidna_analyze, get_version as echidna_version
from app.services.foundry_service import analyze_contract as foundry_analyze, get_version as foundry_version
from app.services.aggregator import aggregate, normalize_issue, compute_score, compute_score_weighted
from app.services import ai_service
from app.database.mongodb import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".sol", ".vy"}


def _run_tool(name: str, fn, contract_path: str) -> tuple[str, dict]:
    """Exécute un outil d'analyse et retourne (nom, résultat)."""
    try:
        result = fn(contract_path)
        return name, result
    except Exception as exc:
        logger.warning("Outil %s a échoué : %s", name, exc)
        return name, {"issues": [], "error": str(exc)}


@router.post("/scan")
async def scan_contract(
    file: UploadFile = File(...),
    tools: Optional[str] = Form(default=None),
):
    # ── Validation de l'extension ─────────────────────────────────────────
    filename = file.filename or "contract.sol"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension non supportée '{ext}'. Fichiers acceptés : .sol, .vy",
        )

    # Outils demandés par le client.
    # None = tous les outils disponibles.
    # Liste explicite = seulement ces outils (y compris "ai" seul sans outil statique/dynamique).
    requested: Optional[set] = None
    if tools:
        try:
            requested = set(json.loads(tools))
        except Exception:
            requested = None

    contents = await file.read()
    code = contents.decode("utf-8", errors="replace")

    # ── Écriture dans un fichier temporaire ──────────────────────────────
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    # ── Lancement des outils en parallèle ────────────────────────────────
    # Mythril et Slither supportent .sol et .vy
    # Solhint, Echidna, Foundry uniquement .sol
    all_tools = [
        ("mythril", mythril_analyze, mythril_version),
        ("slither", slither_analyze, slither_version),
    ]
    if ext == ".sol":
        all_tools += [
            ("solhint", solhint_analyze, solhint_version),
            ("echidna", echidna_analyze, echidna_version),
            ("foundry", foundry_analyze, foundry_version),
        ]

    tools = [(name, fn, vfn) for name, fn, vfn in all_tools if requested is None or name in requested]  # type: ignore[assignment]

    tool_results: dict = {}
    report: dict = {}

    try:
        # ── Outils statiques en parallèle ────────────────────────────────────
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(_run_tool, name, fn, tmp_path): name
                for name, fn, _ in tools  # type: ignore[misc]
            }
            for future in as_completed(futures):
                tool_name, result = future.result()
                tool_results[tool_name] = result
                logger.info("Outil %s terminé — %d issues", tool_name, len(result.get("issues", [])))

        # ── Versions des outils utilisés ─────────────────────────────────────
        tools_versions: dict = {}
        for name, _fn, vfn in tools:  # type: ignore[misc]
            if not tool_results.get(name, {}).get("error"):
                tools_versions[name] = vfn()

        # ── Agrégation des résultats ──────────────────────────────────────────
        report = aggregate(tool_results)
        report["tools_versions"] = tools_versions

        # ── Analyse IA (après les outils, avant suppression du fichier) ───────
        # L'IA reçoit le fichier .sol + les issues normalisées des outils.
        # Elle retourne un verdict indépendant et peut ajouter ses propres issues.
        ai_requested = requested is None or "ai" in (requested or set())
        if ai_requested:
            if ai_service.is_available():
                try:
                    ai_result = ai_service.analyze_contract(tmp_path, report["issues"])

                    if ai_result.get("ai_issues"):
                        new_issues_added = False
                        for raw in ai_result["ai_issues"]:
                            gnn_level = raw.get("gnn_level", "POTENTIAL")

                            if gnn_level == "CONFIRMED":
                                # Marquer les issues existantes qui correspondent à ce finding
                                # sans créer de doublon. On cherche par ligne ET par swcId/title.
                                confirmed_line  = raw.get("line")
                                confirmed_swc   = raw.get("swcId", "")
                                confirmed_outils = raw.get("outils", [])
                                for issue in report["issues"]:
                                    line_match  = issue.get("line") == confirmed_line
                                    tool_match  = issue.get("tool") in confirmed_outils if confirmed_outils else True
                                    swc_match   = (issue.get("swcId", "") == confirmed_swc) if confirmed_swc else True
                                    if line_match and (tool_match or swc_match):
                                        issue["confirmedByGnn"]     = True
                                        issue["gnnConfidence"]      = raw.get("confidence", "")
                                        issue["gnnDescription"]     = raw.get("description", "")

                            else:
                                # POTENTIAL : nouvelle issue détectée par le GNN seul
                                normalized = normalize_issue(raw, "ai")
                                normalized["gnnConfidence"] = raw.get("confidence", "")
                                report["issues"].append(normalized)
                                new_issues_added = True

                        # Recalcul du score avec pondération GNN (CONFIRMED ×1.5)
                        # Fait après le marquage, qu'il y ait eu ou non de nouvelles issues.
                        severity_order = {"critical": 0, "medium": 1, "low": 2}
                        report["issues"].sort(key=lambda i: severity_order.get(i["severity"], 3))
                        report["score"] = compute_score_weighted(report["issues"])
                        report["summary"] = {
                            "critical": sum(1 for i in report["issues"] if i["severity"] == "critical"),
                            "medium":   sum(1 for i in report["issues"] if i["severity"] == "medium"),
                            "low":      sum(1 for i in report["issues"] if i["severity"] == "low"),
                            "total":    len(report["issues"]),
                        }

                    report["ai_verdict"] = {
                        "verdict":     ai_result.get("verdict"),
                        "score":       ai_result.get("score"),
                        "explanation": ai_result.get("explanation"),
                    }
                    report["tools_used"].append("ai")
                    report["tools_versions"]["ai"] = ai_service.get_version()

                except NotImplementedError as exc:
                    logger.info("IA non encore branchée : %s", exc)
                    report["tools_errors"]["ai"] = "AI model not yet implemented"
                except Exception as exc:
                    logger.warning("Analyse IA échouée : %s", exc)
                    report["tools_errors"]["ai"] = str(exc)
            else:
                if requested is not None and "ai" in requested:
                    report["tools_errors"]["ai"] = "AI model non disponible (is_available() == False)"

    finally:
        os.unlink(tmp_path)

    # ── Sauvegarde en base ────────────────────────────────────────────────
    inserted_id = None
    db = get_db()
    if db is not None:
        try:
            result_db = await db.analyses.insert_one({
                "filename": filename,
                "code": code,
                "score": report["score"],
                "issues": report["issues"],
                "summary": report["summary"],
                "tools_used": report["tools_used"],
                "tools_errors": report["tools_errors"],
                "tools_versions": report.get("tools_versions", {}),
                "ai_verdict": report.get("ai_verdict"),
                "raw_tool_results": tool_results,
                "analyzed_at": datetime.utcnow(),
                "status": "completed",
            })
            inserted_id = str(result_db.inserted_id)
        except Exception as exc:
            logger.warning("MongoDB insert failed: %s", exc)

    return {
        "status": "completed",
        "id": inserted_id,
        "report": report,
    }
