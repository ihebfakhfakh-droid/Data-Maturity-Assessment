import logging
from copy import deepcopy
from typing import Any

from app.models.recommendation_models import NDIFramework
from app.services.candidate_action_builder import EXCESS_EFFORT_SELECTION_MESSAGE, find_optimal_best_path
from app.services.framework_map import compute_current_domain_score
from app.services.score_calculator import (
    build_expected_transitions,
    compute_expected_global_gain,
    compute_question_effort,
    compute_total_framework_weight,
    get_transition_explanations,
    round_gain,
    round_score,
)

logger = logging.getLogger(__name__)

SCORE_TOLERANCE = 0.02
GAIN_TOLERANCE = 0.01

INSUFFICIENT_SELECTION_MESSAGE = (
    "LLM selected valid actions but cumulativeGain is lower than targetGap."
)

INSUFFICIENT_SELECTION_AUTO_COMPLETE_DISABLED_MESSAGE = (
    "LLM selected valid actions but cumulativeGain is lower than targetGap. "
    "Backend optimizer found a possible path but AUTO_COMPLETE_BEST_PATH is disabled."
)

EXCESS_OVERGAIN_SELECTION_MESSAGE = (
    "LLM selected path reaches the target but exceeds it more than necessary. "
    "overGain is higher than the minimum possible overGain for the same effortTotal."
)

MISSING_SELECTION_MESSAGE = (
    "Invalid LLM response: the model returned a candidateAction object instead of a selection object."
)

CANDIDATE_ACTION_ROOT_FIELDS = (
    "actionId",
    "domainId",
    "domainName",
    "domainWeight",
    "currentDomainScore",
    "questionsToImprove",
    "transitions",
    "targetDomainScore",
    "globalScoreGain",
    "totalEffort",
    "efficiencyRatio",
)

SUMMARY_REQUIRED_FIELDS = (
    "optimizationLogic",
    "selectedDomainsReason",
    "effortInterpretation",
    "finalValidation",
)

LLM_SELECTION_DOMAIN_FIELDS = ("domainId", "targetDomainScore", "questionsToImprove")
LLM_SELECTION_QUESTION_FIELDS = ("questionCode", "targetScore")

STRUCTURAL_ERROR_MARKERS = (
    "does not exist in NDI framework",
    "does not belong to domainId",
    "must come from effort_transitions",
    "cannot be a decimal",
    "missing questionCode",
    "missing domainId",
)


class BestPathValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def _is_decimal_effort(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, float) and not value.is_integer():
        return True
    if isinstance(value, str):
        try:
            parsed = float(value)
            return not parsed.is_integer()
        except ValueError:
            return False
    return False


def _extract_llm_best_path(result: dict[str, Any]) -> list[dict[str, Any]]:
    best_path = result.get("bestPath")
    if isinstance(best_path, list):
        return best_path
    return []


def _validate_llm_selection_structure(
    result: dict[str, Any],
    *,
    framework: NDIFramework,
    current_scores: dict[str, int],
) -> list[str]:
    errors: list[str] = []
    best_path = _extract_llm_best_path(result)

    if "globalScoreGains" in result and "bestPath" not in result:
        errors.append(
            "Invalid LLM response: globalScoreGains without detailed bestPath is forbidden"
        )
        return errors

    if not best_path:
        errors.append("bestPath must not be empty")
        return errors

    for index, domain_item in enumerate(best_path):
        if not isinstance(domain_item, dict):
            errors.append(f"bestPath[{index}] must be an object")
            continue

        domain_id = domain_item.get("domainId")
        if not isinstance(domain_id, str) or not domain_id:
            errors.append(f"Invalid LLM response: missing domainId in bestPath[{index}].")
            continue

        domain = framework.get_domain(domain_id)
        if domain is None:
            errors.append(
                f"Invalid LLM response: domainId {domain_id} does not exist in NDI framework."
            )
            continue

        try:
            target_domain_score = int(domain_item["targetDomainScore"])
        except (KeyError, TypeError, ValueError):
            errors.append(
                f"Invalid LLM response: missing or invalid targetDomainScore for domainId {domain_id}."
            )
            continue

        current_domain_score = compute_current_domain_score(
            framework=framework,
            domain_id=domain_id,
            current_scores=current_scores,
        )
        if current_domain_score is None:
            errors.append(
                f"Invalid LLM response: domainId {domain_id} has no answered questions in currentScores."
            )
            continue

        if target_domain_score < current_domain_score:
            errors.append(
                f"Invalid LLM response: targetDomainScore ({target_domain_score}) < "
                f"currentDomainScore ({current_domain_score}) for domainId {domain_id}."
            )

        questions = domain_item.get("questionsToImprove")
        if not isinstance(questions, list) or not questions:
            errors.append(
                f"bestPath[{index}].questionsToImprove must be a non-empty list for domainId {domain_id}."
            )
            continue

        for q_index, question_item in enumerate(questions):
            if not isinstance(question_item, dict):
                errors.append(
                    f"bestPath[{index}].questionsToImprove[{q_index}] must be an object"
                )
                continue

            question_code = question_item.get("questionCode")
            if not isinstance(question_code, str) or not question_code:
                errors.append(
                    f"Invalid LLM response: missing questionCode in bestPath[{index}].questionsToImprove[{q_index}]."
                )
                continue

            question = framework.get_question(question_code)
            if question is None:
                errors.append(
                    f"Invalid LLM response: questionCode {question_code} does not exist in NDI framework."
                )
                continue

            if not question_code.startswith(f"{domain_id}."):
                errors.append(
                    f"Invalid LLM response: questionCode {question_code} does not belong to domainId {domain_id}."
                )

            if "effort" in question_item:
                declared_effort = question_item.get("effort")
                if _is_decimal_effort(declared_effort):
                    errors.append(
                        "Invalid LLM response: effort must come from effort_transitions and cannot be a decimal."
                    )

            try:
                target_score = int(question_item["targetScore"])
            except (KeyError, TypeError, ValueError):
                errors.append(
                    f"Invalid LLM response: missing or invalid targetScore for questionCode {question_code}."
                )
                continue

            if question_code in current_scores and target_score < current_scores[question_code]:
                errors.append(
                    f"Invalid LLM response: targetScore ({target_score}) < currentScore "
                    f"({current_scores[question_code]}) for questionCode {question_code}."
                )

    return errors


