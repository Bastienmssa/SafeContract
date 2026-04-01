import tempfile
import os
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.mythril_service import analyze_contract
from app.database.mongodb import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


def _map_severity(s: str) -> str:
    l = s.lower()
    if l == "high":
        return "critical"
    if l == "medium":
        return "medium"
    return "low"


def _compute_score(issues: list) -> int:
    criticals = sum(1 for i in issues if i["severity"] == "critical")
    mediums = sum(1 for i in issues if i["severity"] == "medium")
    lows = sum(1 for i in issues if i["severity"] == "low")
    return max(0, min(100, 100 - criticals * 25 - mediums * 10 - lows * 5))


@router.post("/scan")
async def scan_contract(file: UploadFile = File(...)):
    if not file.filename.endswith(".sol"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un fichier .sol")

    contents = await file.read()
    code = contents.decode("utf-8", errors="replace")

    with tempfile.NamedTemporaryFile(suffix=".sol", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        report = analyze_contract(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

    raw_issues = report.get("issues", []) if isinstance(report, dict) else []
    issues = [
        {
            "line": i.get("lineno"),
            "severity": _map_severity(i.get("severity", "low")),
            "title": i.get("title", ""),
            "desc": i.get("description", ""),
            "swcId": f"SWC-{i.get('swc-id', '')}",
        }
        for i in raw_issues
    ]
    score = _compute_score(issues)

    inserted_id = None
    db = get_db()
    if db is not None:
        try:
            result = await db.analyses.insert_one({
                "filename": file.filename,
                "code": code,
                "score": score,
                "issues": issues,
                "raw_report": report,
                "analyzed_at": datetime.utcnow(),
                "status": "completed",
            })
            inserted_id = str(result.inserted_id)
        except Exception as e:
            logger.warning("MongoDB insert failed: %s", e)

    return {
        "status": "completed",
        "id": inserted_id,
        "report": report,
    }
