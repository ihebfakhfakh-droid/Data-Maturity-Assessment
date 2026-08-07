import json
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.recommendation_models import NDIFramework
from app.services.exact_path_optimizer import _from_units, _to_units
from app.services.score_calculator import (
    build_expected_transitions,
    compute_domain_score,
    compute_expected_global_gain,
    compute_total_framework_weight,
    get_domain_answered_scores,
    round_gain,
    round_score,
)

logger = logging.getLogger(__name__)

OPTIMIZER_MAX_BEAM_SIZE = 200
OPTIMIZER_MAX_RUNTIME_SECONDS = 3.0
OPTIMIZER_MAX_ACTIONS_PER_DOMAIN = 4
OPTIMIZER_NO_VALID_PATH_MESSAGE = "No valid path found within optimizer constraints."


@dataclass(frozen=True)
class _BeamState:
    action_ids: tuple[str, ...] = field(default_factory=tuple)
    gain: float = 0.0
    effort: int = 0
    efficiency_total: float = 0.0


def _group_pruned_domain_actions(
    candidate_actions: list[dict[str, Any]],
    *,
    max_actions_per_domain: int = OPTIMIZER_MAX_ACTIONS_PER_DOMAIN,
) -> dict[str, list[dict[str, Any]]]:
    by_domain: dict[str, list[dict[str, Any]]] = {}
    for action in candidate_actions:
        by_domain.setdefault(str(action["domainId"]), []).append(action)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for domain_id, actions in by_domain.items():
        sorted_actions = sorted(
            actions,
            key=lambda item: (
                int(item["targetDomainScore"]),
                -float(item["efficiencyRatio"]),
                str(item["actionId"]),
            ),
        )
        grouped[domain_id] = sorted_actions[:max_actions_per_domain]
    return grouped


def _beam_prune_key(state: _BeamState, *, target_gap: float) -> tuple[Any, ...]:
    rounded_gain = round_gain(state.gain)
    if rounded_gain >= target_gap:
        over_gain = round_gain(max(rounded_gain - target_gap, 0.0))
        return (0, state.effort, over_gain, -state.efficiency_total, state.action_ids)
    return (
        1,
        round_gain(target_gap - rounded_gain),
        state.effort,
        -state.efficiency_total,
        state.action_ids,
    )


def _beam_final_key(state: _BeamState, *, target_gap: float) -> tuple[Any, ...]:
    rounded_gain = round_gain(state.gain)
    over_gain = round_gain(max(rounded_gain - target_gap, 0.0))
    return (
        state.effort,
        over_gain,
        -state.efficiency_total,
        state.action_ids,
    )


def _dedupe_beam_states(states: list[_BeamState], *, target_gap: float) -> list[_BeamState]:
    best_by_actions: dict[tuple[str, ...], _BeamState] = {}
    for state in states:
        existing = best_by_actions.get(state.action_ids)
        if existing is None or _beam_prune_key(state, target_gap=target_gap) < _beam_prune_key(
            existing,
            target_gap=target_gap,
        ):
            best_by_actions[state.action_ids] = state
    return list(best_by_actions.values())


def _state_from_action(previous: _BeamState, action: dict[str, Any]) -> _BeamState:
    action_id = str(action["actionId"])
    return _BeamState(
        action_ids=previous.action_ids + (action_id,),
        gain=round_gain(previous.gain + float(action["globalScoreGain"])),
        effort=previous.effort + int(action["totalEffort"]),
        efficiency_total=previous.efficiency_total + float(action["efficiencyRatio"]),
    )


