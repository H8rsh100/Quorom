from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "quorom",
        "mode": settings.quorom_mode,
        "dry_run": settings.dry_run,
        "tag_filter": f"{settings.aws_sandbox_tag_key}={settings.aws_sandbox_tag_value}",
    }
