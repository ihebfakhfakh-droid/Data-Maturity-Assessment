"""Merge LLM-written explanations into a validated Best Path."""

from __future__ import annotations

from typing import Any

from app.services.grounded_recommendation import (
    apply_grounded_recommendations,
    process_llm_explanation_response,
)


def apply_framework_explanations(validated_path: dict[str, Any]) -> dict[str, Any]:
    return apply_grounded_recommendations(validated_path)


def normalize_explanation_response(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {"success": False, "questionRecommendations": [], "warnings": []}

    recommendations_raw = parsed.get("questionRecommendations")
    recommendations: list[dict[str, str]] = []
    if isinstance(recommendations_raw, list):
        for item in recommendations_raw:
            if not isinstance(item, dict):
                continue
            domain_id = str(item.get("domainId", "")).strip()
            question_id = str(item.get("questionId") or item.get("questionCode", "")).strip()
            recommendation = str(item.get("recommendation", "")).strip()
            if domain_id and question_id:
                recommendations.append(
                    {
                        "domainId": domain_id,
                        "questionId": question_id,
                        "questionCode": question_id,
                        "recommendation": recommendation,
                    }
                )

    warnings = parsed.get("warnings")
    return {
        "success": bool(parsed.get("success", True)),
        "questionRecommendations": recommendations,
        "warnings": [str(item) for item in warnings] if isinstance(warnings, list) else [],
    }


def merge_llm_explanations(
    validated_path: dict[str, Any],
    explanation_response: dict[str, Any],
) -> dict[str, Any]:
    """Validate LLM output but keep grounded recommendations as the only official text."""
    return process_llm_explanation_response(validated_path, explanation_response)