def _run_beam_search_optimizer(
    candidate_actions: list[dict[str, Any]],
    *,
    target_gap: float,
    max_beam_size: int = OPTIMIZER_MAX_BEAM_SIZE,
    max_runtime_seconds: float = OPTIMIZER_MAX_RUNTIME_SECONDS,
    max_actions_per_domain: int = OPTIMIZER_MAX_ACTIONS_PER_DOMAIN,
) -> dict[str, Any] | None:
    started_at = time.monotonic()
    grouped_actions = _group_pruned_domain_actions(
        candidate_actions,
        max_actions_per_domain=max_actions_per_domain,
    )
    domains = sorted(grouped_actions.keys())

    logger.info("Optimizer started")
    logger.info("candidateActions count: %s", len(candidate_actions))
    logger.info("domains count: %s", len(grouped_actions))

    if not domains:
        logger.info("optimizer duration: %.4fs", time.monotonic() - started_at)
        return None

    states = [_BeamState()]
    best_valid_state: _BeamState | None = None
    timed_out = False

    for domain_id in domains:
        if time.monotonic() - started_at >= max_runtime_seconds:
            timed_out = True
            logger.warning("Optimizer time limit reached after %.2fs", max_runtime_seconds)
            break

        domain_actions = grouped_actions[domain_id]
        expanded_states: list[_BeamState] = []
        for state in states:
            expanded_states.append(state)
            for action in domain_actions:
                expanded_states.append(_state_from_action(state, action))

        states = sorted(
            _dedupe_beam_states(expanded_states, target_gap=target_gap),
            key=lambda item: _beam_prune_key(item, target_gap=target_gap),
        )[:max_beam_size]

        for state in states:
            if round_gain(state.gain) >= target_gap and (
                best_valid_state is None
                or _beam_final_key(state, target_gap=target_gap)
                < _beam_final_key(best_valid_state, target_gap=target_gap)
            ):
                best_valid_state = state

    valid_states = [state for state in states if round_gain(state.gain) >= target_gap]
    if best_valid_state is None and valid_states:
        best_valid_state = min(
            valid_states,
            key=lambda item: _beam_final_key(item, target_gap=target_gap),
        )
    elif best_valid_state is not None and valid_states:
        candidate_best = min(
            valid_states,
            key=lambda item: _beam_final_key(item, target_gap=target_gap),
        )
        if _beam_final_key(candidate_best, target_gap=target_gap) < _beam_final_key(
            best_valid_state,
            target_gap=target_gap,
        ):
            best_valid_state = candidate_best

    duration = time.monotonic() - started_at
    if best_valid_state is None:
        logger.info("optimizer duration: %.4fs", duration)
        logger.warning("Optimizer found no valid path within beam constraints.")
        return None

    selected_gain = round_gain(best_valid_state.gain)
    over_gain = round_gain(max(selected_gain - target_gap, 0.0))
    logger.info("best gain: %s", selected_gain)
    logger.info("best effort: %s", best_valid_state.effort)
    logger.info("optimizer duration: %.4fs", duration)
    if timed_out:
        logger.warning("Optimizer returned best valid state found before timeout.")

    return {
        "selectedActionIds": list(best_valid_state.action_ids),
        "gainTotal": selected_gain,
        "effortTotal": best_valid_state.effort,
        "overGain": over_gain,
        "durationSeconds": round(duration, 4),
        "timedOut": timed_out,
    }


def _action_id(domain_id: str, current_domain_score: int, target_domain_score: int) -> str:
    return f"{domain_id}_{current_domain_score}_TO_{target_domain_score}"


def _build_question_improvement(
    framework: NDIFramework,
    *,
    question_code: str,
    question_text: str,
    current_score: int,
    target_score: int,
) -> dict[str, Any]:
    transitions = build_expected_transitions(
        framework=framework,
        question_id=question_code,
        current_score=current_score,
        target_score=target_score,
    )
    total_question_effort = sum(int(item["effort"]) for item in transitions)
    return {
        "questionCode": question_code,
        "questionText": question_text,
        "currentScore": current_score,
        "targetScore": target_score,
        "totalQuestionEffort": total_question_effort,
        "transitions": transitions,
    }


def _questions_to_improve(
    framework: NDIFramework,
    domain_id: str,
    answered_scores: dict[str, int],
    target_domain_score: int,
) -> list[dict[str, Any]]:
    domain = framework.get_domain(domain_id)
    if domain is None:
        return []

    improvements: list[dict[str, Any]] = []
    for question in domain.questions:
        if question.id not in answered_scores:
            continue
        current_score = answered_scores[question.id]
        if current_score >= target_domain_score:
            continue
        improvements.append(
            _build_question_improvement(
                framework,
                question_code=question.id,
                question_text=question.text,
                current_score=current_score,
                target_score=target_domain_score,
            )
        )
    return improvements


