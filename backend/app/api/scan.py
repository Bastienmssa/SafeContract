import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.services.mythril_service import analyze_contract

router = APIRouter()


@router.post("/scan")
async def scan_contract(file: UploadFile = File(...)):
    if not file.filename.endswith(".sol"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un fichier .sol")

    contents = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".sol", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        report = analyze_contract(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

    return {
        "status": "completed",
        "report": report
    }