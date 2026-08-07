import json
from pathlib import Path

import pytest

from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.best_path_optimizer import BestPathOptimizer
from app.services.report_prompt_builder import build_report_context


@pytest.fixture
def framework() -> NDIFramework:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "ndi_framework.json"
    return NDIFramework.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_report_context_uses_dynamic_values_from_optimizer(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=2.6,
        currentScores={
            "DG.MQ.1": 3,
            "DG.MQ.2": 4,
            "DG.MQ.3": 2,
            "DG.MQ.4": 3,
            "DQ.MQ.1": 2,
            "DQ.MQ.2": 2,
            "DQ.MQ.3": 3,
            "DQ.MQ.4": 1,
            "RMD.MQ.1": 1,
            "RMD.MQ.2": 2,
            "RMD.MQ.3": 2,
        },
    )

    result = BestPathOptimizer().compute_best_path(framework, request)
    context = json.loads(build_report_context(result))

    assert context["task"].startswith("Generate a professional consulting report")
    assert context["scoreGlobalInitial"] == result["scoreGlobalInitial"]
    assert context["scoreGlobalTarget"] == result["scoreGlobalTarget"]
    assert context["scoreGlobalFinalEstimated"] == result["scoreGlobalFinalEstimated"]
    assert context["gainTotal"] == result["gainTotal"]
    assert context["effortTotal"] == result["effortTotal"]
    assert context["bestPath"] == result["bestPath"]
    assert context["scoreGlobalInitial"] == pytest.approx(request.scoreGlobalActual, abs=0.01)
    assert context["scoreGlobalTarget"] == pytest.approx(request.targetScore, abs=0.01)


def test_optimizer_reaches_target_with_real_framework(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=2.6,
        currentScores={
            "DG.MQ.1": 3,
            "DG.MQ.2": 4,
            "DG.MQ.3": 2,
            "DG.MQ.4": 3,
            "DQ.MQ.1": 2,
            "DQ.MQ.2": 2,
            "DQ.MQ.3": 3,
            "DQ.MQ.4": 1,
            "RMD.MQ.1": 1,
            "RMD.MQ.2": 2,
            "RMD.MQ.3": 2,
        },
    )

    result = BestPathOptimizer().compute_best_path(framework, request)

    assert result["targetReached"] is True
    assert result["scoreGlobalFinalEstimated"] >= request.targetScore
    assert result["bestPath"]
    assert all("domainWeight" in item for item in result["bestPath"])
    assert all("explanation" in item["questionsToImprove"][0] for item in result["bestPath"])
