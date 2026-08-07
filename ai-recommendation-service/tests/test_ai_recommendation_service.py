import json
from pathlib import Path

import pytest

from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.ai_recommendation_service import AIRecommendationService
from app.services.candidate_action_builder import build_candidate_actions, compute_max_possible_gain
from app.services.response_validator import validate_llm_selection_response
from app.services.score_calculator import round_gain


@pytest.fixture
def framework() -> NDIFramework:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "ndi_framework.json"
    return NDIFramework.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _sample_scores() -> dict[str, int]:
    return {
        "DQ.MQ.1": 1, "DQ.MQ.2": 1, "DQ.MQ.3": 1, "DQ.MQ.4": 1,
        "DG.MQ.1": 2, "DG.MQ.2": 2, "DG.MQ.3": 2, "DG.MQ.4": 2,
        "RMD.MQ.1": 1, "RMD.MQ.2": 1, "RMD.MQ.3": 1, "RMD.MQ.4": 1,
        "MCM.MQ.1": 4, "MCM.MQ.2": 4, "MCM.MQ.3": 4, "MCM.MQ.4": 4,
        "PDP.MQ.1": 3, "PDP.MQ.2": 3, "PDP.MQ.3": 3, "PDP.MQ.4": 4,
        "DSI.MQ.1": 2, "DSI.MQ.2": 2, "DSI.MQ.3": 2, "DSI.MQ.4": 2,
        "OD.MQ.1": 4, "OD.MQ.2": 4, "OD.MQ.3": 4, "OD.MQ.4": 4,
        "DAM.MQ.1": 2, "DAM.MQ.2": 2, "DAM.MQ.3": 2, "DAM.MQ.4": 2,
        "DVR.MQ.1": 2, "DVR.MQ.2": 2, "DVR.MQ.3": 2, "DVR.MQ.4": 2,
    }


def test_generate_best_path_uses_backend_optimizer_without_ollama(framework, monkeypatch):
    monkeypatch.setattr("app.services.ai_recommendation_service.settings.USE_OLLAMA", False)

    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores=_sample_scores(),
    )

    service = AIRecommendationService()
    result = service.generate_best_path(framework, request)

    assert result.success is True
    assert result.status.targetReached is True
    assert result.scoreSummary.scoreGlobalFinalEstimated >= request.targetScore
    assert result.optimizationValidation is not None
    assert result.optimizationValidation.algorithm == "dynamic_programming"
    assert result.optimizationValidation.optimalityVerified is True
    assert result.optimizationSummary.selectedDomainsCount > 0


def test_generate_best_path_ignores_unsupported_llm_recommendation(framework, monkeypatch):
    monkeypatch.setattr("app.services.ai_recommendation_service.settings.USE_OLLAMA", True)

    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores=_sample_scores(),
    )

    service = AIRecommendationService()
    monkeypatch.setattr(
        service.ollama_service,
        "_call_ollama",
        lambda messages: json.dumps(
            {
                "success": True,
                "questionRecommendations": [
                    {
                        "domainId": "DQ",
                        "questionId": "DQ.MQ.1",
                        "recommendation": "Define the governance plan and implement Regulation X.",
                    }
                ],
                "warnings": [],
            }
        ),
    )

    result = service.generate_best_path(framework, request)
    assert result.detailedActions
    all_recommendations = [
        question.recommendation
        for domain in result.detailedActions
        for question in domain.questionsToImprove
    ]
    assert all_recommendations
    assert all("Regulation X" not in recommendation for recommendation in all_recommendations)
    assert all(
        question.groundedRecommendation == question.recommendation
        for domain in result.detailedActions
        for question in domain.questionsToImprove
    )
    assert any("LLM recommendation rejected" in warning for warning in result.warnings)


def test_generate_best_path_falls_back_to_grounded_recommendation_on_llm_failure(framework, monkeypatch):
    monkeypatch.setattr("app.services.ai_recommendation_service.settings.USE_OLLAMA", True)

    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores=_sample_scores(),
    )

    service = AIRecommendationService()

    def _raise_timeout(_messages):
        raise RuntimeError("timeout")

    monkeypatch.setattr(service.ollama_service, "_call_ollama", _raise_timeout)

    result = service.generate_best_path(framework, request)

    assert result.success is True
    assert any("LLM explanation enrichment failed" in warning for warning in result.warnings)
    question = result.detailedActions[0].questionsToImprove[0]
    assert question.recommendationSource == "knowledge_base"
    assert question.groundedRecommendation == question.recommendation


def test_validate_rejects_insufficient_cumulative_gain(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4, "FOI.MQ.1": 2},
    )
    _, actions_by_id = build_candidate_actions(framework, request.currentScores)

    payload = {
        "success": True,
        "selectedActionIds": ["DC_2_TO_3", "FOI_2_TO_3"],
        "selectionReason": "Too few actions.",
        "warnings": [],
    }

    is_valid, errors, _ = validate_llm_selection_response(
        payload,
        request.targetScore,
        actions_by_id=actions_by_id,
        score_global_initial=request.scoreGlobalActual,
        max_possible_gain=compute_max_possible_gain(list(actions_by_id.values())),
        target_reachable=True,
    )

    assert is_valid is False
    assert any("cumulativeGain is lower than targetGap" in error for error in errors)


def test_validate_rejects_domain_ids(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4, "FOI.MQ.1": 2, "BIA.MQ.1": 4},
    )
    _, actions_by_id = build_candidate_actions(framework, request.currentScores)
    domain_ids = sorted({str(action["domainId"]) for action in actions_by_id.values()})[:4]

    payload = {
        "success": True,
        "selectedActionIds": domain_ids,
        "selectionReason": "Wrong ids.",
        "warnings": [],
    }

    is_valid, errors, _ = validate_llm_selection_response(
        payload,
        request.targetScore,
        actions_by_id=actions_by_id,
        score_global_initial=request.scoreGlobalActual,
    )

    assert is_valid is False
    assert any("is a domainId, not a valid actionId" in error for error in errors)
