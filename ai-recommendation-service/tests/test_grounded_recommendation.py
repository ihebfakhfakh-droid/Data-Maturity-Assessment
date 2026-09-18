"""Tests for knowledge-base-grounded recommendations."""

from __future__ import annotations

import json

import pytest

from app.services.explanation_merger import merge_llm_explanations, normalize_explanation_response
from app.services.grounded_recommendation import (
    LLM_RECOMMENDATION_REJECTED_WARNING,
    apply_grounded_recommendations,
    build_grounded_recommendation,
    enrich_question_with_grounded_recommendation,
    is_llm_recommendation_supported,
    process_llm_explanation_response,
    validate_llm_explanation_response,
)


def _validated_path_with_question(question: dict) -> dict:
    return {
        "success": True,
        "bestPath": [
            {
                "domainId": "DOMAIN_A",
                "domainName": "Domain A",
                "questionsToImprove": [question],
            }
        ],
        "warnings": [],
    }


def test_build_grounded_recommendation_concatenates_only_validated_transitions():
    transitions = [
        {
            "from": 1,
            "to": 2,
            "transitionKey": "1_to_2",
            "effort": 3,
            "explanation": "Define the governance plan.",
        },
        {
            "from": 2,
            "to": 3,
            "transitionKey": "2_to_3",
            "effort": 3,
            "explanation": "Implement the governance controls.",
        },
    ]
    assert build_grounded_recommendation(transitions) == (
        "Define the governance plan. Implement the governance controls."
    )


def test_grounded_recommendation_uses_only_required_transition_levels():
    question = enrich_question_with_grounded_recommendation(
        {
            "questionCode": "Q1",
            "questionText": "Question 1",
            "currentScore": 1,
            "targetScore": 2,
            "totalQuestionEffort": 3,
            "transitions": [
                {
                    "from": 1,
                    "to": 2,
                    "transitionKey": "1_to_2",
                    "effort": 3,
                    "explanation": "Action for level 1 to 2.",
                }
            ],
        }
    )
    assert [item["transitionKey"] for item in question["transitions"]] == ["1_to_2"]
    assert question["groundedRecommendation"] == "Action for level 1 to 2."
    assert question["recommendation"] == question["groundedRecommendation"]
    assert question["recommendationSource"] == "knowledge_base"


def test_llm_recommendation_with_extra_content_is_rejected():
    grounded = "Define the governance plan."
    llm_text = "Define the governance plan and implement Regulation X."
    assert is_llm_recommendation_supported(grounded, llm_text) is False


def test_process_llm_response_keeps_grounded_recommendation_when_llm_adds_content():
    validated = apply_grounded_recommendations(
        _validated_path_with_question(
            {
                "questionCode": "Q1",
                "questionText": "Question 1",
                "currentScore": 1,
                "targetScore": 2,
                "totalQuestionEffort": 3,
                "transitions": [
                    {
                        "from": 1,
                        "to": 2,
                        "transitionKey": "1_to_2",
                        "effort": 3,
                        "explanation": "Define the governance plan.",
                    }
                ],
            }
        )
    )

    result = process_llm_explanation_response(
        validated,
        {
            "success": True,
            "questionRecommendations": [
                {
                    "domainId": "DOMAIN_A",
                    "questionId": "Q1",
                    "recommendation": "Define the governance plan and implement Regulation X.",
                }
            ],
            "warnings": [],
        },
    )

    question = result["bestPath"][0]["questionsToImprove"][0]
    assert question["recommendation"] == "Define the governance plan."
    assert question["groundedRecommendation"] == "Define the governance plan."
    assert LLM_RECOMMENDATION_REJECTED_WARNING in result["warnings"]


