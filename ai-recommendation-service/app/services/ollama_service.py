import json
import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OLLAMA_NUM_PREDICT = 1024
THINKING_ONLY_ERROR_MESSAGE = (
    "Ollama returned only thinking and no content. Disable thinking mode with think=false."
)


class OllamaServiceError(Exception):
    """Raised when the Ollama API call fails."""


def _extract_prompt_from_messages(messages: list[dict[str, str]], role: str) -> str:
    for message in messages:
        if message.get("role") == role:
            return message.get("content", "")
    return ""


def save_ollama_debug_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    payload: dict[str, Any],
    output_path: Path | None = None,
) -> Path:
    target_path = output_path or settings.DEBUG_PAYLOAD_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    debug_document = {
        "model": model,
        "system_prompt_path": str(settings.SYSTEM_PROMPT_PATH.resolve()),
        "system_prompt": _extract_prompt_from_messages(messages, "system"),
        "user_prompt": _extract_prompt_from_messages(messages, "user"),
        "payload": payload,
    }

    target_path.write_text(
        json.dumps(debug_document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Ollama debug payload saved to %s", target_path)
    return target_path


class OllamaService:
    def __init__(
        self,
        api_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.api_url = api_url if api_url is not None else settings.ollama_chat_url
        self.model = model if model is not None else settings.effective_ollama_model
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.effective_ollama_timeout
        )

    def chat_json(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._call_ollama(messages)

    def _call_ollama(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": 0.0,
                "num_predict": OLLAMA_NUM_PREDICT,
            },
        }

        save_ollama_debug_payload(
            model=self.model,
            messages=messages,
            payload=payload,
        )

        print(f"Calling Ollama model={self.model}, timeout={self.timeout_seconds}")
        logger.info(
            "Calling Ollama | url=%s | model=%s | timeout=%ss | prompt_chars=%s",
            self.api_url,
            self.model,
            self.timeout_seconds,
            sum(len(message["content"]) for message in messages),
        )

        timeout = httpx.Timeout(
            connect=30.0,
            read=float(self.timeout_seconds),
            write=30.0,
            pool=30.0,
        )

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(self.api_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise OllamaServiceError(
                f"Ollama API HTTP {exc.response.status_code} at {self.api_url}: {body}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaServiceError(
                f"Ollama connection error at {self.api_url}: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaServiceError("Ollama returned a non-JSON HTTP response") from exc

        response_model = data.get("model")
        if isinstance(response_model, str) and response_model.strip():
            logger.info(
                "Ollama response model=%s | requested_model=%s | match=%s",
                response_model,
                self.model,
                response_model == self.model or response_model.startswith(f"{self.model}"),
            )
        else:
            logger.info(
                "Ollama response status=%s | requested_model=%s",
                getattr(response, "status_code", "unknown"),
                self.model,
            )

        message = data.get("message", {})
        content = message.get("content")
        thinking = message.get("thinking")
        if not isinstance(content, str) or not content.strip():
            if isinstance(thinking, str) and thinking.strip():
                raise OllamaServiceError(THINKING_ONLY_ERROR_MESSAGE)
            raise OllamaServiceError("Ollama returned an empty response")

        raw = content.strip()
        print("RAW LLM RESPONSE:", raw[:2000])
        logger.info("Ollama raw response preview: %s", raw[:300])
        return raw
