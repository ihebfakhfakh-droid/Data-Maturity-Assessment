import logging

from fastapi import APIRouter

from app.core.config import settings
from app.services.llm_response_parser import LLMResponseParseError, parse_llm_json
from app.services.ollama_service import OllamaService, OllamaServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/config")
def debug_config() -> dict:
    return {
        "ollamaBaseUrl": settings.OLLAMA_BASE_URL,
        "ollamaModel": settings.OLLAMA_MODEL,
        "effectiveOllamaModel": settings.effective_ollama_model,
        "useOllama": settings.USE_OLLAMA,
        "ollamaTimeoutSeconds": settings.OLLAMA_TIMEOUT_SECONDS,
        "systemPromptExists": settings.SYSTEM_PROMPT_PATH.exists(),
        "frameworkExists": settings.FRAMEWORK_PATH.exists(),
        "ollamaChatUrl": settings.ollama_chat_url,
        "envFileLoadedFrom": str(settings.model_config["env_file"]),
    }


@router.get("/ollama")
def debug_ollama() -> dict:
    service = OllamaService()
    test_messages = [
        {
            "role": "system",
            "content": "You are a test assistant. Reply only with valid JSON.",
        },
        {
            "role": "user",
            "content": 'Réponds uniquement avec {"status":"ok"}',
        },
    ]

    try:
        raw_response = service._call_ollama(test_messages)
        parsed_response = None
        parse_error = None
        try:
            parsed_response = parse_llm_json(raw_response)
        except LLMResponseParseError as exc:
            parse_error = str(exc)

        return {
            "success": True,
            "model": service.model,
            "timeoutSeconds": service.timeout_seconds,
            "rawResponse": raw_response,
            "parsedResponse": parsed_response,
            "parseError": parse_error,
        }
    except OllamaServiceError as exc:
        logger.exception("Ollama debug call failed")
        return {
            "success": False,
            "model": service.model,
            "timeoutSeconds": service.timeout_seconds,
            "rawResponse": "",
            "error": str(exc),
        }