def _rebuild_question(
    question_item: dict[str, Any],
    *,
    domain_id: str,
    framework: NDIFramework,
    current_scores: dict[str, int],
) -> dict[str, Any] | None:
    question_code = question_item.get("questionCode")
    if not isinstance(question_code, str):
        return None

    question = framework.get_question(question_code)
    if question is None or not question_code.startswith(f"{domain_id}."):
        return None

    if question_code not in current_scores:
        return None

    current_score = int(current_scores[question_code])
    target_score = int(question_item["targetScore"])
    effort = compute_question_effort(
        framework=framework,
        question_id=question_code,
        current_score=current_score,
        target_score=target_score,
    )
    explanations = get_transition_explanations(
        framework=framework,
        question_id=question_code,
        current_score=current_score,
        target_score=target_score,
    )

    return {
        "questionCode": question_code,
        "questionText": question.text,
        "currentScore": current_score,
        "targetScore": target_score,
        "effort": effort,
        "explanation": " | ".join(explanations),
        "recommendation": str(question_item.get("recommendation", "")),
    }


def rebuild_best_path_from_llm_selection(
    result: dict[str, Any],
    *,
    framework: NDIFramework,
    current_scores: dict[str, int],
    score_global_initial: float,
    target_score: float,
) -> dict[str, Any]:
    rebuilt_best_path: list[dict[str, Any]] = []
    llm_best_path = _extract_llm_best_path(result)

    for priority, domain_item in enumerate(llm_best_path, start=1):
        if not isinstance(domain_item, dict):
            continue

        domain_id = domain_item.get("domainId")
        if not isinstance(domain_id, str):
            continue

        domain = framework.get_domain(domain_id)
        if domain is None:
            continue

        current_domain_score = compute_current_domain_score(
            framework=framework,
            domain_id=domain_id,
            current_scores=current_scores,
        )
        if current_domain_score is None:
            continue

        target_domain_score = int(domain_item["targetDomainScore"])
        questions_raw = domain_item.get("questionsToImprove", [])
        rebuilt_questions: list[dict[str, Any]] = []
        domain_effort = 0

        if isinstance(questions_raw, list):
            for question_item in questions_raw:
                if not isinstance(question_item, dict):
                    continue
                rebuilt_question = _rebuild_question(
                    question_item,
                    domain_id=domain_id,
                    framework=framework,
                    current_scores=current_scores,
                )
                if rebuilt_question is None:
                    continue
                rebuilt_questions.append(rebuilt_question)
                domain_effort += int(rebuilt_question["effort"])

        global_score_gain = compute_expected_global_gain(
            framework=framework,
            current_scores=current_scores,
            domain_id=domain_id,
            current_domain_score=current_domain_score,
            target_domain_score=target_domain_score,
        )
        domain_score_gain = target_domain_score - current_domain_score
        efficiency_ratio = (
            round_score(global_score_gain / domain_effort, 4) if domain_effort > 0 else 0.0
        )

        rebuilt_best_path.append(
            {
                "priority": int(domain_item.get("priority", priority)),
                "domainId": domain_id,
                "domainName": domain.domain_name,
                "domainWeight": domain.weight,
                "currentDomainScore": current_domain_score,
                "targetDomainScore": target_domain_score,
                "domainScoreGain": domain_score_gain,
                "globalScoreGain": global_score_gain,
                "totalEffort": domain_effort,
                "efficiencyRatio": efficiency_ratio,
                "questionsToImprove": rebuilt_questions,
            }
        )

    gain_total = round_score(sum(item["globalScoreGain"] for item in rebuilt_best_path))
    effort_total = sum(item["totalEffort"] for item in rebuilt_best_path)
    score_global_final = round_score(score_global_initial + gain_total)
    target_reached = score_global_final >= target_score

    professional = result.get("professionalAnalysis")
    if not isinstance(professional, dict):
        professional = {}

    warnings = result.get("warnings")
    if not isinstance(warnings, list):
        warnings = []

    return {
        "scoreGlobalInitial": round_score(score_global_initial),
        "scoreGlobalTarget": round_score(target_score),
        "scoreGlobalFinalEstimated": score_global_final,
        "gainTotal": gain_total,
        "effortTotal": effort_total,
        "targetReached": target_reached,
        "bestPath": rebuilt_best_path,
        "calculationValidation": {
            "formula": "scoreGlobalFinalEstimated = scoreGlobalInitial + sum(globalScoreGain)",
            "scoreGlobalInitial": round_score(score_global_initial),
            "totalGainFromBestPath": gain_total,
            "scoreGlobalFinalEstimated": score_global_final,
            "scoreGlobalTarget": round_score(target_score),
            "targetReached": target_reached,
        },
        "professionalAnalysis": professional,
        "warnings": warnings,
    }


