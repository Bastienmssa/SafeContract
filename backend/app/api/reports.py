"""
backend/app/api/reports.py

Endpoints FastAPI pour le téléchargement des rapports d'audit.
"""

import io
import base64
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from bson import ObjectId

from app.database.mongodb import get_db
from app.services.report_generator import generer_rapport

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyses", tags=["rapports"])


@router.get("/{id}/rapport")
async def telecharger_rapport(
    id: str,
    format: str = Query(default="pdf", enum=["pdf", "markdown", "both"]),
):
    """
    Génère et télécharge le rapport d'audit pour une analyse existante.

    Paramètres
    ----------
    id     : ObjectId MongoDB de l'analyse
    format : "pdf" | "markdown" | "both"
             - "pdf"      → téléchargement PDF direct
             - "markdown" → téléchargement fichier .md direct
             - "both"     → JSON { "markdown": str, "pdf_base64": str }
    """
    # --- Validation de l'ID ---
    try:
        obj_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID d'analyse invalide.")

    # --- Récupération depuis MongoDB ---
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Base de données indisponible.")

    try:
        analyse = await db.analyses.find_one({"_id": obj_id})
    except Exception as e:
        logger.error(f"[Rapport] Erreur MongoDB : {e}")
        raise HTTPException(status_code=503, detail="Erreur lors de la récupération de l'analyse.")

    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")

    # Convertir ObjectId en str pour la sérialisation JSON interne
    analyse["_id"] = str(analyse["_id"])

    # --- Génération du rapport ---
    try:
        result = generer_rapport(analyse)
    except Exception as e:
        logger.exception(f"[Rapport] Erreur génération : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération : {e}")

    if result.get("erreur"):
        raise HTTPException(status_code=500, detail=result["erreur"])

    nom_fichier = analyse.get("filename", "contrat").replace(".sol", "").replace(".vy", "")

    # --- Réponse selon le format demandé ---
    if format == "pdf":
        if not result.get("pdf_bytes"):
            raise HTTPException(
                status_code=501,
                detail="PDF indisponible. Vérifier que weasyprint est installé (pip install weasyprint)."
            )
        return StreamingResponse(
            io.BytesIO(result["pdf_bytes"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="rapport_{nom_fichier}.pdf"',
                "Content-Length": str(len(result["pdf_bytes"])),
            },
        )

    if format == "markdown":
        md_bytes = result["markdown"].encode("utf-8")
        return StreamingResponse(
            io.BytesIO(md_bytes),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="rapport_{nom_fichier}.md"',
                "Content-Length": str(len(md_bytes)),
            },
        )

    # format == "both"
    pdf_b64 = (
        base64.b64encode(result["pdf_bytes"]).decode("utf-8")
        if result.get("pdf_bytes")
        else None
    )
    return JSONResponse({
        "markdown":   result["markdown"],
        "pdf_base64": pdf_b64,
        "filename":   nom_fichier,
    })
