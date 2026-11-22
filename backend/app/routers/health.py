from fastapi import APIRouter, Depends

from app.dependencies import get_triage_service
from app.models.schemas import HealthResponse
from app.services.triage_service import TriageService

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    service: TriageService = Depends(get_triage_service),
) -> HealthResponse:
    return await service.check_health()
