import json
import time
from pathlib import Path

import pytest

from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.candidate_action_builder import (
    build_candidate_actions,
    complete_selection_to_target,
    compute_max_possible_gain,
    compute_selection_totals,
    EFFORT_SUBOPTIMAL_WARNING,
    build_final_summary,
    finalize_best_path_response,
    find_minimum_effort_selection_ids,
    find_minimum_overgain_selection_ids,
    find_optimal_best_path,
    get_suggested_high_impact_action_ids,
    rebuild_best_path_from_selection,
    validate_final_response_consistency,
)
from app.services.prompt_builder import build_user_prompt
from app.services.score_calculator import compute_total_framework_weight, round_gain


@pytest.fixture
def framework() -> NDIFramework:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "ndi_framework.json"
    return NDIFramework.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_build_candidate_actions_uses_total_weights_for_gain(framework):
    current_scores = {"PDP.MQ.1": 3, "PDP.MQ.2": 3, "PDP.MQ.3": 3, "PDP.MQ.4": 4}
    total_weights = compute_total_framework_weight(framework)
    actions, actions_by_id = build_candidate_actions(
        framework,
        current_scores,
        total_weights=total_weights,
    )

    pdp_action = actions_by_id.get("PDP_3_TO_4")
    if pdp_action is None:
        pdp_actions = [action for action in actions if action["domainId"] == "PDP"]
        assert pdp_actions
        pdp_action = next(
            action
            for action in pdp_actions
            if action["currentDomainScore"] == 3 and action["targetDomainScore"] == 4
        )
    assert pdp_action["globalScoreGain"] == pytest.approx(0.093, abs=0.001)
    assert pdp_action["questionsToImprove"][0]["transitions"][0]["transitionKey"]


