import json
import re
from typing import Any


class LLMResponseParseError(ValueError):
    """Raised when the LLM response cannot be parsed as JSON."""

    def __init__(self, message: str, raw_response: str) -> None:
        self.raw_response = raw_response
        super().__init__(message)


_TRUNCATED_JSON_WARNING = "LLM response JSON was truncated; parser recovered selectedActionIds."


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _safe_extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _extract_json_object(text: str) -> str:
    extracted = _safe_extract_json_object(text)
    if extracted is None:
        snippet = text.strip()[:500]
        message = "No JSON object found in LLM response"
        if snippet:
            message = f"{message}. Raw excerpt: {snippet!r}"
        raise LLMResponseParseError(message, raw_response=text)
    return extracted


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item)]


def extract_selected_action_ids_from_raw(raw_response: str) -> list[str]:
    if not isinstance(raw_response, str) or not raw_response.strip():
        return []

    patterns = (
        r'"selectedActionIds"\s*:\s*\[(.*?)\]',
        r'"selectedActionIds"\s*:\s*\[(.*)',
    )
    for pattern in patterns:
        match = re.search(pattern, raw_response, re.DOTALL)
        if not match:
            continue
        action_ids = re.findall(r'"([A-Za-z0-9_]+)"', match.group(1))
        if action_ids:
            return action_ids
    return []


def _build_recovered_truncated_response(action_ids: list[str]) -> dict[str, Any]:
    return {
        "success": True,
        "selectedActionIds": action_ids,
        "selectionReason": "",
        "warnings": [_TRUNCATED_JSON_WARNING],
    }


def _try_repair_truncated_json(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    if start == -1:
        return None

    fragment = text[start:].strip()
    suffixes = (
        '"}',
        '"]}',
        '""]}',
        '""]}',
        '""]}',
        '", "warnings": []}',
        '", "selectionReason": "", "warnings": []}',
    )
    for suffix in suffixes:
        try:
            parsed = json.loads(fragment + suffix)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    action_ids = extract_selected_action_ids_from_raw(fragment)
    if action_ids:
        return _build_recovered_truncated_response(action_ids)
    return None


def _normalize_single_action_response(parsed: dict[str, Any]) -> dict[str, Any]:
    if "selectedActionIds" in parsed:
        normalized = dict(parsed)
        normalized["selectedActionIds"] = _coerce_string_list(parsed.get("selectedActionIds"))
        warnings = parsed.get("warnings")
        normalized["warnings"] = warnings if isinstance(warnings, list) else []
        return normalized

    action_id = parsed.get("actionId")
    if isinstance(action_id, str) and action_id:
        return {
            "success": True,
            "selectedActionIds": [action_id],
            "selectionReason": "Parser extracted actionId from invalid LLM response.",
            "warnings": ["LLM returned a single action object instead of selectedActionIds."],
        }
    return dict(parsed)


def normalize_llm_selection_response(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {
            "success": False,
            "selectedActionIds": [],
            "selectionReason": "",
            "warnings": ["LLM response could not be parsed."],
        }

    normalized = _normalize_single_action_response(parsed)
    if "selectedActionIds" in normalized or normalized.get("success") is not None:
        normalized["selectedActionIds"] = _coerce_string_list(normalized.get("selectedActionIds"))
        warnings = normalized.get("warnings")
        normalized["warnings"] = warnings if isinstance(warnings, list) else []
        if normalized.get("selectionReason") is None:
            normalized["selectionReason"] = ""
    return normalized


def parse_llm_json(raw_response: str) -> dict[str, Any]:
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise LLMResponseParseError("LLM response is empty", raw_response=raw_response or "")

    cleaned = _strip_markdown_fences(raw_response)
    candidates = [
        raw_response.strip(),
        cleaned,
    ]
    for source in (cleaned, raw_response.strip()):
        extracted = _safe_extract_json_object(source)
        if extracted and extracted not in candidates:
            candidates.append(extracted)

    seen: set[str] = set()
    last_error: json.JSONDecodeError | None = None

    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

        if not isinstance(parsed, dict):
            raise LLMResponseParseError(
                "LLM response JSON must be an object",
                raw_response=raw_response,
            )
        return _normalize_single_action_response(parsed)

    repaired = _try_repair_truncated_json(raw_response)
    if repaired is not None:
        normalized = _normalize_single_action_response(repaired)
        warnings = normalized.get("warnings")
        if not isinstance(warnings, list):
            warnings = []
        if _TRUNCATED_JSON_WARNING not in warnings:
            warnings.append(_TRUNCATED_JSON_WARNING)
        normalized["warnings"] = warnings
        return normalized

    snippet = raw_response.strip()[:500]
    message = f"Invalid JSON response from LLM: {last_error}"
    if snippet:
        message = f"{message}. Raw excerpt: {snippet!r}"
    raise LLMResponseParseError(message, raw_response=raw_response)
