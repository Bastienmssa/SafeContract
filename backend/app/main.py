from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.scan import router as scan_router

app = FastAPI(title="SafeContract API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan_router)