def test_candidate_action_transitions_use_from_to_transition_key(framework):
    current_scores = {"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4}
    _, actions_by_id = build_candidate_actions(framework, current_scores)
    action = actions_by_id["DC_2_TO_3"]
    transition = action["questionsToImprove"][0]["transitions"][0]
    assert "from" in transition
    assert "to" in transition
    assert transition["transitionKey"] == "2_to_3"
    assert action["globalScoreGain"] == pytest.approx(0.068, abs=0.001)


def test_rebuild_best_path_from_selection(framework):
    current_scores = {"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4}
    _, actions_by_id = build_candidate_actions(framework, current_scores)
    rebuilt = rebuild_best_path_from_selection(
        ["DC_2_TO_3"],
        actions_by_id,
        score_global_initial=2.0,
        target_score=2.05,
        summary={"optimizationLogic": "x", "selectedDomainsReason": "y",
                 "effortInterpretation": "z", "finalValidation": "ok"},
    )
    assert rebuilt["targetReached"] is True
    assert rebuilt["gainTotal"] == pytest.approx(0.068, abs=0.001)
    assert rebuilt["bestPath"][0]["domainName"] == "Data Classification"


def test_save_candidate_actions_debug_writes_sorted_lists(framework, tmp_path):
    from app.services.candidate_action_builder import save_candidate_actions_debug

    current_scores = {"DQ.MQ.1": 2, "DQ.MQ.2": 2, "DQ.MQ.3": 3, "DQ.MQ.4": 1}
    actions, _ = build_candidate_actions(framework, current_scores)
    output = save_candidate_actions_debug(
        score_global_actual=2.48,
        target_score=3.48,
        candidate_actions=actions,
        output_path=tmp_path / "latest_candidate_actions.json",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["targetGap"] == pytest.approx(1.0, abs=0.01)
    assert payload["maxPossibleGain"] == pytest.approx(compute_max_possible_gain(actions), abs=0.01)
    assert payload["targetReachable"] == (payload["maxPossibleGain"] >= payload["targetGap"])
    assert payload["candidateActionsByEfficiencyRatio"]
    assert payload["candidateActionsByGlobalScoreGain"][0]["globalScoreGain"] >= payload[
        "candidateActionsByGlobalScoreGain"
    ][-1]["globalScoreGain"]


def test_save_allowed_action_ids_debug_writes_expected_payload(framework, tmp_path):
    from app.services.candidate_action_builder import save_allowed_action_ids_debug

    current_scores = {"DQ.MQ.1": 2, "DQ.MQ.2": 2, "DQ.MQ.3": 3, "DQ.MQ.4": 1}
    actions, _ = build_candidate_actions(framework, current_scores)
    output = save_allowed_action_ids_debug(
        score_global_actual=2.48,
        target_score=3.48,
        candidate_actions=actions,
        output_path=tmp_path / "latest_allowed_action_ids.json",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["allowedActionIds"] == [action["actionId"] for action in actions]
    assert payload["candidateActions"] == actions
    assert payload["scoreGlobalActual"] == pytest.approx(2.48)
    assert payload["targetScore"] == pytest.approx(3.48)
    assert payload["targetGap"] == pytest.approx(1.0, abs=0.01)


def _sample_high_gain_scores() -> dict[str, int]:
    return {
        "DQ.MQ.1": 1, "DQ.MQ.2": 1, "DQ.MQ.3": 1, "DQ.MQ.4": 1,
        "DG.MQ.1": 2, "DG.MQ.2": 2, "DG.MQ.3": 2, "DG.MQ.4": 2,
        "MCM.MQ.1": 4, "MCM.MQ.2": 4, "MCM.MQ.3": 4, "MCM.MQ.4": 4,
        "PDP.MQ.1": 3, "PDP.MQ.2": 3, "PDP.MQ.3": 3, "PDP.MQ.4": 3,
        "RMD.MQ.1": 1, "RMD.MQ.2": 1, "RMD.MQ.3": 1, "RMD.MQ.4": 1,
        "DSI.MQ.1": 2, "DSI.MQ.2": 2, "DSI.MQ.3": 2, "DSI.MQ.4": 2,
        "OD.MQ.1": 4, "OD.MQ.2": 4, "OD.MQ.3": 4, "OD.MQ.4": 4,
        "DAM.MQ.1": 2, "DAM.MQ.2": 2, "DAM.MQ.3": 2, "DAM.MQ.4": 2,
        "DVR.MQ.1": 2, "DVR.MQ.2": 2, "DVR.MQ.3": 2, "DVR.MQ.4": 2,
    }


def test_complete_selection_to_target_adds_remaining_actions(framework):
    current_scores = _sample_high_gain_scores()
    actions, actions_by_id = build_candidate_actions(framework, current_scores)
    target_gap = 1.0
    completed_ids = complete_selection_to_target(
        ["OD_4_TO_5", "DVR_2_TO_3", "DAM_2_TO_3"],
        actions_by_id,
        actions,
        target_gap=target_gap,
    )
    completed_gain, _ = compute_selection_totals(completed_ids, actions_by_id)
    assert completed_gain >= target_gap
    assert len(completed_ids) > 3


def test_build_candidate_actions_includes_intermediate_targets(framework):
    current_scores = {
        "DQ.MQ.1": 1,
        "DQ.MQ.2": 1,
        "DQ.MQ.3": 1,
        "DQ.MQ.4": 1,
        "DG.MQ.1": 2,
        "DG.MQ.2": 2,
        "DG.MQ.3": 2,
        "DG.MQ.4": 2,
        "RMD.MQ.1": 1,
    }
    _, actions_by_id = build_candidate_actions(framework, current_scores)
    expected_ids = [
        "DQ_1_TO_2",
        "DQ_1_TO_3",
        "DQ_1_TO_4",
        "DQ_1_TO_5",
        "DG_2_TO_3",
        "DG_2_TO_4",
        "DG_2_TO_5",
        "RMD_1_TO_2",
        "RMD_1_TO_3",
        "RMD_1_TO_4",
        "RMD_1_TO_5",
    ]
    for action_id in expected_ids:
        assert action_id in actions_by_id


def test_high_impact_actions_prioritize_efficiency(framework):
    current_scores = _sample_high_gain_scores()
    actions, actions_by_id = build_candidate_actions(framework, current_scores)
    suggested = get_suggested_high_impact_action_ids(actions)
    first_action = actions_by_id[suggested[0]]
    domain_best = max(actions, key=lambda item: float(item["efficiencyRatio"]))
    assert float(first_action["efficiencyRatio"]) == pytest.approx(
        float(domain_best["efficiencyRatio"]),
        abs=0.0001,
    )
    assert "DQ_1_TO_5" not in suggested[:3]


def test_find_minimum_effort_selection_prefers_lower_effort_path(framework):
    current_scores = _sample_high_gain_scores()
    actions, _ = build_candidate_actions(framework, current_scores)
    target_gap = 1.0

    minimum = find_minimum_effort_selection_ids(actions, target_gap=target_gap)
    assert minimum is not None
    minimum_ids, minimum_effort, minimum_gain = minimum
    assert minimum_gain >= target_gap

    overshoot_ids = ["DQ_1_TO_5", "RMD_1_TO_5", "DG_2_TO_5"]
    _, overshoot_effort = compute_selection_totals(overshoot_ids, {a["actionId"]: a for a in actions})
    assert minimum_effort < overshoot_effort
    assert "DQ_1_TO_5" not in minimum_ids or len(minimum_ids) > 1


def test_beam_optimizer_completes_within_time_limit(framework):
    current_scores = _sample_high_gain_scores()
    actions, _ = build_candidate_actions(framework, current_scores)
    target_gap = 1.0

    started_at = time.monotonic()
    optimal = find_optimal_best_path(actions, target_gap=target_gap)
    duration = time.monotonic() - started_at

    assert duration < 5.0
    assert optimal is not None
    assert optimal["gainTotal"] >= target_gap
    assert optimal.get("durationSeconds", duration) < 5.0


def test_find_optimal_best_path_prefers_minimum_effort(framework):
    current_scores = _sample_high_gain_scores()
    actions, _ = build_candidate_actions(framework, current_scores)
    target_gap = 1.0

    optimal = find_optimal_best_path(actions, target_gap=target_gap)
    assert optimal is not None
    assert optimal["gainTotal"] >= target_gap

    overshoot_ids = ["DQ_1_TO_5", "RMD_1_TO_5", "DG_2_TO_5"]
    actions_by_id = {action["actionId"]: action for action in actions}
    overshoot_gain, overshoot_effort = compute_selection_totals(overshoot_ids, actions_by_id)
    assert overshoot_gain >= target_gap
    assert optimal["effortTotal"] < overshoot_effort or (
        optimal["effortTotal"] == overshoot_effort
        and optimal["overGain"] <= round_gain(max(overshoot_gain - target_gap, 0.0))
    )


def test_find_minimum_overgain_selection_prefers_minimum_effort(framework):
    current_scores = _sample_high_gain_scores()
    actions, _ = build_candidate_actions(framework, current_scores)
    target_gap = 1.0

    minimum = find_minimum_overgain_selection_ids(actions, target_gap=target_gap)
    assert minimum is not None
    minimum_ids, minimum_effort, minimum_gain, minimum_over_gain = minimum
    assert minimum_gain >= target_gap

    optimal = find_optimal_best_path(actions, target_gap=target_gap)
    assert optimal is not None
    assert minimum_effort == int(optimal["effortTotal"])
    assert minimum_over_gain == pytest.approx(float(optimal["overGain"]), abs=0.01)

    overshoot_ids = ["DQ_1_TO_5", "RMD_1_TO_5", "DG_2_TO_5"]
    overshoot_gain, overshoot_effort = compute_selection_totals(
        overshoot_ids,
        {a["actionId"]: a for a in actions},
    )
    assert minimum_effort < overshoot_effort


def test_rebuild_best_path_includes_over_gain(framework):
    current_scores = _sample_high_gain_scores()
    actions, actions_by_id = build_candidate_actions(framework, current_scores)
    rebuilt = rebuild_best_path_from_selection(
        ["DQ_1_TO_5", "RMD_1_TO_5", "DG_2_TO_5"],
        actions_by_id,
        score_global_initial=2.48,
        target_score=3.48,
        candidate_actions=actions,
    )
    assert rebuilt["targetReached"] is True
    assert rebuilt["overGain"] == pytest.approx(
        rebuilt["scoreGlobalFinalEstimated"] - 3.48,
        abs=0.01,
    )


def test_rebuild_best_path_adds_effort_suboptimal_warning(framework):
    current_scores = _sample_high_gain_scores()
    actions, actions_by_id = build_candidate_actions(framework, current_scores)
    rebuilt = rebuild_best_path_from_selection(
        ["DQ_1_TO_5", "RMD_1_TO_5", "DG_2_TO_5"],
        actions_by_id,
        score_global_initial=2.48,
        target_score=3.48,
        candidate_actions=actions,
    )
    assert rebuilt["targetReached"] is True
    assert EFFORT_SUBOPTIMAL_WARNING in rebuilt["warnings"] or any(
        "exceeds it more than necessary" in warning for warning in rebuilt["warnings"]
    )


def test_high_impact_actions_include_expected_ids_for_sample_scores(framework):
    current_scores = _sample_high_gain_scores()
    actions, actions_by_id = build_candidate_actions(framework, current_scores)
    expected_ids = [
        "DQ_1_TO_3",
        "DG_2_TO_4",
        "MCM_4_TO_5",
        "PDP_3_TO_4",
        "RMD_1_TO_2",
        "DSI_2_TO_3",
        "OD_4_TO_5",
        "DAM_2_TO_3",
        "DVR_2_TO_3",
    ]
    for action_id in expected_ids:
        assert action_id in actions_by_id
    suggested = get_suggested_high_impact_action_ids(actions)
    assert suggested
    for action_id in suggested:
        assert action_id in actions_by_id


def test_build_final_summary_uses_equal_to_when_target_is_exactly_reached():
    summary = build_final_summary(
        score_global_initial=2.48,
        score_global_target=3.48,
        score_global_final_estimated=3.48,
        gain_total=1.0,
        effort_total=70,
        target_reached=True,
        best_path=[{"domainId": "DQ"}],
    )

    assert "which is equal to the target score 3.48." in summary["finalValidation"]


def test_finalize_best_path_response_rebuilds_summary_after_auto_completion(framework):
    current_scores = {"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4}
    _, actions_by_id = build_candidate_actions(framework, current_scores)
    rebuilt = rebuild_best_path_from_selection(
        ["DC_2_TO_3"],
        actions_by_id,
        score_global_initial=2.48,
        target_score=2.05,
        summary={
            "optimizationLogic": "Old LLM logic with cumulative gain = 0.142.",
            "selectedDomainsReason": "Old reason.",
            "effortInterpretation": "Old effort.",
            "finalValidation": "Target score not reached. Additional actions required.",
        },
        warnings=[
            "Target score not yet reached.",
            "Additional actions required.",
        ],
    )
    finalized = finalize_best_path_response(rebuilt, auto_completed=True)

    assert finalized["targetReached"] is True
    assert "0.142" not in finalized["summary"]["optimizationLogic"]
    assert "target reached:" in finalized["summary"]["finalValidation"].lower()
    assert str(finalized["gainTotal"]) in finalized["summary"]["selectedDomainsReason"]
    assert "combines domain DC" in finalized["summary"]["selectedDomainsReason"]
    assert any("backend optimizer" in warning.lower() for warning in finalized["warnings"])
    assert validate_final_response_consistency(finalized) == []


def test_build_user_prompt_contains_selection_options(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4},
    )
    actions, _ = build_candidate_actions(framework, request.currentScores)
    max_possible_gain = compute_max_possible_gain(actions)
    context = json.loads(
        build_user_prompt(
            framework=framework,
            request=request,
            score_global_initial=2.48,
            candidate_actions=actions,
            max_possible_gain=max_possible_gain,
            target_reachable=max_possible_gain >= 1.0,
            auto_complete_enabled=False,
        )
    )
    assert context["task"] == "Select actionIds only."
    assert context["allowedActionIds"]
    assert context["selectionOptions"]
    assert "candidateActions" not in context
    assert "domainsSummary" not in context