def normalize_best_path_result(
    result: dict[str, Any],
    *,
    framework: NDIFramework,
    current_scores: dict[str, int],
    score_global_initial: float,
    target_score: float,
) -> tuple[dict[str, Any], list[str]]:
    structural_errors = _validate_llm_selection_structure(
        result=result,
        framework=framework,
        current_scores=current_scores,
    )
    if structural_errors:
        return deepcopy(result), structural_errors

    rebuilt = rebuild_best_path_from_llm_selection(
        result=result,
        framework=framework,
        current_scores=current_scores,
        score_global_initial=score_global_initial,
        target_score=target_score,
    )
    return rebuilt, []


def calculate_gain_total_from_best_path(best_path: list[dict[str, Any]]) -> float:
    return round_gain(sum(float(item.get("globalScoreGain", 0)) for item in best_path))


def calculate_effort_total_from_best_path(best_path: list[dict[str, Any]]) -> int:
    return sum(int(item.get("totalEffort", 0)) for item in best_path)


def calculate_final_score_from_gains(
    score_global_initial: float, best_path: list[dict[str, Any]]
) -> float:
    return round_score(score_global_initial + calculate_gain_total_from_best_path(best_path))


def _normalize_transition(transition: dict[str, Any]) -> dict[str, int | str]:
    if "fromScore" in transition or "toScore" in transition:
        raise ValueError("deprecated fromScore/toScore")
    return {
        "from": int(transition["from"]),
        "to": int(transition["to"]),
        "transitionKey": str(transition["transitionKey"]),
        "effort": int(transition["effort"]),
        "explanation": str(transition.get("explanation", "")),
    }


def _validate_summary_object(summary: Any) -> list[str]:
    errors: list[str] = []
    if isinstance(summary, str):
        errors.append("summary must be an object, not a string.")
        return errors
    if not isinstance(summary, dict):
        errors.append("summary must be an object.")
        return errors
    for field in SUMMARY_REQUIRED_FIELDS:
        if field not in summary:
            errors.append(f"summary.{field} is missing.")
        elif not isinstance(summary.get(field), str):
            errors.append(f"summary.{field} must be a string.")
    return errors


