import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import findings, health, scan
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.core.pipeline import ScanPipeline
from app.models.finding import FindingRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quorom")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    settings = get_settings()
    if settings.quorom_mode == "mock":
        db = SessionLocal()
        try:
            count = db.query(FindingRecord).count()
            if count == 0:
                logger.info("Mock mode: seeding findings via scan pipeline")
                ScanPipeline(settings).run(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="Quorom",
    description="Autonomous AWS cost + reliability agent (Detect → Reason for Day 1)",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(findings.router, prefix="/api")
app.include_router(scan.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"name": "Quorom", "docs": "/docs", "health": "/health"}
