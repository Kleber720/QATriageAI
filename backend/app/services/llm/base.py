from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.models.schemas import HealthResponse

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(Exception):
    pass


class LLMModelNotFoundError(Exception):
    pass


class LLMResponseParseError(Exception):
    pass


class LLMProvider(ABC):
    @abstractmethod
    async def check_health(self) -> HealthResponse:
        ...

    @abstractmethod
    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        ...
