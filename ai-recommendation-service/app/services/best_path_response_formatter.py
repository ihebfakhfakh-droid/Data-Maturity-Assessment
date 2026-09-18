from typing import Any

from app.models.recommendation_models import (
    BestPathResponse,
    BestPathStatus,
    BestPathTableRow,
    DetailedActionDomain,
    MathematicalValidation,
    OptimizationSummary,
    OptimizationValidation,
    QuestionToImprove,
    ScoreSummary,
    ScoreTransition,
)
from app.services.score_calculator import round_gain, round_score

MATHEMATICAL_VALIDATION_FORMULA = (
    "scoreGlobalFinalEstimated = scoreGlobalInitial + gainTotal"
)

SUCCESS_STATUS_MESSAGE = "Target score reached successfully."
FAILURE_STATUS_MESSAGE = "Target score not reached. LLM selection is insufficient."
INSUFFICIENT_STATUS_MESSAGE = (
    "LLM selection is insufficient. cumulativeGain is lower than targetGap."
)
AUTO_COMPLETE_DISABLED_WARNING = (
    "AUTO_COMPLETE_BEST_PATH is disabled. Backend did not add actions automatically."
)


def sort_best_path_for_display(best_path: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort domains by efficiency ratio (descending) for display priority only."""
    if not best_path:
        return []

    sorted_path = sorted(
        best_path,
        key=lambda item: (
            -float(item.get("efficiencyRatio", 0.0)),
            -float(item.get("globalScoreGain", 0.0)),
            str(item.get("domainId", "")),
        ),
    )

    display_path: list[dict[str, Any]] = []
    for priority, item in enumerate(sorted_path, start=1):
        display_item = dict(item)
        display_item["priority"] = priority
        display_path.append(display_item)
    return display_path


def _count_questions(best_path: list[dict[str, Any]]) -> int:
    return sum(
        len(item.get("questionsToImprove", []))
        for item in best_path
        if isinstance(item.get("questionsToImprove"), list)
    )


def _build_domain_objective(domain_name: str, current_domain_score: int, target_domain_score: int) -> str:
    return (
        f"Improve {domain_name} from score {current_domain_score} "
        f"to {target_domain_score}."
    )


def _normalize_transitions(transitions: list[dict[str, Any]] | None) -> list[ScoreTransition]:
    normalized: list[ScoreTransition] = []
    if not isinstance(transitions, list):
        return normalized
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        normalized.append(
            ScoreTransition(
                **{
                    "from": int(transition.get("from", transition.get("from_level", 0))),
                    "to": int(transition.get("to", 0)),
                    "transitionKey": str(transition.get("transitionKey", "")),
                    "effort": int(transition.get("effort", 0)),
                    "explanation": str(transition.get("explanation", "")),
                }
            )
        )
    return normalized


def _build_best_path_table(best_path: list[dict[str, Any]]) -> list[BestPathTableRow]:
    rows: list[BestPathTableRow] = []
    for item in best_path:
        rows.append(
            BestPathTableRow(
                priority=int(item.get("priority", len(rows) + 1)),
                domainId=str(item.get("domainId", "")),
                domainName=str(item.get("domainName", "")),
                domainWeight=float(item.get("domainWeight", 0.0)),
                currentDomainScore=int(item.get("currentDomainScore", 0)),
                targetDomainScore=int(item.get("targetDomainScore", 0)),
                globalScoreGain=float(item.get("globalScoreGain", 0.0)),
                totalEffort=int(item.get("totalEffort", 0)),
                efficiencyRatio=float(item.get("efficiencyRatio", 0.0)),
            )
        )
    return rows


def _build_detailed_actions(best_path: list[dict[str, Any]]) -> list[DetailedActionDomain]:
    detailed: list[DetailedActionDomain] = []
    for item in best_path:
        questions_payload = item.get("questionsToImprove")
        questions: list[QuestionToImprove] = []
        if isinstance(questions_payload, list):
            for question in questions_payload:
                if not isinstance(question, dict):
                    continue
                questions.append(
                    QuestionToImprove(
                        questionCode=str(question.get("questionCode", "")),
                        questionId=str(question.get("questionId") or question.get("questionCode", "")),
                        questionText=str(question.get("questionText", "")),
                        currentScore=int(question.get("currentScore", 0)),
                        targetScore=int(question.get("targetScore", 0)),
                        totalQuestionEffort=int(question.get("totalQuestionEffort", 0)),
                        transitions=_normalize_transitions(question.get("transitions")),
                        groundedRecommendation=str(question.get("groundedRecommendation", "")),
                        recommendationSource=str(
                            question.get("recommendationSource", "knowledge_base")
                        ),
                        recommendation=str(
                            question.get("groundedRecommendation")
                            or question.get("recommendation", "")
                        ),
                    )
                )

        domain_name = str(item.get("domainName", ""))
        current_domain_score = int(item.get("currentDomainScore", 0))
        target_domain_score = int(item.get("targetDomainScore", 0))
        detailed.append(
            DetailedActionDomain(
                priority=int(item.get("priority", len(detailed) + 1)),
                domainId=str(item.get("domainId", "")),
                domainName=domain_name,
                domainObjective=_build_domain_objective(
                    domain_name,
                    current_domain_score,
                    target_domain_score,
                ),
                questionsToImprove=questions,
            )
        )
    return detailed


def build_mathematical_validation_calculation(
    *,
    score_global_initial: float,
    gain_total: float,
    score_global_final: float,
    target_score: float,
    target_reached: bool,
    over_gain: float,
) -> str:
    initial = round_score(score_global_initial)
    gain = round_gain(gain_total)
    final_score = round_score(score_global_final)
    target = round_score(target_score)

    if target_reached and final_score == target and over_gain <= 0.01:
        return f"{initial} + {gain} = {final_score}, equal to target {target}"
    if target_reached:
        return f"{initial} + {gain} = {final_score} >= target {target}"
    return f"{initial} + {gain} = {final_score} < target {target}"


def _build_success_optimization_summary(
    best_path: list[dict[str, Any]],
) -> OptimizationSummary:
    return OptimizationSummary(
        strategy=(
            "Exact dynamic programming optimizer selecting at most one improvement "
            "option per domain with minimum total effort."
        ),
        selectedDomainsCount=len(best_path),
        selectedQuestionsCount=_count_questions(best_path),
        whyThisPath=(
            "The path minimizes total effort while reaching the target global score, "
            "then minimizes over-target gain, question count and domain count."
        ),
        effortExplanation=(
            "The effort total is the sum of all validated transition efforts "
            "from the knowledge base for the selected actions."
        ),
    )


def _build_failure_optimization_summary(
    best_path: list[dict[str, Any]],
    *,
    auto_complete_disabled: bool,
    insufficient_selection: bool,
) -> OptimizationSummary:
    if insufficient_selection and auto_complete_disabled:
        strategy = "LLM selected candidate actions, but the cumulative gain was insufficient."
        why_this_path = "The selected actions do not cover the required target gap."
        effort_explanation = (
            "Backend validation rejected the selection because AUTO_COMPLETE_BEST_PATH "
            "is disabled."
        )
    else:
        strategy = "LLM selected candidate actions, but the final validation failed."
        why_this_path = "The selected actions do not satisfy the Best Path validation rules."
        effort_explanation = (
            "Effort values come from validated NDI transitions for the parsed selection."
        )

    return OptimizationSummary(
        strategy=strategy,
        selectedDomainsCount=len(best_path),
        selectedQuestionsCount=_count_questions(best_path),
        whyThisPath=why_this_path,
        effortExplanation=effort_explanation,
    )


def _build_status_message(
    *,
    success: bool,
    target_reached: bool,
    insufficient_selection: bool = False,
    auto_complete_disabled: bool = False,
) -> str:
    if success and target_reached:
        return SUCCESS_STATUS_MESSAGE
    if not success and insufficient_selection and auto_complete_disabled:
        return INSUFFICIENT_STATUS_MESSAGE
    return FAILURE_STATUS_MESSAGE


def _extract_best_path(result: dict[str, Any]) -> list[dict[str, Any]]:
    best_path = result.get("bestPath")
    return best_path if isinstance(best_path, list) else []


def _extract_warnings(result: dict[str, Any]) -> list[str]:
    warnings = result.get("warnings")
    return [str(item) for item in warnings] if isinstance(warnings, list) else []


def _extract_optimization_validation(result: dict[str, Any]) -> OptimizationValidation | None:
    payload = result.get("optimizationValidation")
    if not isinstance(payload, dict):
        return None
    try:
        return OptimizationValidation(
            algorithm=str(payload.get("algorithm", "dynamic_programming")),
            objective=str(payload.get("objective", "minimum_total_effort")),
            totalWeight=float(payload.get("totalWeight", 0.0)),
            targetReached=bool(payload.get("targetReached")),
            optimalityVerified=bool(payload.get("optimalityVerified")),
            roundingUsedDuringOptimization=bool(
                payload.get("roundingUsedDuringOptimization", False)
            ),
        )
    except (TypeError, ValueError):
        return None


def _extract_failure_meta(result: dict[str, Any]) -> dict[str, Any]:
    failure_meta = result.get("failureMeta")
    return failure_meta if isinstance(failure_meta, dict) else {}


def format_best_path_response(
    result: dict[str, Any],
    *,
    auto_completed: bool = False,
) -> BestPathResponse:
    """Transform an already validated backend result into the public JSON structure."""
    success = bool(result.get("success", False))
    best_path = _extract_best_path(result)
    failure_meta = _extract_failure_meta(result)

    score_global_initial = float(result.get("scoreGlobalInitial", 0.0))
    score_global_target = float(result.get("scoreGlobalTarget", 0.0))
    gain_total = float(result.get("gainTotal", 0.0))
    score_global_final = float(result.get("scoreGlobalFinalEstimated", 0.0))
    over_gain = float(result.get("overGain", 0.0))
    effort_total = int(result.get("effortTotal", 0))
    target_reached = bool(result.get("targetReached", False))
    target_gap = round_gain(score_global_target - score_global_initial)

    insufficient_selection = bool(failure_meta.get("insufficient_selection", False))
    auto_complete_disabled = bool(failure_meta.get("auto_complete_disabled", False))
    auto_completed = auto_completed or bool(result.get("backendAutoCompleted", False))

    warnings_list = _extract_warnings(result)
    if (
        not success
        and insufficient_selection
        and auto_complete_disabled
        and AUTO_COMPLETE_DISABLED_WARNING not in warnings_list
    ):
        warnings_list.append(AUTO_COMPLETE_DISABLED_WARNING)

    optimization_summary = (
        _build_success_optimization_summary(best_path)
        if success
        else _build_failure_optimization_summary(
            best_path,
            auto_complete_disabled=auto_complete_disabled,
            insufficient_selection=insufficient_selection,
        )
    )
    optimization_validation = _extract_optimization_validation(result)

    display_best_path = sort_best_path_for_display(best_path) if success else []

    return BestPathResponse(
        success=success,
        status=BestPathStatus(
            targetReached=target_reached,
            message=_build_status_message(
                success=success,
                target_reached=target_reached,
                insufficient_selection=insufficient_selection,
                auto_complete_disabled=auto_complete_disabled,
            ),
        ),
        scoreSummary=ScoreSummary(
            scoreGlobalInitial=round_score(score_global_initial),
            scoreGlobalTarget=round_score(score_global_target),
            targetGap=target_gap,
            gainTotal=round_gain(gain_total),
            scoreGlobalFinalEstimated=round_score(score_global_final),
            overGain=round_gain(over_gain),
            effortTotal=effort_total,
        ),
        optimizationSummary=optimization_summary,
        optimizationValidation=optimization_validation,
        bestPathTable=_build_best_path_table(display_best_path) if success else [],
        detailedActions=_build_detailed_actions(display_best_path) if success else [],
        mathematicalValidation=MathematicalValidation(
            formula=MATHEMATICAL_VALIDATION_FORMULA,
            calculation=build_mathematical_validation_calculation(
                score_global_initial=score_global_initial,
                gain_total=gain_total,
                score_global_final=score_global_final,
                target_score=score_global_target,
                target_reached=target_reached,
                over_gain=over_gain,
            ),
            targetReached=target_reached,
        ),
        warnings=warnings_list,
    )


# Backward-compatible aliases used by tests.
format_success_best_path_response = format_best_path_response


def format_failure_best_path_response(
    result: dict[str, Any],
) -> BestPathResponse:
    return format_best_path_response(result)
