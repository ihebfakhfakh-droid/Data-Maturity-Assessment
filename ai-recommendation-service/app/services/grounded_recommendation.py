"""Build and validate knowledge-base-grounded recommendations."""

from __future__ import annotations

import re
from typing import Any

RECOMMENDATION_SOURCE_KNOWLEDGE_BASE = "knowledge_base"
LLM_RECOMMENDATION_REJECTED_WARNING = "LLM recommendation rejected: unsupported content"


def build_grounded_recommendation(transitions: list[dict[str, Any]]) -> str:
    """Concatenate exact transition explanations from the knowledge base."""
    if not isinstance(transitions, list):
        return ""

    explanations: list[str] = []
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        explanation = str(transition.get("explanation", "")).strip()
        if explanation:
            explanations.append(explanation.rstrip("."))

    if not explanations:
        return ""
    if len(explanations) == 1:
        return f"{explanations[0]}."
    return ". ".join(explanations) + "."


def _normalize_text(value: str) -> str:
    lowered = value.lower().strip()
    return re.sub(r"\s+", " ", lowered)


def _tokenize(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", _normalize_text(value))
        if len(token) > 2
    }


def is_llm_recommendation_supported(grounded_recommendation: str, llm_recommendation: str) -> bool:
    """Return True only if the LLM text does not introduce content outside the grounded text."""
    grounded = str(grounded_recommendation).strip()
    llm_text = str(llm_recommendation).strip()
    if not llm_text:
        return True
    if not grounded:
        return False
    if _normalize_text(llm_text) == _normalize_text(grounded):
        return True

    grounded_tokens = _tokenize(grounded)
    llm_tokens = _tokenize(llm_text)
    unsupported_tokens = llm_tokens - grounded_tokens
    return not unsupported_tokens


def enrich_question_with_grounded_recommendation(question: dict[str, Any]) -> dict[str, Any]:
    """Attach groundedRecommendation and force recommendation from the knowledge base."""
    enriched = dict(question)
    transitions = enriched.get("transitions", [])
    if not isinstance(transitions, list):
        transitions = []

    question_id = str(enriched.get("questionId") or enriched.get("questionCode", ""))
    grounded = build_grounded_recommendation(transitions)

    enriched["questionId"] = question_id
    enriched["groundedRecommendation"] = grounded
    enriched["recommendationSource"] = RECOMMENDATION_SOURCE_KNOWLEDGE_BASE
    enriched["recommendation"] = grounded
    return enriched


def apply_grounded_recommendations(validated_path: dict[str, Any]) -> dict[str, Any]:
    """Compute grounded recommendations for every validated question before any LLM call."""
    enriched = dict(validated_path)
    best_path: list[dict[str, Any]] = []

    for domain_item in validated_path.get("bestPath", []):
        if not isinstance(domain_item, dict):
            continue
        domain_copy = dict(domain_item)
        questions: list[dict[str, Any]] = []
        for question in domain_item.get("questionsToImprove", []):
            if not isinstance(question, dict):
                continue
            questions.append(enrich_question_with_grounded_recommendation(question))
        domain_copy["questionsToImprove"] = questions
        best_path.append(domain_copy)

    enriched["bestPath"] = best_path
    return enriched


def _collect_validated_questions(validated_path: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for domain_item in validated_path.get("bestPath", []):
        if not isinstance(domain_item, dict):
            continue
        domain_id = str(domain_item.get("domainId", ""))
        for question in domain_item.get("questionsToImprove", []):
            if not isinstance(question, dict):
                continue
            question_id = str(question.get("questionId") or question.get("questionCode", ""))
            indexed[(domain_id, question_id)] = question
    return indexed


def validate_llm_explanation_response(
    validated_path: dict[str, Any],
    explanation_response: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate that the LLM did not alter validated path data or add unsupported content."""
    errors: list[str] = []
    validated_questions = _collect_validated_questions(validated_path)
    llm_items = explanation_response.get("questionRecommendations", [])
    if not isinstance(llm_items, list):
        return False, ["LLM response questionRecommendations must be a list."]

    seen_keys: set[tuple[str, str]] = set()
    for item in llm_items:
        if not isinstance(item, dict):
            errors.append("LLM response contains a non-object question recommendation.")
            continue

        domain_id = str(item.get("domainId", "")).strip()
        question_id = str(item.get("questionId") or item.get("questionCode", "")).strip()
        key = (domain_id, question_id)

        if not domain_id or not question_id:
            errors.append("LLM response contains a recommendation without domainId or questionId.")
            continue

        if key not in validated_questions:
            errors.append(
                f"LLM response references unsupported question '{question_id}' in domain '{domain_id}'."
            )
            continue

        if key in seen_keys:
            errors.append(f"Duplicate LLM recommendation for question '{question_id}'.")
            continue
        seen_keys.add(key)

        validated_question = validated_questions[key]
        for numeric_field in ("currentScore", "targetScore", "totalQuestionEffort"):
            if numeric_field in item and item[numeric_field] != validated_question.get(numeric_field):
                errors.append(
                    f"LLM response modified {numeric_field} for question '{question_id}'."
                )

        if "transitions" in item:
            errors.append(f"LLM response must not provide transitions for question '{question_id}'.")

        llm_recommendation = str(item.get("recommendation", "")).strip()
        grounded = str(validated_question.get("groundedRecommendation", "")).strip()
        if llm_recommendation and not is_llm_recommendation_supported(grounded, llm_recommendation):
            errors.append(
                f"LLM recommendation for question '{question_id}' introduces unsupported content."
            )

    return len(errors) == 0, errors


def process_llm_explanation_response(
    validated_path: dict[str, Any],
    explanation_response: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate the LLM response but always keep grounded recommendations as the official output.
    """
    grounded_path = apply_grounded_recommendations(validated_path)
    is_valid, validation_errors = validate_llm_explanation_response(
        grounded_path,
        explanation_response,
    )

    warnings = list(grounded_path.get("warnings", []))
    warnings.extend(explanation_response.get("warnings", []) if isinstance(explanation_response.get("warnings"), list) else [])

    if not is_valid:
        warnings.append(LLM_RECOMMENDATION_REJECTED_WARNING)
        warnings.extend(validation_errors)

    result = dict(grounded_path)
    result["warnings"] = warnings
    return result
