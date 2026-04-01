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
from app.services.aggregator import aggregate
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

    # Outils demandés par le client (mythril toujours inclus)
    requested: Optional[set] = None
    if tools:
        try:
            requested = set(json.loads(tools))
            requested.add("mythril")  # toujours obligatoire
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

    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(_run_tool, name, fn, tmp_path): name
                for name, fn, _ in tools  # type: ignore[misc]
            }
            for future in as_completed(futures):
                tool_name, result = future.result()
                tool_results[tool_name] = result
                logger.info("Outil %s terminé — %d issues", tool_name, len(result.get("issues", [])))
    finally:
        os.unlink(tmp_path)

    # ── Versions des outils utilisés ─────────────────────────────────────
    tools_versions: dict = {}
    for name, _fn, vfn in tools:  # type: ignore[misc]
        if not tool_results.get(name, {}).get("error"):
            tools_versions[name] = vfn()

    # ── Agrégation des résultats ──────────────────────────────────────────
    report = aggregate(tool_results)
    report["tools_versions"] = tools_versions

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
