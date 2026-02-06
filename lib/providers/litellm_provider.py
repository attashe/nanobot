"""OpenAI-compatible provider using httpx.

All supported backends (OpenRouter, vLLM, Moonshot/Kimi) expose the
standard POST /v1/chat/completions endpoint, so a single httpx client
covers all of them.
"""

import json
from typing import Any

import httpx
from loguru import logger

from lib.providers.base import LLMProvider, LLMResponse, ToolCallRequest

# Default base URLs per provider
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_MOONSHOT_BASE = "https://api.moonshot.cn/v1"


class LiteLLMProvider(LLMProvider):
    """OpenAI-compatible chat completions provider (no litellm dependency)."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str = "anthropic/claude-opus-4-5",
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model

        # Resolve the actual base URL
        self._base_url = self._resolve_base_url(api_key, api_base, default_model)

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
            },
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    @staticmethod
    def _resolve_base_url(
        api_key: str | None, api_base: str | None, model: str
    ) -> str:
        """Pick the right base URL from explicit config or model name heuristics."""
        if api_base:
            return api_base.rstrip("/")
        if api_key and api_key.startswith("sk-or-"):
            return _OPENROUTER_BASE
        ml = model.lower()
        if "moonshot" in ml or "kimi" in ml:
            return _MOONSHOT_BASE
        # OpenRouter as default (most models go through it)
        return _OPENROUTER_BASE

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a chat completion request."""
        model = model or self.default_model

        # kimi-k2.5 only supports temperature=1.0
        if "kimi-k2.5" in model.lower():
            temperature = 1.0

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        try:
            resp = await self._client.post("/chat/completions", json=body)
            resp.raise_for_status()
            return self._parse_response(resp.json())
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:500] if e.response else str(e)
            logger.error(f"LLM API error {e.response.status_code}: {detail}")
            return LLMResponse(content=f"Error calling LLM: {detail}", finish_reason="error")
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return LLMResponse(content=f"Error calling LLM: {e}", finish_reason="error")

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """Parse an OpenAI-compatible JSON response."""
        choice = data["choices"][0]
        message = choice["message"]

        tool_calls: list[ToolCallRequest] = []
        for tc in message.get("tool_calls") or []:
            args = tc["function"]["arguments"]
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            tool_calls.append(
                ToolCallRequest(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=args,
                )
            )

        usage = {}
        if "usage" in data and data["usage"]:
            u = data["usage"]
            usage = {
                "prompt_tokens": u.get("prompt_tokens", 0),
                "completion_tokens": u.get("completion_tokens", 0),
                "total_tokens": u.get("total_tokens", 0),
            }

        return LLMResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason") or "stop",
            usage=usage,
        )

    def get_default_model(self) -> str:
        return self.default_model