def validate_llm_best_path_response(
    result: dict[str, Any],
    target_score: float,
    *,
    framework: NDIFramework,
    current_scores: dict[str, int],
    score_global_initial: float,
) -> tuple[bool, list[str], float | None]:
    errors: list[str] = []
    total_weights = compute_total_framework_weight(framework)

    if "professionalAnalysis" in result:
        errors.append(
            "Invalid LLM response: professionalAnalysis is deprecated; use summary instead."
        )

    if "calculatedFinalScore" in result and "scoreGlobalFinalEstimated" not in result:
        errors.append(
            "Invalid LLM response: calculatedFinalScore is forbidden; use scoreGlobalFinalEstimated."
        )

    if "globalScoreGains" in result and "bestPath" not in result:
        errors.append(
            "Invalid LLM response: globalScoreGains without detailed bestPath is forbidden"
        )
        return False, errors, None

    required_fields = (
        "success",
        "scoreGlobalInitial",
        "scoreGlobalTarget",
        "scoreGlobalFinalEstimated",
        "gainTotal",
        "effortTotal",
        "targetReached",
        "bestPath",
        "calculationValidation",
        "summary",
    )
    for field in required_fields:
        if field not in result:
            errors.append(f"Invalid LLM response: missing required field '{field}'")

    if "summary" in result:
        errors.extend(_validate_summary_object(result.get("summary")))

    if "calculationValidation" in result and not isinstance(
        result.get("calculationValidation"), dict
    ):
        errors.append("Invalid LLM response: calculationValidation must be an object.")

    try:
        declared_initial = float(result.get("scoreGlobalInitial", score_global_initial))
        if abs(declared_initial - score_global_initial) > SCORE_TOLERANCE:
            errors.append(
                f"scoreGlobalInitial ({declared_initial}) does not match request "
                f"scoreGlobalActual ({score_global_initial})"
            )
    except (TypeError, ValueError):
        if "scoreGlobalInitial" in result:
            errors.append("scoreGlobalInitial is not a valid number")

    try:
        declared_target = float(result.get("scoreGlobalTarget", target_score))
        if abs(declared_target - target_score) > SCORE_TOLERANCE:
            errors.append(
                f"scoreGlobalTarget ({declared_target}) does not match request targetScore ({target_score})"
            )
    except (TypeError, ValueError):
        if "scoreGlobalTarget" in result:
            errors.append("scoreGlobalTarget is not a valid number")

    best_path = result.get("bestPath")
    if not isinstance(best_path, list) or not best_path:
        errors.append("bestPath must not be empty")
        log_validation(
            target_score=target_score,
            score_global_initial=score_global_initial,
            score_global_final_estimated=None,
            calculated_final_score=None,
            target_reached=result.get("targetReached"),
            attempt=None,
            is_valid=False,
            errors=errors,
        )
        return False, errors, None

    for index, domain_item in enumerate(best_path):
        if not isinstance(domain_item, dict):
            errors.append(f"bestPath[{index}] must be an object")
            continue

        domain_id = domain_item.get("domainId")
        if not isinstance(domain_id, str) or not domain_id:
            errors.append(f"Invalid LLM response: missing domainId in bestPath[{index}].")
            continue

        domain = framework.get_domain(domain_id)
        if domain is None:
            errors.append(
                f"Invalid LLM response: domainId {domain_id} does not exist in NDI framework."
            )
            continue

        declared_name = domain_item.get("domainName")
        if declared_name != domain.domain_name:
            errors.append(
                f"domainName for {domain_id} must match the JSON exactly and must not be translated. "
                f"Expected {domain.domain_name!r}, got {declared_name!r}."
            )

        try:
            declared_weight = float(domain_item.get("domainWeight", 0))
            if abs(declared_weight - domain.weight) > 0.01:
                errors.append(
                    f"Invalid LLM response: domainWeight for {domain_id} must be "
                    f"{domain.weight}, got {declared_weight}."
                )
        except (TypeError, ValueError):
            errors.append(f"Invalid LLM response: domainWeight for {domain_id} is not numeric.")

        expected_current_domain_score = compute_current_domain_score(
            framework=framework,
            domain_id=domain_id,
            current_scores=current_scores,
        )
        if expected_current_domain_score is None:
            errors.append(
                f"Invalid LLM response: domainId {domain_id} has no answered questions in currentScores."
            )
            continue

        try:
            declared_current_domain_score = int(domain_item["currentDomainScore"])
            target_domain_score = int(domain_item["targetDomainScore"])
            declared_gain = float(domain_item["globalScoreGain"])
        except (KeyError, TypeError, ValueError):
            errors.append(
                f"Invalid LLM response: invalid domain scores or globalScoreGain for {domain_id}."
            )
            continue

        for field in (
            "priority",
            "domainScoreGain",
            "totalEffort",
            "efficiencyRatio",
        ):
            if field not in domain_item:
                errors.append(
                    f"Invalid LLM response: bestPath[{index}] is missing required field '{field}'."
                )

        if declared_current_domain_score != expected_current_domain_score:
            errors.append(
                f"Invalid LLM response: currentDomainScore for {domain_id} must be "
                f"{expected_current_domain_score}, got {declared_current_domain_score}."
            )

        expected_gain = compute_expected_global_gain(
            framework=framework,
            current_scores=current_scores,
            domain_id=domain_id,
            current_domain_score=expected_current_domain_score,
            target_domain_score=target_domain_score,
            total_weights=total_weights,
        )
        if abs(declared_gain - expected_gain) > GAIN_TOLERANCE:
            errors.append(
                f"{domain_id} globalScoreGain is wrong. You returned {declared_gain}, but the correct value "
                f"is {expected_gain} because ({target_domain_score} - {expected_current_domain_score}) * "
                f"{domain.weight} / {total_weights} = {expected_gain}. It is forbidden to multiply by 10."
            )

        expected_domain_score_gain = target_domain_score - expected_current_domain_score
        try:
            declared_domain_score_gain = int(domain_item["domainScoreGain"])
            if declared_domain_score_gain != expected_domain_score_gain:
                errors.append(
                    f"Invalid LLM response: domainScoreGain for {domain_id} must be "
                    f"{expected_domain_score_gain}, got {declared_domain_score_gain}."
                )
        except (KeyError, TypeError, ValueError):
            pass

        questions = domain_item.get("questionsToImprove")
        if not isinstance(questions, list) or not questions:
            errors.append(
                f"bestPath[{index}].questionsToImprove must be a non-empty list for domainId {domain_id}."
            )
            continue

        domain_question_effort = 0
        for q_index, question_item in enumerate(questions):
            if not isinstance(question_item, dict):
                continue

            question_code = question_item.get("questionCode")
            if not isinstance(question_code, str) or not question_code:
                errors.append(
                    f"Invalid LLM response: missing questionCode in bestPath[{index}].questionsToImprove[{q_index}]."
                )
                continue

            question = framework.get_question(question_code)
            if question is None:
                errors.append(
                    f"Invalid LLM response: questionCode {question_code} does not exist in NDI framework."
                )
                continue

            if not question_code.startswith(f"{domain_id}."):
                errors.append(
                    f"Invalid LLM response: questionCode {question_code} does not belong to domainId {domain_id}."
                )

            declared_text = question_item.get("questionText")
            if declared_text != question.text:
                errors.append(
                    f"questionText for {question_code} must match the JSON exactly and must not be translated. "
                    f"Expected {question.text!r}, got {declared_text!r}."
                )

            if question_code not in current_scores:
                errors.append(
                    f"Invalid LLM response: questionCode {question_code} is not in currentScores."
                )
                continue

            current_score = int(current_scores[question_code])
            try:
                declared_current_score = int(question_item["currentScore"])
                if declared_current_score != current_score:
                    errors.append(
                        f"Invalid LLM response: currentScore for {question_code} must be "
                        f"{current_score}, got {declared_current_score}."
                    )
            except (KeyError, TypeError, ValueError):
                errors.append(
                    f"Invalid LLM response: missing or invalid currentScore for {question_code}."
                )

            try:
                question_target = int(question_item["targetScore"])
            except (KeyError, TypeError, ValueError):
                errors.append(
                    f"Invalid LLM response: invalid targetScore for {question_code}."
                )
                continue

            if question_item.get("effort") is not None and "transitions" not in question_item:
                errors.append(
                    f"Invalid LLM response: effort without transitions is forbidden for {question_code}; "
                    "use transitions and totalQuestionEffort."
                )

            transitions = question_item.get("transitions")
            if not isinstance(transitions, list) or not transitions:
                errors.append(
                    f"Invalid LLM response: transitions for {question_code} must be a non-empty list."
                )
                continue

            expected_transitions = build_expected_transitions(
                framework=framework,
                question_id=question_code,
                current_score=current_score,
                target_score=question_target,
            )
            declared_transitions = []
            transition_effort_sum = 0
            for transition_index, transition in enumerate(transitions):
                if not isinstance(transition, dict):
                    errors.append(
                        f"Invalid LLM response: transitions[{transition_index}] for {question_code} must be an object."
                    )
                    continue
                if "fromScore" in transition or "toScore" in transition:
                    errors.append(
                        f"transitions for {question_code} must use from/to/transitionKey, not fromScore/toScore."
                    )
                if "transitionKey" not in transition:
                    errors.append(
                        f"transitionKey is missing for {question_code} at transitions[{transition_index}]."
                    )
                try:
                    normalized = _normalize_transition(transition)
                except (KeyError, TypeError, ValueError):
                    errors.append(
                        f"Invalid LLM response: invalid transition for {question_code} at index {transition_index}."
                    )
                    continue
                if _is_decimal_effort(normalized["effort"]):
                    errors.append(
                        f"Invalid LLM response: transition effort for {question_code} cannot be a decimal."
                    )
                declared_transitions.append(normalized)
                transition_effort_sum += int(normalized["effort"])

            if expected_transitions and declared_transitions != expected_transitions:
                errors.append(
                    f"Invalid LLM response: transitions for {question_code} must match NDI effort_transitions."
                )

            try:
                declared_question_effort = int(question_item["totalQuestionEffort"])
                if declared_question_effort != transition_effort_sum:
                    errors.append(
                        f"Invalid LLM response: totalQuestionEffort for {question_code} must be "
                        f"{transition_effort_sum}, got {declared_question_effort}."
                    )
            except (KeyError, TypeError, ValueError):
                errors.append(
                    f"Invalid LLM response: missing or invalid totalQuestionEffort for {question_code}."
                )
                continue

            recommendation = question_item.get("recommendation")
            if not isinstance(recommendation, str) or not recommendation.strip():
                errors.append(
                    f"Invalid LLM response: recommendation for {question_code} must be a non-empty actionable string."
                )

            domain_question_effort += declared_question_effort

        try:
            declared_total_effort = int(domain_item["totalEffort"])
            if declared_total_effort != domain_question_effort:
                errors.append(
                    f"Invalid LLM response: totalEffort for {domain_id} must be "
                    f"{domain_question_effort}, got {declared_total_effort}."
                )
            expected_efficiency = (
                round_score(declared_gain / declared_total_effort, 4)
                if declared_total_effort > 0
                else 0.0
            )
            declared_efficiency = float(domain_item["efficiencyRatio"])
            if abs(declared_efficiency - expected_efficiency) > SCORE_TOLERANCE:
                errors.append(
                    f"Invalid LLM response: efficiencyRatio for {domain_id} must be "
                    f"{expected_efficiency}, got {declared_efficiency}."
                )
        except (KeyError, TypeError, ValueError):
            pass

    final_estimated: float | None = None
    try:
        final_estimated = float(result["scoreGlobalFinalEstimated"])
    except (KeyError, TypeError, ValueError):
        errors.append("scoreGlobalFinalEstimated is not a valid number")

    declared_gain_total: float | None = None
    try:
        declared_gain_total = float(result["gainTotal"])
    except (KeyError, TypeError, ValueError):
        errors.append("gainTotal is not a valid number")

    gain_total_from_path = calculate_gain_total_from_best_path(best_path)
    if declared_gain_total is not None and abs(declared_gain_total - gain_total_from_path) > GAIN_TOLERANCE:
        errors.append(
            f"gainTotal ({declared_gain_total}) does not match sum of globalScoreGain "
            f"in bestPath ({gain_total_from_path})"
        )

    calculated_final = calculate_final_score_from_gains(score_global_initial, best_path)

    try:
        declared_effort_total = int(result["effortTotal"])
        expected_effort_total = calculate_effort_total_from_best_path(best_path)
        if declared_effort_total != expected_effort_total:
            errors.append(
                f"effortTotal ({declared_effort_total}) does not match sum of totalEffort "
                f"in bestPath ({expected_effort_total})"
            )
    except (KeyError, TypeError, ValueError):
        if "effortTotal" in result:
            errors.append("effortTotal is not a valid integer")

    calculation_validation = result.get("calculationValidation")
    if isinstance(calculation_validation, dict):
        try:
            cv_gain = float(calculation_validation.get("totalGainFromBestPath"))
            if declared_gain_total is not None and abs(cv_gain - declared_gain_total) > GAIN_TOLERANCE:
                errors.append(
                    f"calculationValidation.totalGainFromBestPath ({cv_gain}) does not match "
                    f"gainTotal ({declared_gain_total})"
                )
            if abs(cv_gain - gain_total_from_path) > GAIN_TOLERANCE:
                errors.append(
                    f"calculationValidation.totalGainFromBestPath ({cv_gain}) does not match "
                    f"sum of globalScoreGain in bestPath ({gain_total_from_path})"
                )
        except (TypeError, ValueError):
            errors.append("calculationValidation.totalGainFromBestPath is not a valid number")

        try:
            cv_final = float(calculation_validation.get("scoreGlobalFinalEstimated"))
            if final_estimated is not None and abs(cv_final - final_estimated) > SCORE_TOLERANCE:
                errors.append(
                    f"calculationValidation.scoreGlobalFinalEstimated ({cv_final}) does not match "
                    f"scoreGlobalFinalEstimated ({final_estimated})"
                )
            if abs(cv_final - calculated_final) > SCORE_TOLERANCE:
                errors.append(
                    f"calculationValidation.scoreGlobalFinalEstimated ({cv_final}) does not match "
                    f"scoreGlobalInitial + gainTotal ({calculated_final})"
                )
        except (TypeError, ValueError):
            errors.append("calculationValidation.scoreGlobalFinalEstimated is not a valid number")

    if final_estimated is not None and abs(final_estimated - calculated_final) > SCORE_TOLERANCE:
        errors.append(
            f"scoreGlobalFinalEstimated ({final_estimated}) differs from "
            f"scoreGlobalInitial + gainTotal ({calculated_final})"
        )

    if final_estimated is not None and final_estimated < target_score:
        errors.append(
            f"scoreGlobalFinalEstimated ({final_estimated}) < targetScore ({target_score})"
        )

    if calculated_final < target_score:
        errors.append(
            f"calculatedFinalScore ({calculated_final}) < targetScore ({target_score})"
        )

    target_reached = result.get("targetReached")
    if target_reached is True and final_estimated is not None and final_estimated < target_score:
        errors.append("targetReached is true but scoreGlobalFinalEstimated is below targetScore")

    if target_reached is not True and final_estimated is not None and final_estimated >= target_score:
        errors.append(
            "targetReached must be true when scoreGlobalFinalEstimated >= scoreGlobalTarget"
        )

    warnings = result.get("warnings")
    if warnings is not None and not isinstance(warnings, list):
        errors.append("warnings must be a list when provided")

    log_validation(
        target_score=target_score,
        score_global_initial=score_global_initial,
        score_global_final_estimated=final_estimated,
        calculated_final_score=calculated_final,
        target_reached=target_reached,
        attempt=None,
        is_valid=not errors,
        errors=errors,
    )
    return not errors, errors, calculated_final


