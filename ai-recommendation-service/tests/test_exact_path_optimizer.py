"""Synthetic tests for the generic exact path optimizer."""

from __future__ import annotations

import itertools
from decimal import Decimal

import pytest

from app.models.recommendation_models import NDIFramework
from app.services.exact_path_optimizer import (
    OptimizationInputError,
    compute_exact_global_score,
    optimize_best_path,
)
from app.services.optimizer import generate_domain_options


def _effort_transitions(*efforts: int) -> dict[str, dict[str, object]]:
    return {
        f"{index}_to_{index + 1}": {
            "effort": effort,
            "explanation": f"Step {index} to {index + 1}",
        }
        for index, effort in enumerate(efforts)
    }


def _question(question_id: str, text: str, efforts: dict[str, dict[str, object]] | None = None):
    return {
        "id": question_id,
        "text": text,
        "effort_transitions": efforts or _effort_transitions(2, 2, 2, 2, 2),
    }


def _domain(domain_id: str, name: str, weight: float, questions: list[dict]):
    return {
        "domain_id": domain_id,
        "domain_name": name,
        "weight": weight,
        "questions": questions,
    }


def build_framework(
    *,
    domains: list[dict],
    effort_scale: dict[str, str] | None = None,
) -> NDIFramework:
    payload = {
        "framework": "SYNTHETIC",
        "total_domains": len(domains),
        "effort_scale": effort_scale
        or {
            "1": "Simple",
            "3": "Moderate",
            "5": "Complex",
        },
        "domains": domains,
    }
    return NDIFramework.model_validate(payload)


@pytest.fixture
def two_domain_framework() -> NDIFramework:
    return build_framework(
        domains=[
            _domain(
                "ALPHA",
                "Alpha Domain",
                30.0,
                [_question("ALPHA.Q1", "Alpha question 1"), _question("ALPHA.Q2", "Alpha question 2")],
            ),
            _domain(
                "BETA",
                "Beta Domain",
                70.5,
                [_question("BETA.Q1", "Beta question 1")],
            ),
        ]
    )


def test_domain_score_is_minimum_of_questions(two_domain_framework):
    scores = {"ALPHA.Q1": 3, "ALPHA.Q2": 2, "BETA.Q1": 4}
    result = optimize_best_path(two_domain_framework, scores, target_score=3.5)
    alpha_item = next(item for item in result["bestPath"] if item["domainId"] == "ALPHA")
    assert alpha_item["currentDomainScore"] == 2


def test_total_weight_is_sum_of_domain_weights(two_domain_framework):
    scores = {"ALPHA.Q1": 2, "ALPHA.Q2": 2, "BETA.Q1": 2}
    result = optimize_best_path(two_domain_framework, scores, target_score=2.5)
    assert result["optimizationValidation"]["totalWeight"] == pytest.approx(100.5)


def test_no_hardcoded_denominator_100(two_domain_framework):
    scores = {"ALPHA.Q1": 2, "ALPHA.Q2": 2, "BETA.Q1": 2}
    exact = compute_exact_global_score(two_domain_framework, scores)
    assert exact == Decimal("2")


def test_single_transition_effort():
    framework = build_framework(
        domains=[
            _domain(
                "ONLY",
                "Only Domain",
                50.0,
                [_question("ONLY.Q1", "Only question", _effort_transitions(7, 3, 4, 5, 6))],
            )
        ]
    )
    scores = {"ONLY.Q1": 1}
    result = optimize_best_path(framework, scores, target_score=2.0)
    question = result["bestPath"][0]["questionsToImprove"][0]
    assert question["totalQuestionEffort"] == 3
    assert question["transitions"][0]["transitionKey"] == "1_to_2"


def test_multi_transition_effort_is_summed():
    framework = build_framework(
        domains=[
            _domain(
                "ONLY",
                "Only Domain",
                40.0,
                [_question("ONLY.Q1", "Only question", _effort_transitions(2, 3, 4, 5, 6))],
            )
        ]
    )
    scores = {"ONLY.Q1": 1}
    result = optimize_best_path(framework, scores, target_score=3.0)
    question = result["bestPath"][0]["questionsToImprove"][0]
    assert question["targetScore"] == 3
    assert question["totalQuestionEffort"] == 7
    assert len(question["transitions"]) == 2


def test_all_questions_below_target_are_selected():
    framework = build_framework(
        domains=[
            _domain(
                "ALPHA",
                "Alpha Domain",
                100.0,
                [
                    _question("ALPHA.Q1", "Alpha question 1"),
                    _question("ALPHA.Q2", "Alpha question 2"),
                ],
            )
        ]
    )
    scores = {"ALPHA.Q1": 1, "ALPHA.Q2": 2}
    result = optimize_best_path(framework, scores, target_score=2.5)
    alpha_item = result["bestPath"][0]
    codes = {item["questionCode"] for item in alpha_item["questionsToImprove"]}
    assert codes == {"ALPHA.Q1", "ALPHA.Q2"}


def test_final_score_uses_unrounded_internal_math(two_domain_framework):
    scores = {"ALPHA.Q1": 2, "ALPHA.Q2": 2, "BETA.Q1": 2}
    result = optimize_best_path(two_domain_framework, scores, target_score=2.2)
    exact_initial = float(compute_exact_global_score(two_domain_framework, scores))
    assert result["scoreGlobalInitial"] == pytest.approx(exact_initial)


