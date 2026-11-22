from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_platform_context_provider
from app.models.schemas import (
    PlatformContextData,
    PlatformSessionSummary,
    RawLogParseRequest,
)
from app.services.platform_context.base import PlatformContextProvider
from app.services.platform_context.raw_log_parser import parse_raw_log

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/sessions", response_model=list[PlatformSessionSummary])
async def list_log_sessions(
    provider: PlatformContextProvider = Depends(get_platform_context_provider),
) -> list[PlatformSessionSummary]:
    return provider.list_sessions()


@router.get("/sessions/{session_id}", response_model=PlatformContextData)
async def lookup_log_session(
    session_id: str,
    provider: PlatformContextProvider = Depends(get_platform_context_provider),
) -> PlatformContextData:
    found = provider.lookup_session(session_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessão '{session_id}' não encontrada nos logs simulados.",
        )
    return found


@router.post("/parse", response_model=PlatformContextData)
async def parse_log_text(payload: RawLogParseRequest) -> PlatformContextData:
    return parse_raw_log(payload.raw_log_text)
