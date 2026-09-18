import json
from typing import Any

from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.candidate_action_builder import (
    find_optimal_best_path,
    get_suggested_high_impact_action_ids,
    get_high_effort_level_five_action_ids,
)
from app.services.score_calculator import round_gain, round_score


def get_allowed_action_ids(candidate_actions: list[dict[str, Any]] | None) -> list[str]:
    candidate_actions = candidate_actions or []
    return [str(action["actionId"]) for action in candidate_actions if action.get("actionId")]


def sort_candidate_actions_for_prompt(
    candidate_actions: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    candidate_actions = candidate_actions or []
    return sorted(
        candidate_actions,
        key=lambda item: (
            -float(item["efficiencyRatio"]),
            -float(item["globalScoreGain"]),
            int(item["totalEffort"]),
            str(item["actionId"]),
        ),
    )


def _build_target_gap_rule(
    target_gap: float,
    *,
    score_global_actual: float,
    target_score: float,
) -> str:
    return (
        f"targetGap = scoreGlobalTarget - scoreGlobalInitial = {target_gap}\n"
        f"scoreGlobalInitial = {score_global_actual}\n"
        f"scoreGlobalTarget = {target_score}\n\n"
        "The selectedActionIds must satisfy:\n"
        "sum(globalScoreGain of selected actions) >= targetGap\n\n"
        "If not, add more valid actionIds from allowedActionIds.\n"
        "You must continue selecting actionIds until cumulativeGain >= targetGap.\n"
        "Do not stop before reaching targetGap.\n"
        "A low-effort path is valid only if it reaches the targetGap.\n"
        "If cumulativeGain < targetGap, the response is invalid."
    )


def _build_invalid_insufficient_example(
    allowed_action_ids: list[str],
    target_gap: float,
) -> dict[str, Any]:
    candidate_ids = ["DQ_1_TO_2", "DG_2_TO_3", "RMD_1_TO_2"]
    selected_ids = [action_id for action_id in candidate_ids if action_id in allowed_action_ids]
    if len(selected_ids) < 3:
        selected_ids = allowed_action_ids[:3]
    return {
        "invalidSelectionExample": {
            "success": True,
            "selectedActionIds": selected_ids,
            "selectionReason": "Too few actions selected.",
            "warnings": [],
        },
        "invalidSelectionReason": (
            f"The cumulativeGain is lower than targetGap = {target_gap}."
        ),
    }


def _build_valid_sufficient_example(
    candidate_actions: list[dict[str, Any]],
    allowed_action_ids: list[str],
    target_gap: float,
) -> dict[str, Any]:
    minimum_selection = find_optimal_best_path(
        candidate_actions,
        target_gap=target_gap,
    )
    if minimum_selection is not None:
        selected_ids = [
            action_id
            for action_id in minimum_selection["selectedActionIds"]
            if action_id in allowed_action_ids
        ]
    else:
        selected_ids = [
            action_id
            for action_id in get_suggested_high_impact_action_ids(candidate_actions, limit=9)
            if action_id in allowed_action_ids
        ]

    return {
        "validSelectionExample": {
            "success": True,
            "selectedActionIds": selected_ids,
            "selectionReason": "Selected the combination that reaches the target with the minimum possible effortTotal.",
            "warnings": [],
        }
    }


def _build_overgain_rule(target_score: float, score_global_actual: float) -> str:
    return (
        "Do not maximize the final score.\n"
        "Do not select actions that push the score far above the target unless required.\n"
        "Select the actionIds that reach the targetScore with the minimum possible effortTotal.\n\n"
        "Formula:\n"
        "overGain = scoreGlobalFinalEstimated - scoreGlobalTarget\n\n"
        "The best path is the valid path with the smallest effortTotal.\n"
        "If two paths reach the target, choose the one with lower effortTotal.\n"
        "If effortTotal is equal, choose the one with smaller overGain.\n\n"
        f"Example:\n"
        f"Path A: final score = {round(target_score, 2)}, effort = 72\n"
        f"Path B: final score = {round(target_score + 0.02, 2)}, effort = 57\n"
        "Choose Path B because it reaches the target with less effort."
    )


def _build_effort_minimization_rule(target_gap: float, target_score: float) -> str:
    return (
        "Do not maximize the final score.\n"
        "Do not push domains to level 5 unless required to reach the target.\n"
        "Prefer intermediate target levels like DQ 1 -> 3 instead of DQ 1 -> 5.\n"
        "After reaching targetGap, minimize effortTotal first, then overGain.\n"
        f"targetGap for this request is {target_gap}.\n"
        f"targetScore for this request is {target_score}."
    )


def _build_anti_overshoot_rule(target_score: float, target_gap: float) -> str:
    return (
        f"If targetGap is {target_gap}, do not select actions that exceed the target by a large margin "
        "if a closer combination can reach the target.\n"
        "Prefer a final score close to the target score.\n"
        f"If targetScore = {target_score}, a final score around {target_score} to "
        f"{round(target_score + 0.05, 2)} is better than {round(target_score + 0.2, 2)}."
    )


def _build_selection_priorities() -> list[str]:
    return [
        "Priority 1: scoreGlobalFinalEstimated >= scoreGlobalTarget.",
        "Priority 2: Minimize effortTotal.",
        "Priority 3: Minimize overGain.",
        "Priority 4: Maximize efficiencyRatio.",
    ]


def _build_effort_efficient_examples(recommended_action_ids: list[str]) -> list[str]:
    return recommended_action_ids[:5]


def _build_high_effort_avoidance_rule(high_effort_action_ids: list[str]) -> str:
    examples = ", ".join(high_effort_action_ids[:6]) if high_effort_action_ids else "DQ_1_TO_5, RMD_1_TO_5"
    return (
        "Avoid selecting only high target actions like DQ_1_TO_5 or RMD_1_TO_5 "
        "if smaller actions like DQ_1_TO_3, DG_2_TO_4, RMD_1_TO_2 can reach the target with less effort.\n"
        f"High-effort level-5 examples to avoid unless necessary: {examples}."
    )


def _build_selection_option_label(action: dict[str, Any]) -> str:
    return (
        f"{action['domainId']} {action['domainName']}: "
        f"{action['currentDomainScore']} -> {action['targetDomainScore']}"
    )


def build_selection_options(candidate_actions: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    candidate_actions = candidate_actions or []
    return [
        {
            "actionId": str(action["actionId"]),
            "label": _build_selection_option_label(action),
            "globalScoreGain": action["globalScoreGain"],
            "totalEffort": action["totalEffort"],
            "efficiencyRatio": action["efficiencyRatio"],
        }
        for action in sort_candidate_actions_for_prompt(candidate_actions)
        if action.get("actionId")
    ]


def get_allowed_action_ids_from_selection_options(
    selection_options: list[dict[str, Any]] | None,
) -> list[str]:
    selection_options = selection_options or []
    return [
        str(option["actionId"])
        for option in selection_options
        if isinstance(option, dict) and option.get("actionId")
    ]


def get_example_low_gain_action_ids(
    candidate_actions: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> list[str]:
    by_low_gain = sorted(
        candidate_actions,
        key=lambda item: (float(item["globalScoreGain"]), -float(item["efficiencyRatio"])),
    )
    return [str(action["actionId"]) for action in by_low_gain[:limit]]


def _prepare_prompt_context(
    candidate_actions: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str], list[str]]:
    candidate_actions = candidate_actions or []
    selection_options = build_selection_options(candidate_actions)
    allowed_action_ids = get_allowed_action_ids_from_selection_options(selection_options)
    recommended_efficient_actions = [
        action_id
        for action_id in get_suggested_high_impact_action_ids(candidate_actions, limit=9)
        if action_id in allowed_action_ids
    ]
    high_effort_actions_to_avoid = [
        action_id
        for action_id in get_high_effort_level_five_action_ids(candidate_actions)
        if action_id in allowed_action_ids
    ]
    example_low_gain_action_ids = [
        action_id
        for action_id in get_example_low_gain_action_ids(candidate_actions)
        if action_id in allowed_action_ids and action_id not in recommended_efficient_actions
    ]
    if not example_low_gain_action_ids:
        example_low_gain_action_ids = [
            action_id
            for action_id in get_example_low_gain_action_ids(candidate_actions)
            if action_id in allowed_action_ids
        ]
    return (
        selection_options,
        allowed_action_ids,
        recommended_efficient_actions,
        example_low_gain_action_ids,
        high_effort_actions_to_avoid,
    )


def _looks_like_domain_id_only(action_id: str, known_domain_ids: set[str] | None) -> bool:
    known_domain_ids = known_domain_ids or set()
    return action_id in known_domain_ids and "_TO_" not in action_id


def _parse_response_json(previous_response: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(previous_response)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _looks_like_candidate_action_response(payload: dict[str, Any]) -> bool:
    if "selectedActionIds" in payload:
        return False
    candidate_markers = (
        "actionId",
        "domainId",
        "domainName",
        "domainWeight",
        "currentDomainScore",
        "questionsToImprove",
        "transitions",
        "globalScoreGain",
        "targetDomainScore",
    )
    return any(field in payload for field in candidate_markers)


def _build_candidate_action_object_correction_message(
    previous_payload: dict[str, Any],
    *,
    allowed_action_ids: list[str] | None = None,
) -> str:
    action_id = previous_payload.get("actionId")
    if not isinstance(action_id, str) or not action_id:
        action_id = "ACTION_ID_FROM_ALLOWED_LIST"
    elif allowed_action_ids and action_id not in allowed_action_ids:
        action_id = allowed_action_ids[0] if allowed_action_ids else "ACTION_ID_FROM_ALLOWED_LIST"

    example_selection = {
        "success": True,
        "selectedActionIds": [action_id],
        "selectionReason": "",
        "warnings": [],
    }
    return (
        "Your previous response is invalid.\n"
        "You returned a candidateAction object.\n"
        "You must return only the selection object.\n\n"
        "Required format:\n"
        f"{json.dumps(example_selection, ensure_ascii=False, indent=2)}\n\n"
        "Do not return actionId as a root field.\n"
        "Do not return domainId.\n"
        "Do not return questionsToImprove.\n"
        "Do not return transitions."
    )


def _build_domain_id_correction_message(
    invalid_action_ids: list[str],
    *,
    example_valid_action_ids: list[str],
) -> str:
    return (
        "Your previous response is invalid.\n"
        "You returned domainIds instead of actionIds.\n\n"
        f"Invalid:\n{json.dumps(invalid_action_ids)}\n\n"
        "You must return exact actionIds from allowedActionIds only.\n\n"
        f"Example valid actionIds:\n{json.dumps(example_valid_action_ids[:5])}\n\n"
        "Return a corrected JSON with selectedActionIds only from allowedActionIds."
    )


def _get_invented_action_ids(
    selected_action_ids: list[str] | None,
    allowed_action_ids: list[str] | None,
    *,
    known_domain_ids: set[str] | None = None,
) -> list[str]:
    selected_action_ids = selected_action_ids or []
    allowed_action_ids = allowed_action_ids or []
    allowed_set = set(allowed_action_ids)
    invented_ids: list[str] = []
    for action_id in selected_action_ids:
        if action_id in allowed_set:
            continue
        if known_domain_ids and _looks_like_domain_id_only(action_id, known_domain_ids):
            continue
        invented_ids.append(action_id)
    return invented_ids


def _build_invented_action_id_correction_message(invalid_action_ids: list[str]) -> str:
    bullet_lines = "\n".join(f"- {action_id}" for action_id in invalid_action_ids)
    return (
        "Your previous response is invalid.\n\n"
        "These actionIds do not exist in allowedActionIds:\n"
        f"{bullet_lines}\n\n"
        "You must not invent actionIds.\n"
        "You must copy exact values from allowedActionIds only.\n\n"
        "Return a corrected JSON using only allowedActionIds."
    )


def build_user_prompt(
    *,
    framework: NDIFramework,
    request: BestPathRequest,
    score_global_initial: float,
    candidate_actions: list[dict[str, Any]] | None,
    max_possible_gain: float,
    target_reachable: bool,
    auto_complete_enabled: bool = False,
) -> str:
    candidate_actions = candidate_actions or []
    score_global_actual = (
        request.scoreGlobalActual
        if request.scoreGlobalActual is not None
        else score_global_initial
    )
    target_gap = round_gain(request.targetScore - score_global_actual)
    (
        selection_options,
        allowed_action_ids,
        recommended_efficient_actions,
        _,
        high_effort_actions_to_avoid,
    ) = _prepare_prompt_context(candidate_actions)

    insufficient_example = _build_invalid_insufficient_example(allowed_action_ids, target_gap)
    valid_example = _build_valid_sufficient_example(
        candidate_actions,
        allowed_action_ids,
        target_gap,
    )

    data_context = {
        "task": "Select actionIds only.",
        "scoreGlobalActual": score_global_actual,
        "targetScore": request.targetScore,
        "targetGap": target_gap,
        "allowedActionIds": allowed_action_ids,
        "selectionOptions": selection_options,
        "targetGapRule": _build_target_gap_rule(
            target_gap,
            score_global_actual=score_global_actual,
            target_score=request.targetScore,
        ),
        "overGainRule": _build_overgain_rule(request.targetScore, score_global_actual),
        "selectionObjective": (
            "Reach targetScore with the minimum possible effortTotal, then minimize overGain."
        ),
        **insufficient_example,
        **valid_example,
        "effortMinimizationRule": _build_effort_minimization_rule(
            target_gap,
            request.targetScore,
        ),
        "antiOvershootRule": _build_anti_overshoot_rule(request.targetScore, target_gap),
        "selectionPriorities": _build_selection_priorities(),
        "effortEfficientExamples": _build_effort_efficient_examples(recommended_efficient_actions),
        "highEffortActionsToAvoid": high_effort_actions_to_avoid,
        "highEffortAvoidanceRule": _build_high_effort_avoidance_rule(high_effort_actions_to_avoid),
    }

    return json.dumps(data_context, ensure_ascii=False, indent=2)


def _format_efficient_actions(action_ids: list[str]) -> str:
    if not action_ids:
        return ""
    lines = "\n".join(f"- {action_id}" for action_id in action_ids)
    return (
        "Prefer efficient low-effort actions such as:\n"
        f"{lines}\n\n"
        "Minimize totalEffort while reaching targetGap.\n"
        "Only use actionIds from allowedActionIds.\n"
    )


def _build_excess_effort_correction_message(
    *,
    score_global_final: float,
    target_score: float,
    selected_effort: int,
    minimum_effort: int,
    selected_action_ids: list[str] | None = None,
) -> str:
    message = (
        "Your selected path reaches the target but requires more effort than necessary.\n"
        f"Current final score = {round_score(score_global_final)}\n"
        f"Target score = {round_score(target_score)}\n"
        f"Current effortTotal = {selected_effort}\n"
        f"Minimum possible effortTotal = {minimum_effort}\n\n"
        "Select another combination of actionIds that reaches the target with lower effortTotal.\n"
        "Return only the JSON selection format."
    )
    if selected_action_ids:
        message += f"\nselectedActionIds = {json.dumps(selected_action_ids)}\n"
    return message


def _build_excess_overgain_correction_message(
    *,
    score_global_final: float,
    target_score: float,
    over_gain: float,
    selected_action_ids: list[str] | None = None,
) -> str:
    message = (
        "Your selected path reaches the target but exceeds it too much.\n"
        f"Current final score = {round_score(score_global_final)}\n"
        f"Target score = {round_score(target_score)}\n"
        f"OverGain = {round_gain(over_gain)}\n\n"
        "Select another combination of actionIds that reaches the target with a smaller overGain.\n"
        "Return only the JSON selection format."
    )
    if selected_action_ids:
        message += f"\nselectedActionIds = {json.dumps(selected_action_ids)}\n"
    return message


def _build_insufficient_gain_correction_message(
    *,
    selected_gain: float,
    target_gap: float,
    selected_action_ids: list[str] | None = None,
) -> str:
    remaining_gap = round_gain(max(target_gap - selected_gain, 0.0))
    message = (
        "Your selectedActionIds are valid but insufficient.\n"
        f"Current cumulativeGain = {round_gain(selected_gain)}\n"
        f"Required targetGap = {target_gap}\n"
        f"remainingGap = {remaining_gap}\n\n"
        "Add more actionIds from allowedActionIds until cumulativeGain >= targetGap.\n"
        "Return the same JSON format only.\n"
        "Do not stop before reaching targetGap.\n"
        "Minimize effort only after targetGap is reached."
    )
    if selected_action_ids:
        message += f"\nselectedActionIds = {json.dumps(selected_action_ids)}\n"
    return message


def _build_correction_message(
    errors: list[str],
    *,
    target_gap: float | None = None,
    selected_gain: float | None = None,
    selected_action_ids: list[str] | None = None,
    high_impact_action_ids: list[str] | None = None,
    allowed_action_ids: list[str] | None = None,
    known_domain_ids: set[str] | None = None,
    previous_response: str | None = None,
    repeated_selection: bool = False,
    auto_complete_enabled: bool = False,
    score_global_final: float | None = None,
    target_score: float | None = None,
) -> str:
    if previous_response:
        previous_payload = _parse_response_json(previous_response)
        if previous_payload and _looks_like_candidate_action_response(previous_payload):
            message = _build_candidate_action_object_correction_message(
                previous_payload,
                allowed_action_ids=allowed_action_ids,
            )
            message += "\n\nReturn only the corrected JSON."
            return message

    if repeated_selection:
        message = (
            "The previous selection was repeated and is still invalid. "
            "You must add more actionIds. Returning the same selectedActionIds is forbidden.\n\n"
        )
    else:
        message = "Your previous selection is invalid.\n"

    domain_only_ids: list[str] = []
    if selected_action_ids and known_domain_ids:
        domain_only_ids = [
            action_id
            for action_id in selected_action_ids
            if _looks_like_domain_id_only(action_id, known_domain_ids)
        ]

    if domain_only_ids:
        example_valid = high_impact_action_ids or (allowed_action_ids or [])[:5]
        message = _build_domain_id_correction_message(
            domain_only_ids,
            example_valid_action_ids=example_valid,
        )
        message += "\n\nReturn only the corrected JSON."
        return message

    invented_action_ids: list[str] = []
    if selected_action_ids and allowed_action_ids:
        invented_action_ids = _get_invented_action_ids(
            selected_action_ids,
            allowed_action_ids,
            known_domain_ids=known_domain_ids,
        )
    if invented_action_ids:
        message = _build_invented_action_id_correction_message(invented_action_ids)
        message += "\n\nReturn only the corrected JSON."
        return message

    if (
        score_global_final is not None
        and target_score is not None
        and score_global_final >= target_score
        and errors
        and any(
            "effortTotal is higher than the minimum" in str(error)
            for error in errors
        )
    ):
        minimum_effort = 0
        selected_effort = 0
        for error in errors:
            if "Minimum possible effortTotal =" in str(error):
                try:
                    minimum_effort = int(str(error).split("=")[-1].strip().rstrip("."))
                except ValueError:
                    pass
            if "Current effortTotal =" in str(error):
                try:
                    selected_effort = int(str(error).split("=")[-1].strip().rstrip("."))
                except ValueError:
                    pass
        message = _build_excess_effort_correction_message(
            score_global_final=score_global_final,
            target_score=target_score,
            selected_effort=selected_effort,
            minimum_effort=minimum_effort,
            selected_action_ids=selected_action_ids,
        )
        message += "\n\nReturn only the corrected JSON."
        return message

    if (
        score_global_final is not None
        and target_score is not None
        and score_global_final >= target_score
        and errors
        and any(
            "exceeds it too much" in str(error)
            or "exceeds it more than necessary" in str(error)
            for error in errors
        )
    ):
        over_gain = round_gain(max(score_global_final - target_score, 0.0))
        message = _build_excess_overgain_correction_message(
            score_global_final=score_global_final,
            target_score=target_score,
            over_gain=over_gain,
            selected_action_ids=selected_action_ids,
        )
        message += "\n\nReturn only the corrected JSON."
        return message

    if (
        target_gap is not None
        and selected_gain is not None
        and selected_gain < target_gap
        and selected_action_ids
    ):
        message = _build_insufficient_gain_correction_message(
            selected_gain=selected_gain,
            target_gap=target_gap,
            selected_action_ids=selected_action_ids,
        )
        if high_impact_action_ids:
            message += "\n\n" + _format_efficient_actions(high_impact_action_ids)
        message += "\n\nReturn only the corrected JSON."
        return message

    if errors:
        errors = errors or []
        bullet_lines = "\n".join(f"- {error}" for error in errors[:20])
        message += f"{bullet_lines}\n"

    if target_gap is not None and selected_gain is not None:
        remaining_gap = round_gain(max(target_gap - selected_gain, 0.0))
        message += (
            f"\nselectedGain = {round_gain(selected_gain)}\n"
            f"targetGap = {target_gap}\n"
            f"remainingGap = {remaining_gap}\n\n"
            "Your previous selection is invalid because cumulativeGain is lower than targetGap. "
            "You must select additional exact actionIds from allowedActionIds until cumulativeGain >= targetGap.\n"
            "You must return a new selection with additional actionIds.\n"
            "Do not return the same selectedActionIds again.\n"
            "Do not calculate cumulativeGain, targetGap or targetReached in your JSON.\n"
        )
        if not auto_complete_enabled:
            message += "Do not rely on backend auto-completion.\n"
        if selected_action_ids:
            message += f"\nselectedActionIds = {json.dumps(selected_action_ids)}\n\n"

    if high_impact_action_ids:
        message += _format_efficient_actions(high_impact_action_ids)
        message += (
            "Do not push domains to level 5 unless necessary.\n"
            "Prefer intermediate actions with lower totalEffort.\n"
        )

    message += "\nReturn only the corrected JSON."
    return message


def build_correction_prompt(
    *,
    target_score: float,
    score_global_actual: float,
    target_gap: float,
    errors: list[str],
    previous_response: str,
    candidate_actions: list[dict[str, Any]] | None = None,
    selected_gain: float | None = None,
    selected_action_ids: list[str] | None = None,
    high_impact_action_ids: list[str] | None = None,
    repeated_selection: bool = False,
    max_possible_gain: float | None = None,
    target_reachable: bool | None = None,
    auto_complete_enabled: bool = False,
    score_global_final: float | None = None,
) -> str:
    selection_options: list[dict[str, Any]] | None = None
    allowed_action_ids: list[str] | None = None
    recommended_efficient_actions: list[str] | None = None
    known_domain_ids: set[str] | None = None
    if candidate_actions is not None:
        candidate_actions = candidate_actions or []
        (
            selection_options,
            allowed_action_ids,
            recommended_efficient_actions,
            _,
            _,
        ) = _prepare_prompt_context(candidate_actions)
        known_domain_ids = {str(action["domainId"]) for action in candidate_actions}
        if high_impact_action_ids is None:
            high_impact_action_ids = recommended_efficient_actions

    correction_context: dict[str, Any] = {
        "task": "Correct your action selection. Return only selectedActionIds.",
        "scoreGlobalActual": score_global_actual,
        "targetScore": target_score,
        "targetGap": target_gap,
        "validationErrors": errors,
        "previousResponse": previous_response,
        "correctionMessage": _build_correction_message(
            errors,
            target_gap=target_gap,
            selected_gain=selected_gain,
            selected_action_ids=selected_action_ids,
            high_impact_action_ids=high_impact_action_ids,
            allowed_action_ids=allowed_action_ids,
            known_domain_ids=known_domain_ids,
            previous_response=previous_response,
            repeated_selection=repeated_selection,
            auto_complete_enabled=auto_complete_enabled,
            score_global_final=score_global_final,
            target_score=target_score,
        ),
    }
    if allowed_action_ids is not None:
        correction_context = {
            "allowedActionIds": allowed_action_ids,
            **correction_context,
        }
    if selection_options is not None:
        correction_context["selectionOptions"] = selection_options

    return json.dumps(correction_context, ensure_ascii=False, indent=2)
