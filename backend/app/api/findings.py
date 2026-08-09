from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.finding import FindingOut, FindingRecord

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=list[FindingOut])
def list_findings(db: Session = Depends(get_db)) -> list[FindingRecord]:
    return (
        db.query(FindingRecord)
        .order_by(FindingRecord.created_at.desc())
        .all()
    )


@router.get("/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: int, db: Session = Depends(get_db)) -> FindingRecord:
    record = db.query(FindingRecord).filter(FindingRecord.id == finding_id).first()
    if record is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Finding not found")
    return record
