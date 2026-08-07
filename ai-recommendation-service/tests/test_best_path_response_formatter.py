import json
from pathlib import Path

import pytest

from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.best_path_response_formatter import (
    AUTO_COMPLETE_DISABLED_WARNING,
    build_mathematical_validation_calculation,
    format_best_path_response,
    sort_best_path_for_display,
)
from app.services.candidate_action_builder import (
    build_candidate_actions,
    build_partial_best_path_from_selection,
    find_minimum_overgain_selection_ids,
    rebuild_best_path_from_selection,
)
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
        "DC.MQ.1": 3, "DC.MQ.2": 3, "DC.MQ.3": 3, "DC.MQ.4": 3,
        "FOI.MQ.1": 2, "FOI.MQ.2": 2, "FOI.MQ.3": 2, "FOI.MQ.4": 2,
        "BIA.MQ.1": 3, "BIA.MQ.2": 3, "BIA.MQ.3": 3, "BIA.MQ.4": 3,
        "DO.MQ.1": 3, "DO.MQ.2": 3, "DO.MQ.3": 3, "DO.MQ.4": 3,
        "DVR.MQ.1": 2, "DVR.MQ.2": 2, "DVR.MQ.3": 2, "DVR.MQ.4": 2,
    }


def test_sort_best_path_for_display_orders_by_global_score_gain():
    best_path = [
        {
            "priority": 1,
            "domainId": "DAM",
            "domainName": "Data Modeling & Architecture",
            "domainWeight": 5.09,
            "globalScoreGain": 0.153,
            "efficiencyRatio": 0.007,
            "totalEffort": 22,
        },
        {
            "priority": 2,
            "domainId": "DC",
            "domainName": "Data Classification",
            "domainWeight": 6.84,
            "globalScoreGain": 0.137,
            "efficiencyRatio": 0.006,
            "totalEffort": 20,
        },
        {
            "priority": 3,
            "domainId": "DG",
            "domainName": "Data Governance",
            "domainWeight": 11.75,
            "globalScoreGain": 0.352,
            "efficiencyRatio": 0.016,
            "totalEffort": 22,
        },
        {
            "priority": 4,
            "domainId": "DQ",
            "domainName": "Data Quality",
            "domainWeight": 11.93,
            "globalScoreGain": 0.358,
            "efficiencyRatio": 0.016,
            "totalEffort": 22,
        },
    ]

    sorted_path = sort_best_path_for_display(best_path)

    assert [item["domainId"] for item in sorted_path] == ["DQ", "DG", "DAM", "DC"]
    assert [item["priority"] for item in sorted_path] == [1, 2, 3, 4]


def test_format_success_response_uses_display_priority_order(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores=_sample_scores(),
    )
    from app.services.exact_path_optimizer import optimize_best_path

    rebuilt = optimize_best_path(framework, request.currentScores, request.targetScore)
    response = format_best_path_response(rebuilt)

    assert response.success is True
    assert response.status.targetReached is True
    assert response.status.message == "Target score reached successfully."
    assert response.scoreSummary.scoreGlobalInitial == pytest.approx(
        rebuilt["scoreGlobalInitial"], abs=0.01
    )
    assert response.scoreSummary.scoreGlobalTarget == pytest.approx(3.48)
    assert response.scoreSummary.targetGap == pytest.approx(
        round_gain(request.targetScore - rebuilt["scoreGlobalInitial"]), abs=0.01
    )
    assert response.scoreSummary.gainTotal >= 1.0
    assert response.optimizationSummary.selectedDomainsCount == len(response.bestPathTable)
    assert response.optimizationSummary.selectedQuestionsCount == sum(
        len(item.questionsToImprove) for item in response.detailedActions
    )
    assert response.bestPathTable
    assert response.detailedActions
    assert response.bestPathTable[0].efficiencyRatio >= response.bestPathTable[-1].efficiencyRatio
    assert response.bestPathTable[0].priority == 1
    assert "questionsToImprove" not in response.bestPathTable[0].model_dump()
    assert response.mathematicalValidation.formula == (
        "scoreGlobalFinalEstimated = scoreGlobalInitial + gainTotal"
    )
    assert "target" in response.mathematicalValidation.calculation


def test_format_failure_response_for_insufficient_selection(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DG.MQ.1": 2, "DG.MQ.2": 2, "DG.MQ.3": 2, "DG.MQ.4": 2},
    )
    _, actions_by_id = build_candidate_actions(framework, request.currentScores)
    selected_ids = ["DG_2_TO_5"]
    action = actions_by_id[selected_ids[0]]

    response = format_best_path_response(
        {
            "success": False,
            "scoreGlobalInitial": 2.48,
            "scoreGlobalTarget": 3.48,
            "scoreGlobalFinalEstimated": 2.48 + float(action["globalScoreGain"]),
            "gainTotal": float(action["globalScoreGain"]),
            "effortTotal": int(action["totalEffort"]),
            "overGain": 0.0,
            "targetReached": False,
            "bestPath": build_partial_best_path_from_selection(selected_ids, actions_by_id),
            "warnings": [],
            "failureMeta": {
                "insufficient_selection": True,
                "auto_complete_disabled": True,
            },
        }
    )

    assert response.success is False
    assert response.status.targetReached is False
    assert "cumulativeGain is lower than targetGap" in response.status.message
    assert response.scoreSummary.gainTotal == pytest.approx(float(action["globalScoreGain"]))
    assert response.bestPathTable == []
    assert response.detailedActions == []
    assert response.optimizationSummary.selectedDomainsCount == 1
    assert AUTO_COMPLETE_DISABLED_WARNING in response.warnings
    assert "< target" in response.mathematicalValidation.calculation


def test_build_mathematical_validation_calculation_equal_case():
    calculation = build_mathematical_validation_calculation(
        score_global_initial=2.48,
        gain_total=1.0,
        score_global_final=3.48,
        target_score=3.48,
        target_reached=True,
        over_gain=0.0,
    )
    assert calculation == "2.48 + 1.0 = 3.48, equal to target 3.48"
