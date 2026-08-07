import json
import pytest

from app.services.llm_response_parser import (
    LLMResponseParseError,
    extract_selected_action_ids_from_raw,
    normalize_llm_selection_response,
    parse_llm_json,
)


def test_parse_llm_json_plain_object():
    result = parse_llm_json('{"status":"ok","value":1}')
    assert result == {"status": "ok", "value": 1}


def test_parse_llm_json_markdown_fence():
    raw = """```json
{"status":"ok"}
```"""
    assert parse_llm_json(raw) == {"status": "ok"}


def test_parse_llm_json_with_prefix_text():
    raw = 'Here is the result:\n```json\n{"status":"ok"}\n```\nThanks.'
    assert parse_llm_json(raw) == {"status": "ok"}


def test_parse_llm_json_normalizes_single_candidate_action_object():
    raw = json.dumps(
        {
            "actionId": "DO_4_TO_5",
            "domainId": "DO",
            "domainName": "Data Storage",
        }
    )
    result = parse_llm_json(raw)
    assert result["success"] is True
    assert result["selectedActionIds"] == ["DO_4_TO_5"]
    assert "Parser extracted actionId from invalid LLM response." in result["selectionReason"]
    assert result["warnings"] == ["LLM returned a single action object instead of selectedActionIds."]


def test_parse_llm_json_recovers_truncated_selected_action_ids():
    raw = (
        '{"success": true, "selectedActionIds": ["DQ_1_TO_2", "DG_2_TO_3", "RMD_1_TO_2"], '
        '"selectionReason": "Selected high-impact'
    )
    result = parse_llm_json(raw)
    assert result["selectedActionIds"] == ["DQ_1_TO_2", "DG_2_TO_3", "RMD_1_TO_2"]
    assert any("truncated" in warning.lower() for warning in result["warnings"])


def test_extract_selected_action_ids_from_raw_handles_truncated_json():
    raw = (
        '{"success": true, "selectedActionIds": ["DQ_1_TO_2", "DG_2_TO_3", "RMD_1_TO_2"], '
        '"selectionReason": "Selected high-impact'
    )
    assert extract_selected_action_ids_from_raw(raw) == [
        "DQ_1_TO_2",
        "DG_2_TO_3",
        "RMD_1_TO_2",
    ]


def test_normalize_llm_selection_response_handles_none():
    result = normalize_llm_selection_response(None)
    assert result["success"] is False
    assert result["selectedActionIds"] == []
    assert result["warnings"]


def test_normalize_llm_selection_response_coerces_null_selected_action_ids():
    result = normalize_llm_selection_response(
        {"success": True, "selectedActionIds": None, "selectionReason": "", "warnings": None}
    )
    assert result["selectedActionIds"] == []
    assert result["warnings"] == []


def test_parse_llm_json_raises_with_excerpt():
    with pytest.raises(LLMResponseParseError) as exc_info:
        parse_llm_json("not json at all")
    assert "Raw excerpt" in str(exc_info.value)