def test_target_already_reached_returns_empty_path(two_domain_framework):
    scores = {"ALPHA.Q1": 4, "ALPHA.Q2": 4, "BETA.Q1": 4}
    result = optimize_best_path(two_domain_framework, scores, target_score=3.0)
    assert result["bestPath"] == []
    assert result["effortTotal"] == 0
    assert result["targetReached"] is True


def test_unreachable_target_returns_maximum_achievable_score():
    framework = build_framework(
        domains=[
            _domain(
                "A",
                "A",
                50.0,
                [_question("A.Q1", "A1", _effort_transitions(2, 2))],
            ),
            _domain(
                "B",
                "B",
                50.0,
                [_question("B.Q1", "B1", _effort_transitions(2, 2))],
            ),
        ]
    )
    scores = {"A.Q1": 1, "B.Q1": 1}
    result = optimize_best_path(framework, scores, target_score=4.0)
    assert result["targetReached"] is False
    assert result["bestPath"]
    assert result["warnings"]


def test_local_best_ratio_is_not_enough_for_global_optimum():
    framework = build_framework(
        domains=[
            _domain(
                "HIGH_RATIO",
                "High Ratio",
                50.0,
                [_question("HIGH_RATIO.Q1", "High ratio", _effort_transitions(1, 20, 20, 20, 20))],
            ),
            _domain(
                "LOW_RATIO",
                "Low Ratio",
                50.0,
                [_question("LOW_RATIO.Q1", "Low ratio", _effort_transitions(5, 5, 5, 5, 5))],
            ),
        ]
    )
    scores = {"HIGH_RATIO.Q1": 1, "LOW_RATIO.Q1": 1}
    result = optimize_best_path(framework, scores, target_score=2.2)
    selected_ids = {item["domainId"] for item in result["bestPath"]}
    assert "LOW_RATIO" in selected_ids


def test_tie_break_is_reproducible(two_domain_framework):
    scores = {"ALPHA.Q1": 2, "ALPHA.Q2": 2, "BETA.Q1": 2}
    first = optimize_best_path(two_domain_framework, scores, target_score=2.6)
    second = optimize_best_path(two_domain_framework, scores, target_score=2.6)
    assert first["bestPath"] == second["bestPath"]
    assert first["effortTotal"] == second["effortTotal"]


def test_missing_transition_raises_validation_error():
    framework = build_framework(
        domains=[
            _domain(
                "BROKEN",
                "Broken",
                100.0,
                [
                    _question(
                        "BROKEN.Q1",
                        "Broken",
                        {
                            "0_to_1": {"effort": 2, "explanation": "0 to 1"},
                            "2_to_3": {"effort": 2, "explanation": "2 to 3"},
                        },
                    )
                ],
            )
        ]
    )
    scores = {"BROKEN.Q1": 1}
    with pytest.raises(OptimizationInputError, match="Missing transition effort"):
        optimize_best_path(framework, scores, target_score=3.0)


def test_invalid_weight_is_rejected():
    framework = build_framework(
        domains=[_domain("BAD", "Bad", 0.0, [_question("BAD.Q1", "Bad question")])]
    )
    with pytest.raises(OptimizationInputError, match="weight must be positive"):
        optimize_best_path(framework, {"BAD.Q1": 2}, target_score=3.0)


def test_empty_scores_are_rejected(two_domain_framework):
    with pytest.raises(OptimizationInputError, match="currentScores cannot be empty"):
        optimize_best_path(two_domain_framework, {}, target_score=3.0)


def test_brute_force_matches_dp_for_small_framework():
    framework = build_framework(
        domains=[
            _domain("D1", "D1", 25.0, [_question("D1.Q1", "D1Q1")]),
            _domain("D2", "D2", 25.0, [_question("D2.Q1", "D2Q1")]),
            _domain("D3", "D3", 50.5, [_question("D3.Q1", "D3Q1")]),
        ]
    )
    scores = {"D1.Q1": 2, "D2.Q1": 2, "D3.Q1": 2}
    target_score = 2.7
    dp_result = optimize_best_path(framework, scores, target_score=target_score)

    options = generate_domain_options(framework, scores)
    domain_ids = sorted(options.keys())
    best_effort = None
    for combo in itertools.product(*(options[domain_id] for domain_id in domain_ids)):
        final = sum(
            (
                Decimal(option.currentDomainScore) * Decimal(str(option.domainWeight))
                for option in combo
            ),
            Decimal("0"),
        )
        final += sum(
            Decimal(option.targetDomainScore - option.currentDomainScore)
            * Decimal(str(option.domainWeight))
            for option in combo
            if option.targetDomainScore > option.currentDomainScore
        )
        total_weight = Decimal("100.5")
        final_score = final / total_weight
        if final_score + Decimal("1e-12") < Decimal(str(target_score)):
            continue
        effort = sum(option.totalEffort for option in combo)
        if best_effort is None or effort < best_effort:
            best_effort = effort

    assert dp_result["effortTotal"] == best_effort


def test_priority_follows_efficiency_ratio_descending(two_domain_framework):
    scores = {"ALPHA.Q1": 1, "ALPHA.Q2": 1, "BETA.Q1": 1}
    result = optimize_best_path(two_domain_framework, scores, target_score=3.0)
    ratios = [item["efficiencyRatio"] for item in result["bestPath"]]
    assert ratios == sorted(ratios, reverse=True)
