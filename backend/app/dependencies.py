from functools import lru_cache

from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.platform_context.base import PlatformContextProvider
from app.services.platform_context.mock_logs_provider import MockLogsProvider
from app.services.triage_service import TriageService


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )


@lru_cache(maxsize=1)
def get_platform_context_provider() -> PlatformContextProvider:
    return MockLogsProvider()


def get_triage_service() -> TriageService:
    return TriageService(
        llm=get_llm_provider(),
        platform_provider=get_platform_context_provider(),
    )