def _known_domain_ids(actions_by_id: dict[str, dict[str, Any]]) -> set[str]:
    return {str(action["domainId"]) for action in actions_by_id.values()}


def _looks_like_candidate_action_response(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    if "selectedActionIds" in result:
        return False
    return any(field in result for field in CANDIDATE_ACTION_ROOT_FIELDS)


def _coerce_allowed_action_ids(allowed_action_ids: list[str] | None, actions_by_id: dict[str, dict[str, Any]]) -> list[str]:
    if isinstance(allowed_action_ids, list):
        return [str(action_id) for action_id in allowed_action_ids if action_id]
    return list(actions_by_id.keys())


def _coerce_selected_action_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(action_id) for action_id in value if action_id is not None and str(action_id)]


def _invalid_action_id_error(action_id: str, actions_by_id: dict[str, dict[str, Any]]) -> str:
    domain_ids = _known_domain_ids(actions_by_id)
    if action_id in domain_ids:
        return (
            f"Invalid selectedActionIds: '{action_id}' is a domainId, not a valid actionId. "
            "Use exact actionIds from allowedActionIds."
        )
    return (
        f"Invalid selectedActionId: {action_id} does not exist in allowedActionIds. "
        "The LLM must copy exact actionIds from allowedActionIds."
    )


