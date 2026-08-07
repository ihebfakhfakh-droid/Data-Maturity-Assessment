import itertools
from typing import Any

from app.models.recommendation_models import (
    DomainImprovementOption,
    FrameworkDomain,
    NDIFramework,
)
from app.services.score_calculator import (
    build_domain_scores_map,
    compute_domain_score,
    compute_global_score,
    compute_global_score_from_domain_scores,
    compute_question_effort,
    get_domain_answered_scores,
    round_score,
)


def _questions_to_improve(
    domain: FrameworkDomain,
    framework: NDIFramework,
    answered_scores: dict[str, int],
    target_domain_score: int,
) -> list[dict[str, Any]]:
    if target_domain_score <= compute_domain_score(answered_scores):
        return []

    improvements: list[dict[str, Any]] = []
    for question in domain.questions:
        if question.questionCode not in answered_scores:
            continue
        current_score = answered_scores[question.questionCode]
        if current_score >= target_domain_score:
            continue
        improvements.append(
            {
                "questionCode": question.questionCode,
                "questionText": question.questionText,
                "currentScore": current_score,
                "targetScore": target_domain_score,
                "effort": compute_question_effort(
                    framework,
                    question.id,
                    current_score,
                    target_domain_score,
                ),
            }
        )
    return improvements


def _global_gain(
    old_domain_score: int,
    new_domain_score: int,
    domain_weight: float,
    total_weight: float,
) -> float:
    if total_weight <= 0:
        return 0.0
    return round_score((new_domain_score - old_domain_score) * domain_weight / total_weight)


def generate_domain_options(
    framework: NDIFramework,
    current_scores: dict[str, int],
) -> dict[str, list[DomainImprovementOption]]:
    active_domain_scores = build_domain_scores_map(framework, current_scores)
    total_weight = sum(weight for _, weight in active_domain_scores.values())
    options_by_domain: dict[str, list[DomainImprovementOption]] = {}

    for domain in framework.domains:
        answered = get_domain_answered_scores(domain, current_scores)
        if not answered:
            continue

        current_domain_score = compute_domain_score(answered)
        domain_options: list[DomainImprovementOption] = [
            DomainImprovementOption(
                domainId=domain.domainId,
                domainName=domain.domainName,
                domainWeight=domain.domainWeight,
                currentDomainScore=current_domain_score,
                targetDomainScore=current_domain_score,
                totalEffort=0,
                globalScoreGain=0.0,
                questionsToImprove=[],
            )
        ]

        max_target = max(question.maxScore for question in domain.questions)
        for target in range(current_domain_score + 1, max_target + 1):
            improvements = _questions_to_improve(
                domain, framework, answered, target
            )
            if not improvements:
                continue
            total_effort = sum(item["effort"] for item in improvements)
            domain_options.append(
                DomainImprovementOption(
                    domainId=domain.domainId,
                    domainName=domain.domainName,
                    domainWeight=domain.domainWeight,
                    currentDomainScore=current_domain_score,
                    targetDomainScore=target,
                    totalEffort=total_effort,
                    globalScoreGain=_global_gain(
                        current_domain_score,
                        target,
                        domain.domainWeight,
                        total_weight,
                    ),
                    questionsToImprove=improvements,
                )
            )

        options_by_domain[domain.domainId] = domain_options

    return options_by_domain


def _final_global_score(
    initial_domain_scores: dict[str, tuple[int, float]],
    selected_options: list[DomainImprovementOption],
) -> float:
    updated_scores = dict(initial_domain_scores)
    for option in selected_options:
        if option.targetDomainScore > option.currentDomainScore:
            updated_scores[option.domainId] = (
                option.targetDomainScore,
                option.domainWeight,
            )
    return compute_global_score_from_domain_scores(updated_scores)


def find_best_path(
    framework: NDIFramework,
    current_scores: dict[str, int],
    target_score: float,
) -> dict[str, Any]:
    initial_global = compute_global_score(framework, current_scores)
    if initial_global >= target_score:
        return {
            "scoreGlobalInitial": initial_global,
            "scoreGlobalTarget": round_score(target_score),
            "scoreGlobalFinalEstimated": initial_global,
            "gainTotal": 0.0,
            "effortTotal": 0,
            "bestPath": [],
        }

    options_by_domain = generate_domain_options(framework, current_scores)
    if not options_by_domain:
        return {
            "scoreGlobalInitial": initial_global,
            "scoreGlobalTarget": round_score(target_score),
            "scoreGlobalFinalEstimated": initial_global,
            "gainTotal": 0.0,
            "effortTotal": 0,
            "bestPath": [],
        }

    initial_domain_scores = build_domain_scores_map(framework, current_scores)
    domain_ids = sorted(options_by_domain.keys())
    option_lists = [options_by_domain[domain_id] for domain_id in domain_ids]

    best_combo: list[DomainImprovementOption] | None = None
    best_metrics: tuple[int, float, int] | None = None
    best_final_score = initial_global

    for combo in itertools.product(*option_lists):
        combo_list = list(combo)
        final_score = _final_global_score(initial_domain_scores, combo_list)
        if final_score < target_score:
            continue

        effort_total = sum(option.totalEffort for option in combo_list)
        num_actions = sum(
            len(option.questionsToImprove) for option in combo_list
        )
        metrics = (effort_total, -final_score, num_actions)

        if best_metrics is None or metrics < best_metrics:
            best_metrics = metrics
            best_combo = combo_list
            best_final_score = final_score

    if best_combo is None:
        return {
            "scoreGlobalInitial": initial_global,
            "scoreGlobalTarget": round_score(target_score),
            "scoreGlobalFinalEstimated": initial_global,
            "gainTotal": 0.0,
            "effortTotal": 0,
            "bestPath": [],
        }

    best_path: list[dict[str, Any]] = []
    effort_total = 0
    for option in best_combo:
        if option.targetDomainScore <= option.currentDomainScore:
            continue
        efficiency = (
            option.globalScoreGain / option.totalEffort
            if option.totalEffort > 0
            else 0.0
        )
        effort_total += option.totalEffort
        best_path.append(
            {
                "domainId": option.domainId,
                "domainName": option.domainName,
                "domainWeight": option.domainWeight,
                "currentDomainScore": option.currentDomainScore,
                "targetDomainScore": option.targetDomainScore,
                "globalScoreGain": option.globalScoreGain,
                "totalEffort": option.totalEffort,
                "efficiencyRatio": round(efficiency, 5),
                "questionsToImprove": option.questionsToImprove,
            }
        )

    return {
        "scoreGlobalInitial": initial_global,
        "scoreGlobalTarget": round_score(target_score),
        "scoreGlobalFinalEstimated": best_final_score,
        "gainTotal": round_score(best_final_score - initial_global),
        "effortTotal": effort_total,
        "bestPath": best_path,
    }
