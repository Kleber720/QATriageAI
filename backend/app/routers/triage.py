from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_triage_service
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ExamplePreset,
    GenerateRequest,
    QATicket,
)
from app.services.knowledge_loader import get_example_presets
from app.services.llm.base import (
    LLMModelNotFoundError,
    LLMResponseParseError,
    LLMUnavailableError,
)
from app.services.triage_service import TriageService

router = APIRouter(prefix="/api/triage", tags=["triage"])


@router.get("/examples", response_model=list[ExamplePreset])
async def list_examples() -> list[ExamplePreset]:
    return get_example_presets()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_report(
    payload: AnalyzeRequest,
    service: TriageService = Depends(get_triage_service),
) -> AnalyzeResponse:
    try:
        return await service.analyze(payload.report_text)
    except (LLMUnavailableError, LLMModelNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMResponseParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/generate", response_model=QATicket)
async def generate_ticket(
    payload: GenerateRequest,
    service: TriageService = Depends(get_triage_service),
) -> QATicket:
    try:
        return await service.generate(payload)
    except (LLMUnavailableError, LLMModelNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMResponseParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