def build_candidate_actions(
    framework: NDIFramework,
    current_scores: dict[str, int],
    *,
    total_weights: float | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    denominator = total_weights if total_weights is not None else compute_total_framework_weight(framework)
    actions: list[dict[str, Any]] = []
    actions_by_id: dict[str, dict[str, Any]] = {}

    for domain in framework.domains:
        answered = get_domain_answered_scores(domain, current_scores)
        if not answered:
            continue

        current_domain_score = compute_domain_score(answered)
        max_target = max(question.maxScore for question in domain.questions)

        for target_domain_score in range(current_domain_score + 1, max_target + 1):
            questions = _questions_to_improve(
                framework,
                domain.domain_id,
                answered,
                target_domain_score,
            )
            if not questions:
                continue

            total_effort = sum(int(item["totalQuestionEffort"]) for item in questions)
            global_score_gain = compute_expected_global_gain(
                framework=framework,
                current_scores=current_scores,
                domain_id=domain.domain_id,
                current_domain_score=current_domain_score,
                target_domain_score=target_domain_score,
                total_weights=denominator,
            )
            efficiency_ratio = (
                round(global_score_gain / total_effort, 4) if total_effort > 0 else 0.0
            )

            action = {
                "actionId": _action_id(
                    domain.domain_id,
                    current_domain_score,
                    target_domain_score,
                ),
                "domainId": domain.domain_id,
                "domainName": domain.domain_name,
                "domainWeight": domain.weight,
                "currentDomainScore": current_domain_score,
                "targetDomainScore": target_domain_score,
                "domainScoreGain": target_domain_score - current_domain_score,
                "globalScoreGain": global_score_gain,
                "totalEffort": total_effort,
                "efficiencyRatio": efficiency_ratio,
                "questionsToImprove": questions,
            }
            actions.append(action)
            actions_by_id[action["actionId"]] = action

    actions.sort(key=lambda item: (-item["efficiencyRatio"], item["totalEffort"], item["actionId"]))
    return actions, actions_by_id


def compute_max_possible_gain(candidate_actions: list[dict[str, Any]]) -> float:
    best_gain_by_domain: dict[str, float] = {}
    for action in candidate_actions:
        domain_id = str(action["domainId"])
        gain = float(action["globalScoreGain"])
        current_best = best_gain_by_domain.get(domain_id, 0.0)
        if gain > current_best:
            best_gain_by_domain[domain_id] = gain
    return round_gain(sum(best_gain_by_domain.values()))


def get_suggested_high_impact_action_ids(
    candidate_actions: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> list[str]:
    best_by_domain: dict[str, dict[str, Any]] = {}
    for action in candidate_actions:
        domain_id = str(action["domainId"])
        current_best = best_by_domain.get(domain_id)
        if current_best is None or (
            float(action["efficiencyRatio"]) > float(current_best["efficiencyRatio"])
            or (
                float(action["efficiencyRatio"]) == float(current_best["efficiencyRatio"])
                and int(action["totalEffort"]) < int(current_best["totalEffort"])
            )
            or (
                float(action["efficiencyRatio"]) == float(current_best["efficiencyRatio"])
                and int(action["totalEffort"]) == int(current_best["totalEffort"])
                and float(action["globalScoreGain"]) > float(current_best["globalScoreGain"])
            )
        ):
            best_by_domain[domain_id] = action

    sorted_actions = sorted(
        best_by_domain.values(),
        key=lambda item: (
            -float(item["efficiencyRatio"]),
            -float(item["globalScoreGain"]),
            int(item["totalEffort"]),
            str(item["actionId"]),
        ),
    )
    return [str(action["actionId"]) for action in sorted_actions[:limit]]


def get_high_effort_level_five_action_ids(
    candidate_actions: list[dict[str, Any]],
) -> list[str]:
    actions_by_domain: dict[str, list[dict[str, Any]]] = {}
    for action in candidate_actions:
        actions_by_domain.setdefault(str(action["domainId"]), []).append(action)

    high_effort_ids: list[str] = []
    for domain_actions in actions_by_domain.values():
        has_intermediate = any(
            int(action["targetDomainScore"]) < 5 for action in domain_actions
        )
        if not has_intermediate:
            continue
        for action in domain_actions:
            if (
                int(action["targetDomainScore"]) == 5
                and int(action["currentDomainScore"]) <= 2
            ):
                high_effort_ids.append(str(action["actionId"]))
    return sorted(high_effort_ids)


def find_minimum_effort_selection_ids(
    candidate_actions: list[dict[str, Any]],
    *,
    target_gap: float,
) -> tuple[list[str], int, float] | None:
    result = find_optimal_best_path(candidate_actions, target_gap=target_gap)
    if result is None:
        return None
    return (
        [str(action_id) for action_id in result["selectedActionIds"]],
        int(result["effortTotal"]),
        float(result["gainTotal"]),
    )


def find_minimum_overgain_selection_ids(
    candidate_actions: list[dict[str, Any]],
    *,
    target_gap: float,
) -> tuple[list[str], int, float, float] | None:
    result = find_optimal_best_path(candidate_actions, target_gap=target_gap)
    if result is None:
        return None
    return (
        [str(action_id) for action_id in result["selectedActionIds"]],
        int(result["effortTotal"]),
        float(result["gainTotal"]),
        float(result["overGain"]),
    )


def find_optimal_best_path(
    candidate_actions: list[dict[str, Any]],
    *,
    target_gap: float,
) -> dict[str, Any] | None:
    """Return the valid combination with minimum effort using exact dynamic programming."""
    if not candidate_actions:
        return None

    total_weight = Decimal("0")
    seen_domains: set[str] = set()
    for action in candidate_actions:
        domain_id = str(action["domainId"])
        if domain_id in seen_domains:
            continue
        seen_domains.add(domain_id)
        total_weight += Decimal(str(action["domainWeight"]))
    if total_weight <= 0:
        return None

    required_gain_units = _to_units(Decimal(str(target_gap)) * total_weight)
    target_weighted_units = required_gain_units

    grouped: dict[str, list[dict[str, Any]]] = {}
    for action in candidate_actions:
        grouped.setdefault(str(action["domainId"]), []).append(action)

    @dataclass(frozen=True)
    class _ActionSolution:
        effort: int
        over_gain_units: int
        question_count: int
        domain_count: int
        domain_ids: tuple[str, ...]
        weighted_gain_units: int
        action_ids: tuple[str, ...]

    def _action_weighted_gain(action: dict[str, Any]) -> Decimal:
        return Decimal(str(action["domainScoreGain"])) * Decimal(str(action["domainWeight"]))

    def _merge_action_solution(previous: _ActionSolution, action: dict[str, Any] | None) -> _ActionSolution:
        if action is None:
            return previous
        weighted_gain_units = previous.weighted_gain_units + _to_units(_action_weighted_gain(action))
        effort = previous.effort + int(action["totalEffort"])
        questions = action.get("questionsToImprove", [])
        question_count = previous.question_count + (len(questions) if isinstance(questions, list) else 0)
        domain_ids = previous.domain_ids + (str(action["domainId"]),)
        action_ids = previous.action_ids + (str(action["actionId"]),)
        over_gain_units = max(weighted_gain_units - target_weighted_units, 0)
        return _ActionSolution(
            effort=effort,
            over_gain_units=over_gain_units,
            question_count=question_count,
            domain_count=len(domain_ids),
            domain_ids=domain_ids,
            weighted_gain_units=weighted_gain_units,
            action_ids=action_ids,
        )

    def _action_solution_key(solution: _ActionSolution) -> tuple[Any, ...]:
        return (
            solution.effort,
            solution.over_gain_units,
            solution.question_count,
            solution.domain_count,
            solution.domain_ids,
        )

    def _better_action_solution(candidate: _ActionSolution, current: _ActionSolution | None) -> bool:
        if current is None:
            return True
        return _action_solution_key(candidate) < _action_solution_key(current)

    empty = _ActionSolution(0, 0, 0, 0, (), 0, ())
    states: dict[int, _ActionSolution] = {0: empty}

    for domain_id in sorted(grouped.keys()):
        domain_actions = grouped[domain_id]
        next_states: dict[int, _ActionSolution] = {}
        for gain_units, state in states.items():
            for candidate in (None, *domain_actions):
                merged = _merge_action_solution(state, candidate)
                existing = next_states.get(merged.weighted_gain_units)
                if _better_action_solution(merged, existing):
                    next_states[merged.weighted_gain_units] = merged
        states = next_states

    best: _ActionSolution | None = None
    for gain_units, state in states.items():
        if gain_units < required_gain_units:
            continue
        if _better_action_solution(state, best):
            best = state
    if best is None:
        return None

    selected_gain = float(_from_units(best.weighted_gain_units) / total_weight)
    over_gain = max(selected_gain - float(target_gap), 0.0)
    return {
        "selectedActionIds": list(best.action_ids),
        "gainTotal": round_gain(selected_gain),
        "effortTotal": best.effort,
        "overGain": round_gain(over_gain),
    }


BACKEND_OPTIMIZER_SELECTED_WARNING = (
    "LLM selection was insufficient. Backend optimizer selected the minimum-effort valid path to the target."
)

BACKEND_OPTIMIZER_EXCESS_OVERGAIN_WARNING = (
    "LLM selection was suboptimal. Backend optimizer selected the minimum-effort valid path to the target."
)

EXCESS_EFFORT_SELECTION_MESSAGE = (
    "LLM selected path reaches the target but effortTotal is higher than the minimum possible effortTotal."
)

EXCESS_OVERGAIN_MESSAGE = EXCESS_EFFORT_SELECTION_MESSAGE

EFFORT_SUBOPTIMAL_WARNING = (
    "The selected path reaches the target but may not be effort-optimal."
)


def compute_over_gain(
    *,
    score_global_initial: float,
    selected_gain: float,
    target_score: float,
) -> float:
    score_global_final = round_score(score_global_initial + selected_gain)
    return round_gain(max(score_global_final - target_score, 0.0))


def build_overgain_optimality_warning(
    selected_action_ids: list[str],
    actions_by_id: dict[str, dict[str, Any]],
    candidate_actions: list[dict[str, Any]],
    *,
    target_gap: float,
    score_global_initial: float,
    target_score: float,
) -> str | None:
    selected_gain, selected_effort = compute_selection_totals(
        selected_action_ids,
        actions_by_id,
    )
    if selected_gain < target_gap:
        return None

    optimal_path = find_optimal_best_path(candidate_actions, target_gap=target_gap)
    if optimal_path is None:
        return None

    minimum_effort = int(optimal_path["effortTotal"])
    minimum_over_gain = float(optimal_path["overGain"])
    selected_over_gain = compute_over_gain(
        score_global_initial=score_global_initial,
        selected_gain=selected_gain,
        target_score=target_score,
    )

    if selected_effort <= minimum_effort and selected_over_gain <= minimum_over_gain + 0.01:
        return None

    if selected_effort > minimum_effort:
        return EFFORT_SUBOPTIMAL_WARNING

    return (
        "The selected path reaches the target but exceeds it more than necessary. "
        f"overGain={selected_over_gain}, minimum possible overGain={minimum_over_gain}."
    )


def build_effort_optimality_warning(
    selected_action_ids: list[str],
    actions_by_id: dict[str, dict[str, Any]],
    candidate_actions: list[dict[str, Any]],
    *,
    target_gap: float,
    score_global_initial: float,
    target_score: float,
) -> str | None:
    selected_gain, selected_effort = compute_selection_totals(
        selected_action_ids,
        actions_by_id,
    )
    if selected_gain < target_gap:
        return None

    minimum_selection = find_minimum_effort_selection_ids(
        candidate_actions,
        target_gap=target_gap,
    )
    if minimum_selection is None:
        return None

    _, minimum_effort, _ = minimum_selection
    if selected_effort <= minimum_effort:
        return None

    score_global_final = round_score(score_global_initial + selected_gain)
    over_target = score_global_final - target_score
    if over_target > 0.05 or selected_effort > minimum_effort:
        return EFFORT_SUBOPTIMAL_WARNING
    return None


def complete_selection_to_target(
    selected_action_ids: list[str],
    actions_by_id: dict[str, dict[str, Any]],
    candidate_actions: list[dict[str, Any]],
    *,
    target_gap: float,
) -> list[str]:
    used_domains: set[str] = set()
    completed_ids: list[str] = []
    cumulative_gain = 0.0

    for action_id in selected_action_ids:
        action = actions_by_id.get(action_id)
        if action is None:
            continue
        domain_id = str(action["domainId"])
        if domain_id in used_domains:
            continue
        used_domains.add(domain_id)
        completed_ids.append(action_id)
        cumulative_gain += float(action["globalScoreGain"])

    if round_gain(cumulative_gain) >= target_gap:
        return completed_ids

    remaining_actions = [
        action for action in candidate_actions if str(action["domainId"]) not in used_domains
    ]
    remaining_actions.sort(
        key=lambda item: (
            -float(item["efficiencyRatio"]),
            -float(item["globalScoreGain"]),
            str(item["actionId"]),
        )
    )

    for action in remaining_actions:
        if round_gain(cumulative_gain) >= target_gap:
            break
        action_id = str(action["actionId"])
        domain_id = str(action["domainId"])
        if domain_id in used_domains:
            continue
        used_domains.add(domain_id)
        completed_ids.append(action_id)
        cumulative_gain += float(action["globalScoreGain"])

    return completed_ids


def build_partial_best_path_from_selection(
    selected_action_ids: list[str] | None,
    actions_by_id: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    selected_action_ids = selected_action_ids or []
    actions_by_id = actions_by_id or {}
    best_path: list[dict[str, Any]] = []
    seen_domains: set[str] = set()
    priority = 1

    for action_id in selected_action_ids:
        action = actions_by_id.get(action_id)
        if action is None:
            continue
        domain_id = str(action.get("domainId", ""))
        if domain_id in seen_domains:
            continue
        seen_domains.add(domain_id)
        best_path.append(
            {
                "priority": priority,
                "domainId": action.get("domainId"),
                "domainName": action.get("domainName"),
                "domainWeight": action.get("domainWeight"),
                "currentDomainScore": action.get("currentDomainScore"),
                "targetDomainScore": action.get("targetDomainScore"),
                "globalScoreGain": action.get("globalScoreGain"),
                "totalEffort": action.get("totalEffort"),
                "efficiencyRatio": action.get("efficiencyRatio"),
                "questionsToImprove": action.get("questionsToImprove", []),
            }
        )
        priority += 1
    return best_path


def compute_selection_totals(
    selected_action_ids: list[str] | None,
    actions_by_id: dict[str, dict[str, Any]] | None,
) -> tuple[float, int]:
    selected_action_ids = selected_action_ids or []
    actions_by_id = actions_by_id or {}
    selected_gain = round_gain(
        sum(
            float(actions_by_id[action_id]["globalScoreGain"])
            for action_id in selected_action_ids
            if action_id in actions_by_id
        )
    )
    selected_effort = sum(
        int(actions_by_id[action_id]["totalEffort"])
        for action_id in selected_action_ids
        if action_id in actions_by_id
    )
    return selected_gain, selected_effort


def build_selection_steps_from_ids(
    selected_action_ids: list[str],
    actions_by_id: dict[str, dict[str, Any]],
    *,
    target_gap: float,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    running_gain = 0.0
    for step_number, action_id in enumerate(selected_action_ids, start=1):
        action = actions_by_id[action_id]
        action_gain = float(action["globalScoreGain"])
        running_gain = round_gain(running_gain + action_gain)
        steps.append(
            {
                "step": step_number,
                "actionId": action_id,
                "globalScoreGain": action_gain,
                "runningCumulativeGain": running_gain,
                "remainingGap": round_gain(max(target_gap - running_gain, 0.0)),
            }
        )
    return steps


def save_candidate_actions_debug(
    *,
    score_global_actual: float,
    target_score: float,
    candidate_actions: list[dict[str, Any]],
    output_path: Path | None = None,
) -> Path:
    target_path = output_path or settings.DEBUG_CANDIDATE_ACTIONS_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_gap = round_gain(target_score - score_global_actual)
    max_possible_gain = compute_max_possible_gain(candidate_actions)
    by_efficiency = sorted(
        candidate_actions,
        key=lambda item: (-float(item["efficiencyRatio"]), -float(item["globalScoreGain"])),
    )
    by_gain = sorted(
        candidate_actions,
        key=lambda item: (-float(item["globalScoreGain"]), float(item["totalEffort"])),
    )
    debug_document = {
        "scoreGlobalActual": score_global_actual,
        "targetScore": target_score,
        "targetGap": target_gap,
        "maxPossibleGain": max_possible_gain,
        "targetReachable": max_possible_gain >= target_gap,
        "candidateActionsByEfficiencyRatio": by_efficiency,
        "candidateActionsByGlobalScoreGain": by_gain,
        "candidateActions": candidate_actions,
    }
    target_path.write_text(
        json.dumps(debug_document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target_path


def save_allowed_action_ids_debug(
    *,
    score_global_actual: float,
    target_score: float,
    candidate_actions: list[dict[str, Any]],
    output_path: Path | None = None,
) -> Path:
    target_path = output_path or settings.DEBUG_ALLOWED_ACTION_IDS_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_gap = round_gain(target_score - score_global_actual)
    allowed_action_ids = [str(action["actionId"]) for action in candidate_actions]
    debug_document = {
        "allowedActionIds": allowed_action_ids,
        "candidateActions": candidate_actions,
        "scoreGlobalActual": score_global_actual,
        "targetScore": target_score,
        "targetGap": target_gap,
    }
    target_path.write_text(
        json.dumps(debug_document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target_path


SUMMARY_FIELDS = (
    "optimizationLogic",
    "selectedDomainsReason",
    "effortInterpretation",
    "finalValidation",
)

CONTRADICTORY_WARNING_PATTERNS_WHEN_REACHED = (
    "target score not",
    "target not reached",
    "not yet reached",
    "additional actions required",
    "more actions required",
    "more actions are required",
    "need to select more",
    "select more actions",
    "cumulative gain insufficient",
    "cumulative gain",
    "target gap",
)

CONTRADICTORY_SUMMARY_PATTERNS_WHEN_REACHED = (
    "not reached",
    "not yet reached",
    "additional actions",
    "more actions",
    "need to select more",
    "select more actions",
    "cumulative gain",
    "target gap",
    "0.142",
)


def build_final_summary(
    *,
    score_global_initial: float,
    score_global_target: float,
    score_global_final_estimated: float,
    gain_total: float,
    effort_total: int,
    target_reached: bool,
    best_path: list[dict[str, Any]],
    auto_completed: bool = False,
) -> dict[str, str]:
    domain_count = len(best_path)

    optimization_logic = (
        "The final Best Path was reconstructed from validated candidate actions. "
        "The optimization uses weighted global gain, domain weights, effort transitions "
        "and the limiting-factor rule."
    )
    if auto_completed:
        optimization_logic += (
            " The LLM initial selection was insufficient or suboptimal; the backend optimizer "
            "selected the closest valid path to the target."
        )

    if domain_count == 0:
        selected_domains_reason = (
            f"The final path provides a total global gain of {gain_total}, "
            f"increasing the score from {score_global_initial} to {score_global_final_estimated}."
        )
    elif domain_count == 1:
        domain_id = str(best_path[0]["domainId"])
        selected_domains_reason = (
            f"The final path combines domain {domain_id} and provides a total global gain "
            f"of {gain_total}, increasing the score from {score_global_initial} to "
            f"{score_global_final_estimated}."
        )
    else:
        selected_domains_reason = (
            f"The final path combines {domain_count} domains and provides a total global gain "
            f"of {gain_total}, increasing the score from {score_global_initial} to "
            f"{score_global_final_estimated}."
        )

    effort_interpretation = (
        f"The validated path requires {effort_total} effort units. "
        "Each effort value comes from NDI effort_transitions."
    )

    if target_reached:
        final_rounded = round_score(score_global_final_estimated)
        target_rounded = round_score(score_global_target)
        if final_rounded == target_rounded:
            comparison = "equal to"
        else:
            comparison = "greater than"
        final_validation = (
            f"Target reached: {score_global_initial} + {gain_total} = "
            f"{score_global_final_estimated}, which is {comparison} the target score "
            f"{score_global_target}."
        )
    else:
        final_validation = (
            f"Target not reached: {score_global_initial} + {gain_total} = "
            f"{score_global_final_estimated}, which is below the target score "
            f"{score_global_target}."
        )

    return {
        "optimizationLogic": optimization_logic,
        "selectedDomainsReason": selected_domains_reason,
        "effortInterpretation": effort_interpretation,
        "finalValidation": final_validation,
    }


def build_summary_from_final_path(
    *,
    score_global_initial: float,
    target_score: float,
    gain_total: float,
    effort_total: int,
    score_global_final: float,
    target_reached: bool,
    best_path: list[dict[str, Any]],
    auto_completed: bool = False,
) -> dict[str, str]:
    return build_final_summary(
        score_global_initial=score_global_initial,
        score_global_target=target_score,
        score_global_final_estimated=score_global_final,
        gain_total=gain_total,
        effort_total=effort_total,
        target_reached=target_reached,
        best_path=best_path,
        auto_completed=auto_completed,
    )


def sanitize_warnings_for_target_reached(
    warnings: list[str],
    *,
    target_reached: bool,
    auto_completed: bool = False,
) -> list[str]:
    if auto_completed and target_reached:
        return [BACKEND_OPTIMIZER_SELECTED_WARNING]

    sanitized: list[str] = []
    for warning in warnings:
        lower_warning = warning.lower()
        if target_reached and any(
            pattern in lower_warning for pattern in CONTRADICTORY_WARNING_PATTERNS_WHEN_REACHED
        ):
            continue
        sanitized.append(warning)

    return sanitized


def validate_final_response_consistency(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    target_reached = bool(payload.get("targetReached"))
    summary = payload.get("summary")
    warnings = payload.get("warnings")

    if not isinstance(summary, dict):
        errors.append("summary must be an object in the final response.")
        return errors

    summary_text = " ".join(str(summary.get(field, "")) for field in SUMMARY_FIELDS).lower()
    final_validation = str(summary.get("finalValidation", "")).lower()

    if target_reached:
        if any(pattern in final_validation for pattern in CONTRADICTORY_SUMMARY_PATTERNS_WHEN_REACHED):
            errors.append("summary.finalValidation contradicts targetReached=true.")
        if any(pattern in summary_text for pattern in CONTRADICTORY_SUMMARY_PATTERNS_WHEN_REACHED):
            errors.append("summary contains text inconsistent with targetReached=true.")

    if isinstance(warnings, list) and target_reached:
        for warning in warnings:
            lower_warning = str(warning).lower()
            if any(pattern in lower_warning for pattern in CONTRADICTORY_WARNING_PATTERNS_WHEN_REACHED):
                errors.append("warnings contain text inconsistent with targetReached=true.")

    return errors


def finalize_best_path_response(
    payload: dict[str, Any],
    *,
    auto_completed: bool = False,
) -> dict[str, Any]:
    finalized = dict(payload)
    auto_completed = auto_completed or bool(finalized.pop("backendAutoCompleted", False))
    target_reached = bool(finalized.get("targetReached"))
    best_path = finalized.get("bestPath")
    if not isinstance(best_path, list):
        best_path = []

    should_rebuild_summary = True
    if should_rebuild_summary:
        finalized["summary"] = build_final_summary(
            score_global_initial=float(finalized["scoreGlobalInitial"]),
            score_global_target=float(finalized["scoreGlobalTarget"]),
            score_global_final_estimated=float(finalized["scoreGlobalFinalEstimated"]),
            gain_total=float(finalized["gainTotal"]),
            effort_total=int(finalized["effortTotal"]),
            target_reached=target_reached,
            best_path=best_path,
            auto_completed=auto_completed,
        )
    elif isinstance(finalized.get("summary"), dict):
        summary = finalized["summary"]
        finalized["summary"] = {
            field: str(summary.get(field, "")) for field in SUMMARY_FIELDS
        }

    raw_warnings = finalized.get("warnings")
    warnings = [str(item) for item in raw_warnings] if isinstance(raw_warnings, list) else []
    finalized["warnings"] = sanitize_warnings_for_target_reached(
        warnings,
        target_reached=target_reached,
        auto_completed=auto_completed,
    )

    consistency_errors = validate_final_response_consistency(finalized)
    if consistency_errors:
        finalized["summary"] = build_final_summary(
            score_global_initial=float(finalized["scoreGlobalInitial"]),
            score_global_target=float(finalized["scoreGlobalTarget"]),
            score_global_final_estimated=float(finalized["scoreGlobalFinalEstimated"]),
            gain_total=float(finalized["gainTotal"]),
            effort_total=int(finalized["effortTotal"]),
            target_reached=target_reached,
            best_path=best_path,
            auto_completed=auto_completed,
        )
        finalized["warnings"] = sanitize_warnings_for_target_reached(
            finalized["warnings"],
            target_reached=target_reached,
            auto_completed=auto_completed,
        )

    return finalized


def rebuild_best_path_from_selection(
    selected_action_ids: list[str] | None,
    actions_by_id: dict[str, dict[str, Any]] | None,
    *,
    score_global_initial: float,
    target_score: float,
    summary: dict[str, Any] | None = None,
    selection_reason: str = "",
    warnings: list[str] | None = None,
    candidate_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    selected_action_ids = selected_action_ids or []
    actions_by_id = actions_by_id or {}
    candidate_actions = candidate_actions or []
    best_path: list[dict[str, Any]] = []
    seen_domains: set[str] = set()
    gain_total = 0.0
    effort_total = 0

    for priority, action_id in enumerate(selected_action_ids, start=1):
        action = actions_by_id[action_id]
        domain_id = str(action["domainId"])
        if domain_id in seen_domains:
            raise ValueError(f"Duplicate domain selection is not allowed: {domain_id}")

        seen_domains.add(domain_id)
        gain_total += float(action["globalScoreGain"])
        effort_total += int(action["totalEffort"])
        best_path.append(
            {
                "priority": priority,
                "domainId": action["domainId"],
                "domainName": action["domainName"],
                "domainWeight": action["domainWeight"],
                "currentDomainScore": action["currentDomainScore"],
                "targetDomainScore": action["targetDomainScore"],
                "domainScoreGain": action["domainScoreGain"],
                "globalScoreGain": action["globalScoreGain"],
                "totalEffort": action["totalEffort"],
                "efficiencyRatio": action["efficiencyRatio"],
                "questionsToImprove": action["questionsToImprove"],
            }
        )

    gain_total = round_gain(gain_total)
    score_global_final = round_score(score_global_initial + gain_total)
    target_reached = score_global_final >= target_score
    over_gain = round_gain(max(score_global_final - target_score, 0.0))

    summary_payload = summary if isinstance(summary, dict) else {}
    warnings_payload = [str(item) for item in warnings] if isinstance(warnings, list) else []

    if candidate_actions and target_reached:
        overgain_warning = build_overgain_optimality_warning(
            selected_action_ids,
            actions_by_id,
            candidate_actions,
            target_gap=round_gain(target_score - score_global_initial),
            score_global_initial=score_global_initial,
            target_score=target_score,
        )
        if overgain_warning and overgain_warning not in warnings_payload:
            warnings_payload.append(overgain_warning)

    return {
        "success": True,
        "scoreGlobalInitial": round_score(score_global_initial),
        "scoreGlobalTarget": round_score(target_score),
        "scoreGlobalFinalEstimated": score_global_final,
        "gainTotal": gain_total,
        "effortTotal": effort_total,
        "overGain": over_gain,
        "targetReached": target_reached,
        "bestPath": best_path,
        "calculationValidation": {
            "formula": "scoreGlobalFinalEstimated = scoreGlobalInitial + sum(globalScoreGain)",
            "scoreGlobalInitial": round_score(score_global_initial),
            "scoreGlobalTarget": round_score(target_score),
            "totalGainFromBestPath": gain_total,
            "scoreGlobalFinalEstimated": score_global_final,
            "overGain": over_gain,
            "targetReached": target_reached,
        },
        "summary": {
            "optimizationLogic": summary_payload.get("optimizationLogic", selection_reason),
            "selectedDomainsReason": summary_payload.get("selectedDomainsReason", ""),
            "effortInterpretation": summary_payload.get("effortInterpretation", ""),
            "finalValidation": summary_payload.get("finalValidation", ""),
        },
        "warnings": warnings_payload,
    }
