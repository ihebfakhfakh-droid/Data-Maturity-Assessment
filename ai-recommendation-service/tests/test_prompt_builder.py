import json
from pathlib import Path

import pytest

from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.candidate_action_builder import (
    build_candidate_actions,
    compute_max_possible_gain,
)
from app.services.prompt_builder import (
    build_correction_prompt,
    build_selection_options,
    build_user_prompt,
    get_allowed_action_ids_from_selection_options,
)
from app.services.response_validator import validate_llm_selection_response


@pytest.fixture
def framework(framework_raw) -> NDIFramework:
    return NDIFramework.model_validate(framework_raw)


@pytest.fixture
def framework_raw() -> dict:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "ndi_framework.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_user_prompt_uses_selection_options_only(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DG.MQ.1": 3, "DG.MQ.2": 2, "DQ.MQ.1": 2},
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

    selection_options = build_selection_options(actions)
    allowed_action_ids = get_allowed_action_ids_from_selection_options(selection_options)

    assert context["task"] == "Select actionIds only."
    assert context["allowedActionIds"] == allowed_action_ids
    assert context["selectionOptions"] == selection_options
    assert "candidateActions" not in context
    assert "questionsToImprove" not in json.dumps(context)
    assert "transitions" not in json.dumps(context)
    assert context["selectionOptions"]
    assert context["effortMinimizationRule"]
    assert "Do not push domains to level 5 unless required to reach the target" in context["effortMinimizationRule"]
    assert context["antiOvershootRule"]
    assert context["selectionPriorities"]
    assert context["highEffortAvoidanceRule"]
    assert context["targetGapRule"]
    assert "sum(globalScoreGain of selected actions) >= targetGap" in context["targetGapRule"]
    assert context["invalidSelectionExample"]
    assert context["overGainRule"]
    assert "minimum possible effortTotal" in context["overGainRule"]
    assert context["selectionPriorities"][1].startswith("Priority 2: Minimize effortTotal")


def test_build_correction_prompt_handles_domain_ids(framework):
    actions, _ = build_candidate_actions(framework, {"DQ.MQ.4": 1})
    context = json.loads(
        build_correction_prompt(
            target_score=3.48,
            score_global_actual=2.48,
            target_gap=1.0,
            errors=["Invalid selectedActionIds: 'DQ' is a domainId, not a valid actionId."],
            previous_response='{"selectedActionIds": ["DQ"]}',
            candidate_actions=actions,
            selected_action_ids=["DQ"],
            auto_complete_enabled=False,
        )
    )

    assert context["allowedActionIds"]
    assert context["selectionOptions"]
    assert "candidateActions" not in context
    assert "You returned domainIds instead of actionIds" in context["correctionMessage"]
    assert '["DQ"]' in context["correctionMessage"]
    assert "Example valid actionIds" in context["correctionMessage"]


def test_build_user_prompt_puts_task_first(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DG.MQ.1": 3, "DG.MQ.2": 2, "DQ.MQ.1": 2},
    )
    actions, _ = build_candidate_actions(framework, request.currentScores)
    prompt = build_user_prompt(
        framework=framework,
        request=request,
        score_global_initial=2.48,
        candidate_actions=actions,
        max_possible_gain=compute_max_possible_gain(actions),
        target_reachable=True,
        auto_complete_enabled=False,
    )
    first_key = next(iter(json.loads(prompt)))
    assert first_key == "task"


