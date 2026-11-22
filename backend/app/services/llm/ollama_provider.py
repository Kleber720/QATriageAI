import json
import re
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.models.schemas import HealthResponse
from app.services.llm.base import (
    LLMModelNotFoundError,
    LLMProvider,
    LLMResponseParseError,
    LLMUnavailableError,
)

T = TypeVar("T", bound=BaseModel)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json_string(raw: str) -> str:
    stripped = raw.strip()
    fence_match = _JSON_BLOCK_RE.search(stripped)
    if fence_match:
        return fence_match.group(1).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def _is_model_installed(configured: str, installed: list[str]) -> bool:
    if configured in installed:
        return True
    if ":" not in configured:
        return f"{configured}:latest" in installed or any(
            m.split(":")[0] == configured for m in installed
        )
    return False


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def check_health(self) -> HealthResponse:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, OSError, ValueError) as exc:
            return HealthResponse(
                status="degraded",
                ollama_online=False,
                ollama_base_url=self.base_url,
                configured_model=self.model,
                model_available=False,
                available_models=[],
                message=(
                    f"Ollama offline ou inacessível em {self.base_url}. "
                    f"Abra o Ollama no Windows para habilitar a IA local ({type(exc).__name__})."
                ),
            )

        models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        model_available = _is_model_installed(self.model, models)
        if not model_available:
            return HealthResponse(
                status="degraded",
                ollama_online=True,
                ollama_base_url=self.base_url,
                configured_model=self.model,
                model_available=False,
                available_models=models,
                message=(
                    f"Ollama ativo, mas o modelo '{self.model}' ainda não foi baixado. "
                    f"Execute: ollama pull {self.model}"
                ),
            )

        return HealthResponse(
            status="ok",
            ollama_online=True,
            ollama_base_url=self.base_url,
            configured_model=self.model,
            model_available=True,
            available_models=models,
            message=f"Ollama local pronto com '{self.model}'.",
        )

    async def _post_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        format_param: dict | str,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": format_param,
            "options": {
                "temperature": 0.15,
                "num_ctx": 8192,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMUnavailableError(
                f"Tempo limite excedido ({self.timeout_seconds}s) aguardando resposta do Ollama local."
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise LLMUnavailableError(
                f"Não foi possível conectar ao Ollama em {self.base_url}. Verifique se o serviço está rodando."
            ) from exc

        if resp.status_code == 404:
            raise LLMModelNotFoundError(
                f"Modelo '{self.model}' não encontrado no Ollama. Execute: ollama pull {self.model}"
            )
        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Ollama returned HTTP {resp.status_code}: {resp.text}",
                request=resp.request,
                response=resp,
            )

        data = resp.json()
        return data.get("message", {}).get("content", "")

    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        schema = response_model.model_json_schema()

        try:
            raw_content = await self._post_chat(system_prompt, user_prompt, schema)
            cleaned = _extract_json_string(raw_content)
            return response_model.model_validate_json(cleaned)
        except (LLMUnavailableError, LLMModelNotFoundError):
            raise
        except (httpx.HTTPStatusError, ValidationError, ValueError) as first_err:
            schema_str = json.dumps(schema, ensure_ascii=False)
            fallback_prompt = (
                f"{user_prompt}\n\n"
                "ATENÇÃO: Responda APENAS com um objeto JSON válido seguindo exatamente este JSON Schema:\n"
                f"{schema_str}"
            )
            try:
                raw_retry = await self._post_chat(system_prompt, fallback_prompt, "json")
                cleaned_retry = _extract_json_string(raw_retry)
                return response_model.model_validate_json(cleaned_retry)
            except (LLMUnavailableError, LLMModelNotFoundError):
                raise
            except Exception as second_err:
                raise LLMResponseParseError(
                    f"O modelo '{self.model}' não retornou um JSON válido conforme o schema esperado. "
                    f"Detalhes: {first_err} | Retry: {second_err}"
                ) from second_err
