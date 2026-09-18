"""Build prompts for optional LLM report enrichment (grounded recommendations are authoritative)."""

from __future__ import annotations

import json
from typing import Any


EXPLANATION_OUTPUT_SCHEMA = {
    "success": True,
    "questionRecommendations": [
        {
            "domainId": "domain-id",
            "questionId": "question-id",
            "recommendation": "Must remain identical to groundedRecommendation when provided.",
        }
    ],
    "warnings": [],
}


def build_explanation_user_prompt(validated_path: dict[str, Any]) -> str:
    """Send validated grounded recommendations to the LLM for optional narrative support only."""
    grounded_questions: list[dict[str, Any]] = []
    for domain_item in validated_path.get("bestPath", []):
        if not isinstance(domain_item, dict):
            continue
        domain_id = str(domain_item.get("domainId", ""))
        for question in domain_item.get("questionsToImprove", []):
            if not isinstance(question, dict):
                continue
            grounded_questions.append(
                {
                    "domainId": domain_id,
                    "questionId": question.get("questionId") or question.get("questionCode"),
                    "currentScore": question.get("currentScore"),
                    "targetScore": question.get("targetScore"),
                    "validatedTransitions": question.get("transitions", []),
                    "groundedRecommendation": question.get("groundedRecommendation", ""),
                }
            )

    payload = {
        "instruction": (
            "The validated Best Path and groundedRecommendation values are authoritative. "
            "Do not add new actions, regulations, technologies, deadlines, roles or examples. "
            "If you return questionRecommendations, each recommendation must remain strictly "
            "within the groundedRecommendation content."
        ),
        "validatedBestPath": {
            "scoreGlobalInitial": validated_path.get("scoreGlobalInitial"),
            "scoreGlobalTarget": validated_path.get("scoreGlobalTarget"),
            "scoreGlobalFinalEstimated": validated_path.get("scoreGlobalFinalEstimated"),
            "gainTotal": validated_path.get("gainTotal"),
            "effortTotal": validated_path.get("effortTotal"),
            "targetReached": validated_path.get("targetReached"),
            "groundedQuestions": grounded_questions,
        },
        "requiredOutputSchema": EXPLANATION_OUTPUT_SCHEMA,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