def test_build_correction_prompt_handles_invented_action_ids(framework):
    actions, _ = build_candidate_actions(framework, {"BIA.MQ.1": 4, "DO.MQ.1": 4})
    invented_ids = ["BIA_1_TO_2", "DO_1_TO_2", "FOI_1_TO_2", "DVR_1_TO_2", "DCM_1_TO_2"]
    context = json.loads(
        build_correction_prompt(
            target_score=3.48,
            score_global_actual=2.48,
            target_gap=1.0,
            errors=[
                "Invalid selectedActionId: BIA_1_TO_2 does not exist in allowedActionIds. "
                "The LLM must copy exact actionIds from allowedActionIds."
            ],
            previous_response=json.dumps({"selectedActionIds": invented_ids}),
            candidate_actions=actions,
            selected_action_ids=invented_ids,
            auto_complete_enabled=False,
        )
    )

    assert context["allowedActionIds"]
    assert context["selectionOptions"]
    assert "These actionIds do not exist in allowedActionIds" in context["correctionMessage"]
    assert "- BIA_1_TO_2" in context["correctionMessage"]
    assert "You must not invent actionIds" in context["correctionMessage"]


def test_build_correction_prompt_handles_candidate_action_object(framework):
    actions, _ = build_candidate_actions(framework, {"DO.MQ.1": 4})
    previous_response = json.dumps(
        {
            "actionId": "DO_4_TO_5",
            "domainId": "DO",
            "domainName": "Data Storage",
        }
    )
    context = json.loads(
        build_correction_prompt(
            target_score=3.48,
            score_global_actual=2.48,
            target_gap=1.0,
            errors=[
                "Invalid LLM response: the model returned a candidateAction object instead of a selection object."
            ],
            previous_response=previous_response,
            candidate_actions=actions,
            auto_complete_enabled=False,
        )
    )

    assert "You returned a candidateAction object" in context["correctionMessage"]
    assert "DO_4_TO_5" in context["correctionMessage"]
    assert "selectedActionIds" in context["correctionMessage"]
    assert "Do not return actionId as a root field" in context["correctionMessage"]


def test_build_correction_prompt_handles_insufficient_gain(framework):
    actions, _ = build_candidate_actions(framework, {"DQ.MQ.1": 1, "DG.MQ.1": 2, "RMD.MQ.1": 1})
    context = json.loads(
        build_correction_prompt(
            target_score=3.48,
            score_global_actual=2.48,
            target_gap=1.0,
            errors=["LLM selected valid actions but cumulativeGain is lower than targetGap."],
            previous_response='{"selectedActionIds": ["DQ_1_TO_2", "DG_2_TO_3", "RMD_1_TO_2"]}',
            candidate_actions=actions,
            selected_gain=0.2,
            selected_action_ids=["DQ_1_TO_2", "DG_2_TO_3", "RMD_1_TO_2"],
            auto_complete_enabled=False,
        )
    )
    assert "Your selectedActionIds are valid but insufficient" in context["correctionMessage"]
    assert "Current cumulativeGain" in context["correctionMessage"]
    assert "Required targetGap = 1.0" in context["correctionMessage"]


def test_validate_rejects_excess_effort_selection(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores=_sample_high_gain_scores_for_test(framework),
    )
    candidate_actions, actions_by_id = build_candidate_actions(framework, request.currentScores)
    overshoot_ids = ["DQ_1_TO_5", "RMD_1_TO_5", "DG_2_TO_5"]
    payload = {
        "success": True,
        "selectedActionIds": overshoot_ids,
        "selectionReason": "Too much effort.",
        "warnings": [],
    }

    is_valid, errors, _ = validate_llm_selection_response(
        payload,
        request.targetScore,
        actions_by_id=actions_by_id,
        score_global_initial=request.scoreGlobalActual,
        candidate_actions=candidate_actions,
    )

    assert is_valid is False
    assert any("effortTotal is higher than the minimum" in error for error in errors)


def _sample_high_gain_scores_for_test(framework) -> dict[str, int]:
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


def test_validate_rejects_non_object_response(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DO.MQ.1": 4},
    )
    _, actions_by_id = build_candidate_actions(framework, request.currentScores)

    is_valid, errors, _ = validate_llm_selection_response(
        None,
        request.targetScore,
        actions_by_id=actions_by_id,
        score_global_initial=request.scoreGlobalActual,
    )

    assert is_valid is False
    assert any("response must be a JSON object" in error for error in errors)


