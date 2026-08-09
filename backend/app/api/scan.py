from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.pipeline import ScanPipeline
from app.db import get_db
from app.models.finding import FindingOut

router = APIRouter(prefix="/scan", tags=["scan"])


class ScanResult(BaseModel):
    created: int
    findings: list[FindingOut]


@router.post("", response_model=ScanResult)
def run_scan(db: Session = Depends(get_db)) -> ScanResult:
    """Trigger Detect → Reason → Persist. Read-only toward AWS."""
    records = ScanPipeline().run(db)
    return ScanResult(created=len(records), findings=records)
