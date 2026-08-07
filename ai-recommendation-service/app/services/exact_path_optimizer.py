"""Generic exact Best Path optimizer using dynamic programming."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.models.recommendation_models import FrameworkDomain, NDIFramework
from app.services.grounded_recommendation import enrich_question_with_grounded_recommendation
from app.services.score_calculator import (
    build_expected_transitions,
    compute_domain_score,
    get_domain_answered_scores,
    round_gain,
    round_score,
)

PRECISION_SCALE = Decimal("1000000")


class OptimizationInputError(ValueError):
    """Raised when assessment input cannot be optimized."""


class OptimizationValidationError(ValueError):
    """Raised when the optimized path fails post-selection validation."""


@dataclass(frozen=True)
class _DomainOption:
    domain_id: str
    domain_name: str
    domain_weight: Decimal
    current_domain_score: int
    target_domain_score: int
    weighted_gain: Decimal
    global_gain: Decimal
    total_effort: int
    questions_count: int
    efficiency_ratio: Decimal
    questions_to_improve: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class _Solution:
    effort: int
    over_gain_units: int
    question_count: int
    domain_count: int
    domain_ids: tuple[str, ...]
    weighted_gain_units: int
    options: tuple[_DomainOption, ...]


def _to_units(value: Decimal) -> int:
    return int((value * PRECISION_SCALE).quantize(Decimal("1")))


def _from_units(value: int) -> Decimal:
    return Decimal(value) / PRECISION_SCALE


def _decimal_weight(weight: float) -> Decimal:
    return Decimal(str(weight))


def _validate_framework_weights(framework: NDIFramework) -> Decimal:
    if not framework.domains:
        raise OptimizationInputError("The framework contains no domains.")

    total_weight = Decimal("0")
    for domain in framework.domains:
        weight = _decimal_weight(domain.weight)
        if weight <= 0:
            raise OptimizationInputError(
                f"Invalid domain weight for domain '{domain.domain_id}': weight must be positive."
            )
        total_weight += weight
    if total_weight <= 0:
        raise OptimizationInputError("Total domain weight must be greater than zero.")
    return total_weight


def compute_exact_weighted_numerator(
    framework: NDIFramework,
    current_scores: dict[str, int],
) -> tuple[Decimal, Decimal]:
    """Return (weighted numerator, total weight) without rounding."""
    total_weight = _validate_framework_weights(framework)
    weighted_numerator = Decimal("0")

    for domain in framework.domains:
        answered = get_domain_answered_scores(domain, current_scores)
        if not answered:
            continue
        domain_score = compute_domain_score(answered)
        weighted_numerator += Decimal(domain_score) * _decimal_weight(domain.weight)

    return weighted_numerator, total_weight


def compute_exact_global_score(
    framework: NDIFramework,
    current_scores: dict[str, int],
) -> Decimal:
    weighted_numerator, total_weight = compute_exact_weighted_numerator(
        framework,
        current_scores,
    )
    if total_weight <= 0:
        return Decimal("0")
    return weighted_numerator / total_weight


def _domain_max_score(domain: FrameworkDomain) -> int:
    if not domain.questions:
        return 0
    max_scores: list[int] = []
    for question in domain.questions:
        highest = 0
        for key in question.effort_transitions:
            if "_to_" not in key:
                continue
            highest = max(highest, int(key.split("_to_", 1)[1]))
        max_scores.append(highest or question.maxScore)
    return max(max_scores)


def _build_question_improvements(
    framework: NDIFramework,
    domain: FrameworkDomain,
    answered_scores: dict[str, int],
    target_domain_score: int,
) -> list[dict[str, Any]]:
    improvements: list[dict[str, Any]] = []
    for question in domain.questions:
        if question.id not in answered_scores:
            continue
        current_score = answered_scores[question.id]
        if current_score >= target_domain_score:
            continue

        transitions = build_expected_transitions(
            framework=framework,
            question_id=question.id,
            current_score=current_score,
            target_score=target_domain_score,
        )
        expected_steps = target_domain_score - current_score
        if len(transitions) < expected_steps:
            raise OptimizationInputError(
                f"Missing transition effort in knowledge base for question "
                f"'{question.id}' ({current_score} -> {target_domain_score})."
            )

        total_question_effort = sum(int(item["effort"]) for item in transitions)
        improvements.append(
            enrich_question_with_grounded_recommendation(
                {
                    "questionCode": question.id,
                    "questionText": question.text,
                    "currentScore": current_score,
                    "targetScore": target_domain_score,
                    "totalQuestionEffort": total_question_effort,
                    "transitions": transitions,
                }
            )
        )
    return improvements


def _build_domain_options(
    framework: NDIFramework,
    current_scores: dict[str, int],
    total_weight: Decimal,
) -> dict[str, list[_DomainOption]]:
    options_by_domain: dict[str, list[_DomainOption]] = {}

    for domain in framework.domains:
        answered = get_domain_answered_scores(domain, current_scores)
        if not answered:
            continue

        current_domain_score = compute_domain_score(answered)
        domain_weight = _decimal_weight(domain.weight)
        max_target = _domain_max_score(domain)
        domain_options: list[_DomainOption] = []

        for target_domain_score in range(current_domain_score, max_target + 1):
            if target_domain_score == current_domain_score:
                domain_options.append(
                    _DomainOption(
                        domain_id=domain.domain_id,
                        domain_name=domain.domain_name,
                        domain_weight=domain_weight,
                        current_domain_score=current_domain_score,
                        target_domain_score=current_domain_score,
                        weighted_gain=Decimal("0"),
                        global_gain=Decimal("0"),
                        total_effort=0,
                        questions_count=0,
                        efficiency_ratio=Decimal("0"),
                        questions_to_improve=[],
                    )
                )
                continue

            questions = _build_question_improvements(
                framework,
                domain,
                answered,
                target_domain_score,
            )
            if not questions:
                continue

            total_effort = sum(int(item["totalQuestionEffort"]) for item in questions)
            weighted_gain = Decimal(target_domain_score - current_domain_score) * domain_weight
            global_gain = weighted_gain / total_weight if total_weight > 0 else Decimal("0")
            efficiency_ratio = (
                global_gain / Decimal(total_effort) if total_effort > 0 else Decimal("0")
            )
            domain_options.append(
                _DomainOption(
                    domain_id=domain.domain_id,
                    domain_name=domain.domain_name,
                    domain_weight=domain_weight,
                    current_domain_score=current_domain_score,
                    target_domain_score=target_domain_score,
                    weighted_gain=weighted_gain,
                    global_gain=global_gain,
                    total_effort=total_effort,
                    questions_count=len(questions),
                    efficiency_ratio=efficiency_ratio,
                    questions_to_improve=questions,
                )
            )

        if domain_options:
            options_by_domain[domain.domain_id] = domain_options

    if not options_by_domain:
        raise OptimizationInputError("No domain with answered questions is available for optimization.")

    return options_by_domain


def _solution_key(solution: _Solution) -> tuple[Any, ...]:
    return (
        solution.effort,
        solution.over_gain_units,
        solution.question_count,
        solution.domain_count,
        solution.domain_ids,
    )


def _better_solution(candidate: _Solution, current: _Solution | None) -> bool:
    if current is None:
        return True
    return _solution_key(candidate) < _solution_key(current)


def _merge_solution(
    previous: _Solution,
    option: _DomainOption,
    *,
    target_weighted_units: int,
) -> _Solution:
    weighted_gain_units = previous.weighted_gain_units + _to_units(option.weighted_gain)
    effort = previous.effort + option.total_effort
    question_count = previous.question_count + option.questions_count
    domain_count = previous.domain_count + (1 if option.target_domain_score > option.current_domain_score else 0)
    domain_ids = previous.domain_ids + (
        (option.domain_id,) if option.target_domain_score > option.current_domain_score else ()
    )
    options = previous.options + ((option,) if option.target_domain_score > option.current_domain_score else ())
    over_gain_units = max(weighted_gain_units - target_weighted_units, 0)
    return _Solution(
        effort=effort,
        over_gain_units=over_gain_units,
        question_count=question_count,
        domain_count=domain_count,
        domain_ids=domain_ids,
        weighted_gain_units=weighted_gain_units,
        options=options,
    )


def _run_dynamic_programming(
    options_by_domain: dict[str, list[_DomainOption]],
    *,
    required_gain_units: int,
    target_weighted_units: int,
) -> _Solution | None:
    empty_solution = _Solution(
        effort=0,
        over_gain_units=0,
        question_count=0,
        domain_count=0,
        domain_ids=(),
        weighted_gain_units=0,
        options=(),
    )
    states: dict[int, _Solution] = {0: empty_solution}

    for domain_id in sorted(options_by_domain.keys()):
        domain_options = options_by_domain[domain_id]
        next_states: dict[int, _Solution] = {}

        for gain_units, state in states.items():
            for option in domain_options:
                merged = _merge_solution(state, option, target_weighted_units=target_weighted_units)
                new_gain_units = merged.weighted_gain_units
                existing = next_states.get(new_gain_units)
                if _better_solution(merged, existing):
                    next_states[new_gain_units] = merged

        states = next_states

    best: _Solution | None = None
    for gain_units, state in states.items():
        if gain_units < required_gain_units:
            continue
        if _better_solution(state, best):
            best = state
    return best


def _simulate_maximum_path(
    options_by_domain: dict[str, list[_DomainOption]],
) -> _Solution:
    options: list[_DomainOption] = []
    for domain_id in sorted(options_by_domain.keys()):
        domain_options = options_by_domain[domain_id]
        selected = max(
            domain_options,
            key=lambda item: (item.target_domain_score, -item.total_effort, item.domain_id),
        )
        if selected.target_domain_score > selected.current_domain_score:
            options.append(selected)

    effort = sum(option.total_effort for option in options)
    question_count = sum(option.questions_count for option in options)
    weighted_gain_units = sum(_to_units(option.weighted_gain) for option in options)
    domain_ids = tuple(option.domain_id for option in options)
    return _Solution(
        effort=effort,
        over_gain_units=weighted_gain_units,
        question_count=question_count,
        domain_count=len(options),
        domain_ids=domain_ids,
        weighted_gain_units=weighted_gain_units,
        options=tuple(options),
    )


def _build_best_path_items(solution: _Solution) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for option in solution.options:
        items.append(
            {
                "domainId": option.domain_id,
                "domainName": option.domain_name,
                "domainWeight": float(option.domain_weight),
                "currentDomainScore": option.current_domain_score,
                "targetDomainScore": option.target_domain_score,
                "domainScoreGain": option.target_domain_score - option.current_domain_score,
                "globalScoreGain": float(option.global_gain),
                "totalEffort": option.total_effort,
                "efficiencyRatio": float(option.efficiency_ratio),
                "questionsToImprove": option.questions_to_improve,
            }
        )

    items.sort(
        key=lambda item: (
            -float(item["efficiencyRatio"]),
            -float(item["globalScoreGain"]),
            str(item["domainId"]),
        ),
    )
    for priority, item in enumerate(items, start=1):
        item["priority"] = priority
    return items


def _validate_selected_path(
    *,
    framework: NDIFramework,
    current_scores: dict[str, int],
    initial_weighted: Decimal,
    total_weight: Decimal,
    target_score: Decimal,
    best_path: list[dict[str, Any]],
    effort_total: int,
    final_global_score: Decimal,
) -> None:
    if final_global_score + Decimal("1e-12") < target_score and best_path:
        raise OptimizationValidationError(
            "Selected path does not reach the target global score."
        )

    seen_domains: set[str] = set()
    recomputed_effort = 0
    recomputed_weighted_gain = Decimal("0")

    for domain_item in best_path:
        domain_id = str(domain_item["domainId"])
        if domain_id in seen_domains:
            raise OptimizationValidationError(f"Duplicate domain in best path: {domain_id}")
        seen_domains.add(domain_id)

        domain = framework.get_domain(domain_id)
        if domain is None:
            raise OptimizationValidationError(f"Unknown domain in best path: {domain_id}")

        weight = _decimal_weight(float(domain_item["domainWeight"]))
        if weight != _decimal_weight(domain.weight):
            raise OptimizationValidationError(
                f"Domain weight mismatch for '{domain_id}'."
            )

        answered = get_domain_answered_scores(domain, current_scores)
        current_domain_score = compute_domain_score(answered)
        target_domain_score = int(domain_item["targetDomainScore"])
        if int(domain_item["currentDomainScore"]) != current_domain_score:
            raise OptimizationValidationError(
                f"Current domain score mismatch for '{domain_id}'."
            )

        questions = domain_item.get("questionsToImprove", [])
        if not isinstance(questions, list):
            raise OptimizationValidationError(f"Invalid questions list for '{domain_id}'.")

        expected_questions = _build_question_improvements(
            framework,
            domain,
            answered,
            target_domain_score,
        )
        expected_codes = {item["questionCode"] for item in expected_questions}
        actual_codes = {str(item["questionCode"]) for item in questions}
        if expected_codes != actual_codes:
            raise OptimizationValidationError(
                f"Question selection mismatch for domain '{domain_id}'."
            )

        domain_effort = 0
        for question in questions:
            transitions = question.get("transitions", [])
            domain_effort += sum(int(item["effort"]) for item in transitions)

        if domain_effort != int(domain_item["totalEffort"]):
            raise OptimizationValidationError(
                f"Effort mismatch for domain '{domain_id}'."
            )
        recomputed_effort += domain_effort
        recomputed_weighted_gain += Decimal(target_domain_score - current_domain_score) * weight

    if recomputed_effort != effort_total:
        raise OptimizationValidationError("Total effort mismatch after validation.")

    expected_final = (initial_weighted + recomputed_weighted_gain) / total_weight
    if abs(expected_final - final_global_score) > Decimal("1e-9"):
        raise OptimizationValidationError("Final global score mismatch after validation.")


def optimize_best_path(
    framework: NDIFramework,
    current_scores: dict[str, int],
    target_score: float,
) -> dict[str, Any]:
    """Compute the optimal Best Path for any assessment using exact dynamic programming."""
    if not current_scores:
        raise OptimizationInputError("currentScores cannot be empty.")

    total_weight = _validate_framework_weights(framework)
    initial_weighted, _ = compute_exact_weighted_numerator(framework, current_scores)
    initial_global_score = initial_weighted / total_weight
    target_decimal = Decimal(str(target_score))
    target_weighted = target_decimal * total_weight
    required_gain = target_weighted - initial_weighted
    required_gain_units = max(_to_units(required_gain), 0)
    target_weighted_units = _to_units(target_weighted)

    options_by_domain = _build_domain_options(framework, current_scores, total_weight)

    if required_gain_units == 0:
        solution = _Solution(
            effort=0,
            over_gain_units=0,
            question_count=0,
            domain_count=0,
            domain_ids=(),
            weighted_gain_units=0,
            options=(),
        )
        target_reached = True
        warnings: list[str] = []
    else:
        solution = _run_dynamic_programming(
            options_by_domain,
            required_gain_units=required_gain_units,
            target_weighted_units=target_weighted_units,
        )
        if solution is None:
            solution = _simulate_maximum_path(options_by_domain)
            target_reached = False
            warnings = [
                "Target score is not reachable with the available domain improvements. "
                "Returning the maximum achievable score."
            ]
        else:
            target_reached = True
            warnings = []

    final_weighted = initial_weighted + _from_units(solution.weighted_gain_units)
    final_global_score = final_weighted / total_weight
    gain_total = final_global_score - initial_global_score
    over_gain = max(final_global_score - target_decimal, Decimal("0"))
    best_path = _build_best_path_items(solution)

    _validate_selected_path(
        framework=framework,
        current_scores=current_scores,
        initial_weighted=initial_weighted,
        total_weight=total_weight,
        target_score=target_decimal,
        best_path=best_path,
        effort_total=solution.effort,
        final_global_score=final_global_score,
    ) if target_reached else None

    return {
        "success": target_reached,
        "scoreGlobalInitial": float(initial_global_score),
        "scoreGlobalTarget": float(target_decimal),
        "scoreGlobalFinalEstimated": float(final_global_score),
        "gainTotal": float(gain_total),
        "overGain": float(over_gain),
        "effortTotal": solution.effort,
        "targetReached": target_reached,
        "bestPath": best_path,
        "warnings": warnings,
        "optimizationValidation": {
            "algorithm": "dynamic_programming",
            "objective": "minimum_total_effort",
            "totalWeight": float(total_weight),
            "targetReached": target_reached,
            "optimalityVerified": target_reached,
            "roundingUsedDuringOptimization": False,
        },
        "calculationValidation": {
            "formula": "scoreGlobalFinalEstimated = (initialWeightedNumerator + weightedGain) / totalWeight",
            "scoreGlobalInitial": round_score(float(initial_global_score)),
            "scoreGlobalTarget": round_score(float(target_decimal)),
            "totalGainFromBestPath": round_gain(float(gain_total)),
            "scoreGlobalFinalEstimated": round_score(float(final_global_score)),
            "overGain": round_gain(float(over_gain)),
            "targetReached": target_reached,
        },
    }