def test_validate_rejects_candidate_action_object(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DO.MQ.1": 4},
    )
    candidate_actions, actions_by_id = build_candidate_actions(framework, request.currentScores)

    payload = {
        "actionId": "DO_4_TO_5",
        "domainId": "DO",
        "domainName": "Data Storage",
        "domainWeight": 10.0,
        "currentDomainScore": 4,
        "questionsToImprove": ["DO.MQ.1"],
    }

    is_valid, errors, _ = validate_llm_selection_response(
        payload,
        request.targetScore,
        actions_by_id=actions_by_id,
        score_global_initial=request.scoreGlobalActual,
        max_possible_gain=compute_max_possible_gain(candidate_actions),
        target_reachable=True,
    )

    assert is_valid is False
    assert any(
        "the model returned a candidateAction object instead of a selection object."
        in error
        for error in errors
    )


def test_validate_rejects_invented_action_ids(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"BIA.MQ.1": 4, "DO.MQ.1": 4, "FOI.MQ.1": 3, "DVR.MQ.1": 2, "DCM.MQ.1": 3},
    )
    candidate_actions, actions_by_id = build_candidate_actions(framework, request.currentScores)
    invented_ids = ["BIA_1_TO_2", "DO_1_TO_2", "FOI_1_TO_2", "DVR_1_TO_2", "DCM_1_TO_2"]

    payload = {
        "success": True,
        "selectedActionIds": invented_ids,
        "selectionReason": "Invented ids.",
        "warnings": [],
    }

    is_valid, errors, _ = validate_llm_selection_response(
        payload,
        request.targetScore,
        actions_by_id=actions_by_id,
        score_global_initial=request.scoreGlobalActual,
        max_possible_gain=compute_max_possible_gain(candidate_actions),
        target_reachable=True,
    )

    assert is_valid is False
    assert any(
        "BIA_1_TO_2 does not exist in allowedActionIds" in error for error in errors
    )
    assert any(
        "The LLM must copy exact actionIds from allowedActionIds" in error for error in errors
    )


def test_validate_rejects_domain_ids_instead_of_action_ids(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4, "FOI.MQ.1": 2, "BIA.MQ.1": 4},
    )
    candidate_actions, actions_by_id = build_candidate_actions(framework, request.currentScores)
    domain_ids = sorted({str(action["domainId"]) for action in actions_by_id.values()})[:4]

    payload = {
        "success": True,
        "selectedActionIds": domain_ids,
        "selectionReason": "Invalid domain selection.",
        "warnings": [],
    }

    is_valid, errors, _ = validate_llm_selection_response(
        payload,
        request.targetScore,
        actions_by_id=actions_by_id,
        score_global_initial=request.scoreGlobalActual,
        max_possible_gain=compute_max_possible_gain(candidate_actions),
        target_reachable=True,
    )

    assert is_valid is False
    assert any("is a domainId, not a valid actionId" in error for error in errors)


def test_validate_rejects_llm_computed_fields(framework):
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=2.6,
        currentScores={"DQ.MQ.4": 1, "DG.MQ.1": 2, "DG.MQ.2": 2, "DG.MQ.3": 2, "DG.MQ.4": 2},
    )
    candidate_actions, actions_by_id = build_candidate_actions(framework, request.currentScores)
    selected_ids = [candidate_actions[0]["actionId"]]

    payload = {
        "success": True,
        "selectedActionIds": selected_ids,
        "cumulativeGain": 99.0,
        "targetGap": 15.45,
        "targetReached": True,
        "selectionSteps": [],
        "selectionReason": "Bad math.",
        "warnings": [],
    }

    is_valid, errors, _ = validate_llm_selection_response(
        payload,
        request.targetScore,
        actions_by_id=actions_by_id,
        score_global_initial=request.scoreGlobalActual,
        max_possible_gain=compute_max_possible_gain(candidate_actions),
        target_reachable=True,
    )

    assert is_valid is False
    assert any("cumulativeGain must not be returned by the LLM" in error for error in errors)
    assert any("targetGap must not be returned by the LLM" in error for error in errors)