def test_process_llm_response_rejects_modified_effort():
    validated = apply_grounded_recommendations(
        _validated_path_with_question(
            {
                "questionCode": "Q1",
                "questionText": "Question 1",
                "currentScore": 1,
                "targetScore": 2,
                "totalQuestionEffort": 3,
                "transitions": [
                    {
                        "from": 1,
                        "to": 2,
                        "transitionKey": "1_to_2",
                        "effort": 3,
                        "explanation": "Define the governance plan.",
                    }
                ],
            }
        )
    )

    is_valid, errors = validate_llm_explanation_response(
        validated,
        {
            "questionRecommendations": [
                {
                    "domainId": "DOMAIN_A",
                    "questionId": "Q1",
                    "totalQuestionEffort": 99,
                    "recommendation": "Define the governance plan.",
                }
            ]
        },
    )
    assert is_valid is False
    assert any("totalQuestionEffort" in error for error in errors)


def test_process_llm_response_rejects_extra_question():
    validated = apply_grounded_recommendations(
        _validated_path_with_question(
            {
                "questionCode": "Q1",
                "questionText": "Question 1",
                "currentScore": 1,
                "targetScore": 2,
                "totalQuestionEffort": 3,
                "transitions": [
                    {
                        "from": 1,
                        "to": 2,
                        "transitionKey": "1_to_2",
                        "effort": 3,
                        "explanation": "Define the governance plan.",
                    }
                ],
            }
        )
    )

    is_valid, errors = validate_llm_explanation_response(
        validated,
        {
            "questionRecommendations": [
                {
                    "domainId": "DOMAIN_A",
                    "questionId": "EXTRA_Q",
                    "recommendation": "Unsupported question.",
                }
            ]
        },
    )
    assert is_valid is False
    assert any("unsupported question" in error.lower() for error in errors)


def test_pdf_uses_grounded_recommendation():
    from app.services.best_path_pdf_generator import generate_best_path_pdf
    from app.services.grounded_recommendation import apply_grounded_recommendations

    report = apply_grounded_recommendations(
        {
            "success": True,
            "bestPath": [
                {
                    "domainId": "D1",
                    "domainName": "Domain 1",
                    "questionsToImprove": [
                        {
                            "questionCode": "Q1",
                            "questionText": "Question 1",
                            "currentScore": 1,
                            "targetScore": 2,
                            "totalQuestionEffort": 3,
                            "transitions": [
                                {
                                    "from": 1,
                                    "to": 2,
                                    "transitionKey": "1_to_2",
                                    "effort": 3,
                                    "explanation": "Define the governance plan.",
                                }
                            ],
                        }
                    ],
                }
            ],
            "warnings": [],
        }
    )
    question = report["bestPath"][0]["questionsToImprove"][0]
    assert question["recommendation"] == question["groundedRecommendation"]

    pdf_bytes = generate_best_path_pdf(
        {
            "success": True,
            "status": {"targetReached": True, "message": "OK"},
            "scoreSummary": {
                "scoreGlobalInitial": 1.0,
                "scoreGlobalTarget": 2.0,
                "targetGap": 1.0,
                "gainTotal": 1.0,
                "scoreGlobalFinalEstimated": 2.0,
                "overGain": 0.0,
                "effortTotal": 3,
            },
            "optimizationSummary": {
                "strategy": "dynamic_programming",
                "selectedDomainsCount": 1,
                "selectedQuestionsCount": 1,
                "whyThisPath": "Test",
                "effortExplanation": "Test",
            },
            "bestPathTable": [],
            "detailedActions": report["bestPath"],
            "mathematicalValidation": {
                "formula": "test",
                "calculation": "test",
                "targetReached": True,
            },
            "warnings": [],
        }
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_invalid_llm_json_fallback_keeps_grounded_recommendation():
    validated = apply_grounded_recommendations(
        _validated_path_with_question(
            {
                "questionCode": "Q1",
                "questionText": "Question 1",
                "currentScore": 1,
                "targetScore": 2,
                "totalQuestionEffort": 3,
                "transitions": [
                    {
                        "from": 1,
                        "to": 2,
                        "transitionKey": "1_to_2",
                        "effort": 3,
                        "explanation": "Define the governance plan.",
                    }
                ],
            }
        )
    )

    result = merge_llm_explanations(
        validated,
        normalize_explanation_response(json.loads('{"success": false, "questionRecommendations": []}')),
    )
    question = result["bestPath"][0]["questionsToImprove"][0]
    assert question["recommendation"] == "Define the governance plan."
    assert question["recommendationSource"] == "knowledge_base"