def validate_llm_selection_response(
    result: Any,
    target_score: float,
    *,
    actions_by_id: dict[str, dict[str, Any]],
    score_global_initial: float,
    max_possible_gain: float | None = None,
    target_reachable: bool | None = None,
    allowed_action_ids: list[str] | None = None,
    candidate_actions: list[dict[str, Any]] | None = None,
) -> tuple[bool, list[str], float | None]:
    errors: list[str] = []

    if not isinstance(result, dict):
        errors.append("Invalid LLM response: response must be a JSON object.")
        log_validation(
            target_score=target_score,
            score_global_initial=score_global_initial,
            score_global_final_estimated=None,
            calculated_final_score=None,
            target_reached=None,
            attempt=None,
            is_valid=False,
            errors=errors,
        )
        return False, errors, None

    allowed_ids = _coerce_allowed_action_ids(allowed_action_ids, actions_by_id)
    allowed_id_set = set(allowed_ids)

    target_gap = round_gain(target_score - score_global_initial)
    if max_possible_gain is None:
        best_gain_by_domain: dict[str, float] = {}
        for action in actions_by_id.values():
            domain_id = str(action["domainId"])
            gain = float(action["globalScoreGain"])
            best_gain_by_domain[domain_id] = max(best_gain_by_domain.get(domain_id, 0.0), gain)
        max_possible_gain = round_gain(sum(best_gain_by_domain.values()))
    if target_reachable is None:
        target_reachable = max_possible_gain >= target_gap

    for forbidden_field in (
        "bestPath",
        "gainTotal",
        "effortTotal",
        "scoreGlobalFinalEstimated",
        "calculationValidation",
        "professionalAnalysis",
        "cumulativeGain",
        "targetGap",
        "targetReached",
        "selectionSteps",
        "summary",
        *CANDIDATE_ACTION_ROOT_FIELDS,
    ):
        if forbidden_field in result:
            if forbidden_field in CANDIDATE_ACTION_ROOT_FIELDS:
                errors.append(MISSING_SELECTION_MESSAGE)
            else:
                errors.append(
                    f"Invalid LLM response: {forbidden_field} must not be returned by the LLM; "
                    "backend calculates and rebuilds the full Best Path from selectedActionIds."
                )

    if result.get("success") is not True:
        errors.append("success must be true.")

    selected_action_ids = _coerce_selected_action_ids(result.get("selectedActionIds"))
    if not selected_action_ids:
        if "selectedActionIds" not in result or _looks_like_candidate_action_response(result):
            if MISSING_SELECTION_MESSAGE not in errors:
                errors.append(MISSING_SELECTION_MESSAGE)
        else:
            errors.append("selectedActionIds must be a non-empty list.")
        log_validation(
            target_score=target_score,
            score_global_initial=score_global_initial,
            score_global_final_estimated=None,
            calculated_final_score=None,
            target_reached=None,
            attempt=None,
            is_valid=False,
            errors=errors,
        )
        return False, errors, None

    seen_domains: set[str] = set()
    selected_gain = 0.0
    selected_effort = 0

    for action_id in selected_action_ids:
        if not isinstance(action_id, str) or not action_id:
            errors.append("selectedActionIds must contain non-empty strings.")
            continue

        action = actions_by_id.get(action_id)
        if action is None:
            errors.append(_invalid_action_id_error(action_id, actions_by_id))
            continue

        if action_id not in allowed_id_set:
            errors.append(
                f"Invalid selectedActionId: {action_id} does not exist in allowedActionIds. "
                "The LLM must copy exact actionIds from allowedActionIds."
            )
            continue

        domain_id = str(action["domainId"])
        if domain_id in seen_domains:
            errors.append(
                f"Incompatible duplicate domain selection for {domain_id}. "
                "Select only one actionId per domainId."
            )
        seen_domains.add(domain_id)
        selected_gain += float(action["globalScoreGain"])
        selected_effort += int(action["totalEffort"])

    selected_gain = round_gain(selected_gain)
    calculated_final = round_score(score_global_initial + selected_gain)

    if selected_gain < target_gap:
        errors.append(INSUFFICIENT_SELECTION_MESSAGE)

    if calculated_final < target_score:
        errors.append(
            f"Selected actions only reach scoreGlobalFinalEstimated {calculated_final}, "
            f"which is below targetScore {target_score}. "
            f"Add more actionIds from allowedActionIds."
        )

    if selected_gain >= target_gap and candidate_actions:
        optimal_path = find_optimal_best_path(candidate_actions, target_gap=target_gap)
        if optimal_path is not None:
            minimum_effort = int(optimal_path["effortTotal"])
            minimum_over_gain = float(optimal_path["overGain"])
            selected_over_gain = round_gain(max(selected_gain - target_gap, 0.0))
            if selected_effort > minimum_effort:
                errors.append(EXCESS_EFFORT_SELECTION_MESSAGE)
                errors.append(
                    f"Current effortTotal = {selected_effort}. "
                    f"Minimum possible effortTotal = {minimum_effort}."
                )
            elif selected_over_gain > minimum_over_gain + GAIN_TOLERANCE:
                errors.append(EXCESS_OVERGAIN_SELECTION_MESSAGE)
                errors.append(
                    f"Current overGain = {selected_over_gain}. "
                    f"Minimum possible overGain = {minimum_over_gain}."
                )

    warnings = result.get("warnings")
    if warnings is not None and not isinstance(warnings, list):
        errors.append("warnings must be a list when provided.")

    log_validation(
        target_score=target_score,
        score_global_initial=score_global_initial,
        score_global_final_estimated=calculated_final,
        calculated_final_score=calculated_final,
        target_reached=selected_gain >= target_gap,
        attempt=None,
        is_valid=not errors,
        errors=errors,
    )
    return not errors, errors, calculated_final


