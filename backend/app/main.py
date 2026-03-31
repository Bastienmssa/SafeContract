from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.scan import router as scan_router
from app.api.analyses import router as analyses_router
from app.database.mongodb import connect_db, close_db

app = FastAPI(title="SafeContract API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await connect_db()


@app.on_event("shutdown")
async def shutdown():
    await close_db()


app.include_router(scan_router)
app.include_router(analyses_router)
