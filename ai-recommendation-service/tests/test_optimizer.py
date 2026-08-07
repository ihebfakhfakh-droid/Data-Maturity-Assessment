import json
from pathlib import Path

import pytest

from app.models.recommendation_models import NDIFramework
from app.services.optimizer import find_best_path, generate_domain_options
from app.services.score_calculator import (
    compute_domain_score,
    compute_global_score,
    compute_question_effort,
    get_domain_answered_scores,
)


def _effort_transitions(
    e01: int = 2,
    e12: int = 3,
    e23: int = 4,
    e34: int = 5,
    e45: int = 6,
) -> dict[str, dict[str, object]]:
    efforts = [e01, e12, e23, e34, e45]
    return {
        f"{i}_to_{i + 1}": {"effort": efforts[i], "explanation": f"Transition {i} to {i + 1}"}
        for i in range(5)
    }


def _question(question_id: str, text: str, efforts: dict[str, dict[str, object]] | None = None):
    return {
        "id": question_id,
        "text": text,
        "effort_transitions": efforts or _effort_transitions(),
    }


@pytest.fixture
def mini_framework() -> NDIFramework:
    raw = {
        "framework": "NDI-TEST",
        "total_domains": 5,
        "effort_scale": {
            "1": "Simple (< 1 mois)",
            "3": "Modéré (1 à 3 mois)",
            "5": "Complexe (> 6 mois)",
        },
        "domains": [
            {
                "domain_id": "DG",
                "domain_name": "Data Governance",
                "weight": 20.0,
                "questions": [
                    _question("DG.MQ.1", "Gouvernance formalisee ?"),
                    _question("DG.MQ.2", "Politiques DM ?"),
                    _question("DG.MQ.3", "Organisation DM ?"),
                ],
            },
            {
                "domain_id": "DQ",
                "domain_name": "Data Quality",
                "weight": 20.0,
                "questions": [
                    _question("DQ.MQ.1", "Plan DQ ?"),
                    _question("DQ.MQ.2", "Pratiques DQ ?"),
                ],
            },
            {
                "domain_id": "MCM",
                "domain_name": "Metadata",
                "weight": 20.0,
                "questions": [_question("MCM.MQ.1", "Plan metadata ?")],
            },
            {
                "domain_id": "DO",
                "domain_name": "Data Operations",
                "weight": 20.0,
                "questions": [_question("DO.MQ.1", "Plan operations ?")],
            },
            {
                "domain_id": "DAM",
                "domain_name": "Data Architecture",
                "weight": 20.0,
                "questions": [_question("DAM.MQ.1", "Plan architecture ?")],
            },
        ],
    }
    return NDIFramework.model_validate(raw)


def test_domain_score_is_minimum(mini_framework):
    domain = mini_framework.domains[0]
    answered = {"DG.MQ.1": 3, "DG.MQ.2": 2, "DG.MQ.3": 2}
    assert compute_domain_score(answered) == 2
    assert compute_domain_score(get_domain_answered_scores(domain, answered)) == 2


def test_global_weighted_score(mini_framework):
    current_scores = {
        "DG.MQ.1": 3,
        "DG.MQ.2": 2,
        "DG.MQ.3": 2,
        "DQ.MQ.1": 2,
        "DQ.MQ.2": 3,
        "MCM.MQ.1": 3,
        "DO.MQ.1": 3,
        "DAM.MQ.1": 2,
    }
    assert compute_global_score(mini_framework, current_scores) == 2.4


def test_all_blocking_questions_are_selected(mini_framework):
    current_scores = {"DG.MQ.1": 2, "DG.MQ.2": 2, "DG.MQ.3": 3}
    options = generate_domain_options(mini_framework, current_scores)
    target_three = next(
        opt for opt in options["DG"] if opt.targetDomainScore == 3
    )
    codes = {q["questionCode"] for q in target_three.questionsToImprove}
    assert codes == {"DG.MQ.1", "DG.MQ.2"}


def test_non_blocking_question_not_recommended_alone(mini_framework):
    current_scores = {"DG.MQ.1": 2, "DG.MQ.2": 3}
    options = generate_domain_options(mini_framework, current_scores)
    target_three = next(
        opt for opt in options["DG"] if opt.targetDomainScore == 3
    )
    assert len(target_three.questionsToImprove) == 1
    assert target_three.questionsToImprove[0]["questionCode"] == "DG.MQ.1"


def test_multi_level_effort_is_summed(mini_framework):
    # 2 -> 4 = effort(2->3) + effort(3->4) = 4 + 5 = 9
    assert compute_question_effort(mini_framework, "DG.MQ.1", 2, 4) == 9


def test_best_path_reaches_target_score(mini_framework):
    current_scores = {
        "DG.MQ.1": 3,
        "DG.MQ.2": 2,
        "DQ.MQ.1": 2,
        "DQ.MQ.2": 3,
        "MCM.MQ.1": 3,
        "DO.MQ.1": 3,
        "DAM.MQ.1": 2,
    }
    result = find_best_path(mini_framework, current_scores, target_score=3.0)
    assert result["scoreGlobalFinalEstimated"] >= 3.0


def test_best_path_minimizes_effort(mini_framework):
    current_scores = {
        "DG.MQ.1": 2,
        "DG.MQ.2": 2,
        "DQ.MQ.1": 2,
        "DQ.MQ.2": 2,
        "MCM.MQ.1": 2,
        "DO.MQ.1": 2,
        "DAM.MQ.1": 2,
    }
    result = find_best_path(mini_framework, current_scores, target_score=2.5)
    brute = _brute_force_best_effort(mini_framework, current_scores, 2.5)
    assert result["effortTotal"] == brute["effort"]


def _brute_force_best_effort(framework, current_scores, target):
    import itertools

    from app.services.optimizer import _final_global_score
    from app.services.score_calculator import build_domain_scores_map

    options = generate_domain_options(framework, current_scores)
    domain_ids = sorted(options.keys())
    best = None
    for combo in itertools.product(*(options[d] for d in domain_ids)):
        result = _final_global_score(
            build_domain_scores_map(framework, current_scores),
            list(combo),
        )
        if result < target:
            continue
        effort = sum(c.totalEffort for c in combo)
        if best is None or effort < best:
            best = effort
    return {"effort": best}


def test_framework_file_loads():
    framework_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "data"
        / "ndi_framework.json"
    )
    raw = json.loads(framework_path.read_text(encoding="utf-8"))
    framework = NDIFramework.model_validate(raw)
    assert framework.framework == "NDI"
    assert framework.total_domains == 14
    assert len(framework.domains) == 14
    weight_sum = round(sum(domain.weight for domain in framework.domains), 2)
    assert weight_sum == 100.01
    for domain in framework.domains:
        for question in domain.questions:
            for key in ("0_to_1", "1_to_2", "2_to_3", "3_to_4", "4_to_5"):
                transition = question.effort_transitions[key]
                assert transition.effort in {1, 3, 5}