def build_insufficient_selection_failure(
    *,
    target_score: float,
    score_global_initial: float,
    selected_gain: float,
    target_gap: float,
    last_llm_response: str = "",
    candidate_actions: list[dict[str, Any]] | None = None,
    auto_complete_enabled: bool = False,
) -> dict[str, Any]:
    score_global_final = round_score(score_global_initial + selected_gain)
    over_gain = round_gain(max(score_global_final - target_score, 0.0))
    message = INSUFFICIENT_SELECTION_MESSAGE
    if (
        not auto_complete_enabled
        and candidate_actions
        and find_optimal_best_path(candidate_actions, target_gap=target_gap) is not None
    ):
        message = INSUFFICIENT_SELECTION_AUTO_COMPLETE_DISABLED_MESSAGE

    return {
        "success": False,
        "message": message,
        "targetScore": round_score(target_score),
        "selectedGain": round_gain(selected_gain),
        "targetGap": round_gain(target_gap),
        "overGain": over_gain,
        "scoreGlobalFinalEstimated": score_global_final,
        "targetReached": False,
        "lastLLMResponse": last_llm_response,
    }


def validate_best_path_result(
    result: dict[str, Any],
    target_score: float,
    *,
    score_global_initial: float | None = None,
    require_non_empty_path: bool | None = None,
    framework: NDIFramework | None = None,
    current_scores: dict[str, int] | None = None,
) -> tuple[bool, list[str], float | None]:
    errors: list[str] = []

    best_path = result.get("bestPath")
    if not isinstance(best_path, list) or not best_path:
        errors.append("bestPath must not be empty")

    initial = score_global_initial
    if initial is None and "scoreGlobalInitial" in result:
        try:
            initial = float(result["scoreGlobalInitial"])
        except (TypeError, ValueError):
            errors.append("scoreGlobalInitial is not a valid number")

    final_estimated: float | None = None
    if "scoreGlobalFinalEstimated" in result:
        try:
            final_estimated = float(result["scoreGlobalFinalEstimated"])
        except (TypeError, ValueError):
            errors.append("scoreGlobalFinalEstimated is not a valid number")

    if final_estimated is not None and final_estimated < target_score:
        errors.append(
            f"scoreGlobalFinalEstimated ({final_estimated}) < targetScore ({target_score})"
        )

    target_reached = result.get("targetReached")
    if target_reached is True and final_estimated is not None and final_estimated < target_score:
        errors.append("targetReached is true but scoreGlobalFinalEstimated is below targetScore")

    needs_improvements = (
        require_non_empty_path
        if require_non_empty_path is not None
        else initial is not None and initial < target_score
    )
    if needs_improvements and (not isinstance(best_path, list) or not best_path):
        errors.append("bestPath must not be empty when target score is not yet reached")

    calculated_final: float | None = None
    if initial is not None and isinstance(best_path, list):
        calculated_final = calculate_final_score_from_gains(initial, best_path)
        if calculated_final < target_score:
            errors.append(
                f"calculatedFinalScore ({calculated_final}) < targetScore ({target_score})"
            )
        if final_estimated is not None and abs(calculated_final - final_estimated) > SCORE_TOLERANCE:
            errors.append(
                f"scoreGlobalFinalEstimated ({final_estimated}) differs from calculatedFinalScore ({calculated_final})"
            )

    log_validation(
        target_score=target_score,
        score_global_initial=initial,
        score_global_final_estimated=final_estimated,
        calculated_final_score=calculated_final,
        target_reached=target_reached,
        attempt=None,
        is_valid=not errors,
        errors=errors,
    )
    return not errors, errors, calculated_final


def log_validation(
    *,
    target_score: float,
    score_global_initial: float | None,
    score_global_final_estimated: float | None,
    calculated_final_score: float | None,
    target_reached: Any,
    attempt: int | None,
    is_valid: bool,
    errors: list[str] | None = None,
) -> None:
    attempt_label = attempt if attempt is not None else "-"
    logger.info(
        "Best path validation | attempt=%s | targetScore=%s | scoreGlobalInitial=%s | "
        "scoreGlobalFinalEstimated=%s | calculatedFinalScore=%s | targetReached=%s | valid=%s",
        attempt_label,
        target_score,
        score_global_initial,
        score_global_final_estimated,
        calculated_final_score,
        target_reached,
        is_valid,
    )
    if errors:
        logger.warning("Best path validation errors: %s", "; ".join(errors))
