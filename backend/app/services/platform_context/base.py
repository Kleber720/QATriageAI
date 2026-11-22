from abc import ABC, abstractmethod

from app.models.schemas import PlatformContextData, PlatformSessionSummary


class PlatformContextProvider(ABC):
    @abstractmethod
    def list_sessions(self) -> list[PlatformSessionSummary]:
        ...

    @abstractmethod
    def lookup_session(self, session_id: str) -> PlatformContextData | None:
        ...
