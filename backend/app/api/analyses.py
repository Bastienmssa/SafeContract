from fastapi import APIRouter, HTTPException
from bson import ObjectId
from app.database.mongodb import get_db

router = APIRouter()


def _serialize(doc: dict) -> dict:
    analyzed_at = doc.get("analyzed_at")
    return {
        "id": str(doc["_id"]),
        "filename": doc.get("filename", ""),
        "code": doc.get("code", ""),
        "score": doc.get("score", 0),
        "issues": doc.get("issues", []),
        "tools_used": doc.get("tools_used", []),
        "tools_errors": doc.get("tools_errors", {}),
        "analyzed_at": analyzed_at.isoformat() if hasattr(analyzed_at, "isoformat") else str(analyzed_at),
        "status": doc.get("status", "completed"),
    }


@router.get("/analyses")
async def list_analyses():
    db = get_db()
    if db is None:
        return []
    try:
        cursor = db.analyses.find().sort("analyzed_at", -1)
        return [_serialize(doc) async for doc in cursor]
    except Exception:
        return []


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Base de données non disponible")
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID invalide")
    try:
        doc = await db.analyses.find_one({"_id": oid})
    except Exception:
        raise HTTPException(status_code=503, detail="Base de données non disponible")
    if not doc:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    return _serialize(doc)
