import pytest

from app.services.best_path_validator import (
    calculate_final_score_from_gains,
    validate_best_path_result,
)


def _valid_result(target: float = 3.48, initial: float = 2.48) -> dict:
    return {
        "success": True,
        "scoreGlobalInitial": initial,
        "scoreGlobalTarget": target,
        "scoreGlobalFinalEstimated": 3.49,
        "gainTotal": 1.01,
        "effortTotal": 10,
        "targetReached": True,
        "bestPath": [
            {
                "priority": 1,
                "domainId": "DQ",
                "domainName": "Data Quality",
                "domainWeight": 11.93,
                "currentDomainScore": 2,
                "targetDomainScore": 3,
                "domainScoreGain": 1,
                "globalScoreGain": 0.62,
                "totalEffort": 6,
                "efficiencyRatio": 0.1033,
                "questionsToImprove": [
                    {
                        "questionCode": "DQ.MQ.1",
                        "questionText": "Plan DQ ?",
                        "currentScore": 2,
                        "targetScore": 3,
                        "totalQuestionEffort": 6,
                        "transitions": [
                            {
                                "from": 2,
                                "to": 3,
                                "transitionKey": "2_to_3",
                                "effort": 6,
                                "explanation": "Bloquant",
                            }
                        ],
                        "recommendation": "Améliorer DQ",
                    }
                ],
            },
            {
                "priority": 2,
                "domainId": "DG",
                "domainName": "Data Governance",
                "domainWeight": 11.75,
                "currentDomainScore": 2,
                "targetDomainScore": 3,
                "domainScoreGain": 1,
                "globalScoreGain": 0.39,
                "totalEffort": 4,
                "efficiencyRatio": 0.0975,
                "questionsToImprove": [
                    {
                        "questionCode": "DG.MQ.2",
                        "questionText": "Politiques DM ?",
                        "currentScore": 2,
                        "targetScore": 3,
                        "totalQuestionEffort": 4,
                        "transitions": [
                            {
                                "from": 2,
                                "to": 3,
                                "transitionKey": "2_to_3",
                                "effort": 4,
                                "explanation": "Bloquant",
                            }
                        ],
                        "recommendation": "Améliorer DG",
                    }
                ],
            },
        ],
        "calculationValidation": {
            "formula": "scoreGlobalFinalEstimated = scoreGlobalInitial + sum(globalScoreGain)",
            "scoreGlobalInitial": initial,
            "totalGainFromBestPath": 1.01,
            "scoreGlobalFinalEstimated": 3.49,
            "scoreGlobalTarget": target,
            "targetReached": True,
        },
        "summary": {
            "optimizationLogic": "Combine domains",
            "selectedDomainsReason": "DQ and DG",
            "effortInterpretation": "Moderate effort",
            "finalValidation": "Target reached",
        },
        "warnings": [],
    }


def test_validate_best_path_accepts_valid_result():
    result = _valid_result()
    is_valid, errors, calculated = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is True
    assert errors == []
    assert calculated == pytest.approx(3.49, abs=0.02)


def test_validate_rejects_score_below_target():
    result = _valid_result()
    result["scoreGlobalFinalEstimated"] = 3.2
    result["targetReached"] = True
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any("scoreGlobalFinalEstimated" in error for error in errors)
    assert any("targetReached is true" in error for error in errors)


def test_validate_rejects_target_reached_false_when_score_met():
    result = _valid_result()
    result["targetReached"] = False
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any("targetReached must be true" in error for error in errors)


def test_validate_rejects_math_mismatch():
    result = _valid_result()
    result["scoreGlobalFinalEstimated"] = 4.0
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any("differs from calculatedFinalScore" in error for error in errors)


def test_validate_rejects_empty_best_path_when_target_not_reached():
    result = _valid_result()
    result["bestPath"] = []
    result["scoreGlobalFinalEstimated"] = 2.48
    result["targetReached"] = False
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any("bestPath must not be empty" in error for error in errors)


def test_validate_rejects_missing_domain_weight():
    result = _valid_result()
    del result["bestPath"][0]["domainWeight"]
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any("domainWeight" in error for error in errors)


def test_validate_rejects_missing_global_score_gain():
    result = _valid_result()
    del result["bestPath"][0]["globalScoreGain"]
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any("globalScoreGain" in error for error in errors)


def test_validate_rejects_missing_efficiency_ratio():
    result = _valid_result()
    del result["bestPath"][0]["efficiencyRatio"]
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any("efficiencyRatio" in error for error in errors)


def test_calculate_final_score_from_gains():
    result = _valid_result()
    calculated = calculate_final_score_from_gains(2.48, result["bestPath"])
    assert calculated == pytest.approx(3.49, abs=0.02)


def test_validate_rejects_incorrect_weighted_gain():
    from app.models.recommendation_models import NDIFramework

    framework = NDIFramework.model_validate(
        {
            "framework": "NDI",
            "total_domains": 2,
            "effort_scale": {"1": "Simple"},
            "domains": [
                {
                    "domain_id": "DG",
                    "domain_name": "Data Governance",
                    "weight": 11.75,
                    "questions": [
                        {
                            "id": "DG.MQ.2",
                            "text": "Politiques ?",
                            "effort_transitions": {
                                "0_to_1": {"effort": 1, "explanation": "a"},
                                "1_to_2": {"effort": 3, "explanation": "b"},
                                "2_to_3": {"effort": 3, "explanation": "c"},
                                "3_to_4": {"effort": 3, "explanation": "d"},
                                "4_to_5": {"effort": 3, "explanation": "e"},
                            },
                        }
                    ],
                },
                {
                    "domain_id": "DQ",
                    "domain_name": "Data Quality",
                    "weight": 11.93,
                    "questions": [
                        {
                            "id": "DQ.MQ.1",
                            "text": "Plan DQ ?",
                            "effort_transitions": {
                                "0_to_1": {"effort": 1, "explanation": "a"},
                                "1_to_2": {"effort": 3, "explanation": "b"},
                                "2_to_3": {"effort": 3, "explanation": "c"},
                                "3_to_4": {"effort": 3, "explanation": "d"},
                                "4_to_5": {"effort": 3, "explanation": "e"},
                            },
                        }
                    ],
                },
            ],
        }
    )

    result = _valid_result()
    result["bestPath"][0]["globalScoreGain"] = 0.01
    result["bestPath"][0]["domainWeight"] = 11.93

    is_valid, errors, _ = validate_best_path_result(
        result,
        target_score=3.48,
        score_global_initial=2.48,
        framework=framework,
        current_scores={"DG.MQ.2": 2, "DQ.MQ.1": 2},
    )
    assert is_valid is False
    assert any("globalScoreGain" in error for error in errors)


def test_validate_accepts_correct_weighted_gain():
    from app.models.recommendation_models import NDIFramework
    from app.services.score_calculator import compute_expected_global_gain

    framework = NDIFramework.model_validate(
        {
            "framework": "NDI",
            "total_domains": 2,
            "effort_scale": {"1": "Simple"},
            "domains": [
                {
                    "domain_id": "DG",
                    "domain_name": "Data Governance",
                    "weight": 11.75,
                    "questions": [
                        {
                            "id": "DG.MQ.2",
                            "text": "Politiques ?",
                            "effort_transitions": {
                                "0_to_1": {"effort": 1, "explanation": "a"},
                                "1_to_2": {"effort": 3, "explanation": "b"},
                                "2_to_3": {"effort": 3, "explanation": "c"},
                                "3_to_4": {"effort": 3, "explanation": "d"},
                                "4_to_5": {"effort": 3, "explanation": "e"},
                            },
                        }
                    ],
                },
                {
                    "domain_id": "DQ",
                    "domain_name": "Data Quality",
                    "weight": 11.93,
                    "questions": [
                        {
                            "id": "DQ.MQ.1",
                            "text": "Plan DQ ?",
                            "effort_transitions": {
                                "0_to_1": {"effort": 1, "explanation": "a"},
                                "1_to_2": {"effort": 3, "explanation": "b"},
                                "2_to_3": {"effort": 3, "explanation": "c"},
                                "3_to_4": {"effort": 3, "explanation": "d"},
                                "4_to_5": {"effort": 3, "explanation": "e"},
                            },
                        }
                    ],
                },
            ],
        }
    )
    current_scores = {"DG.MQ.2": 2, "DQ.MQ.1": 2}
    dq_gain = compute_expected_global_gain(
        framework, current_scores, "DQ", 2, 3
    )
    dg_gain = compute_expected_global_gain(
        framework, current_scores, "DG", 2, 3
    )

    result = {
        "success": True,
        "scoreGlobalInitial": 2.0,
        "scoreGlobalTarget": 3.0,
        "scoreGlobalFinalEstimated": round(2.0 + dq_gain + dg_gain, 2),
        "gainTotal": round(dq_gain + dg_gain, 2),
        "effortTotal": 10,
        "targetReached": True,
        "bestPath": [
            {
                "priority": 1,
                "domainId": "DQ",
                "domainName": "Data Quality",
                "domainWeight": 11.93,
                "currentDomainScore": 2,
                "targetDomainScore": 3,
                "domainScoreGain": 1,
                "globalScoreGain": dq_gain,
                "totalEffort": 6,
                "efficiencyRatio": 0.1,
                "questionsToImprove": [
                    {
                        "questionCode": "DQ.MQ.1",
                        "questionText": "Plan DQ ?",
                        "currentScore": 2,
                        "targetScore": 3,
                        "totalQuestionEffort": 6,
                        "transitions": [
                            {
                                "from": 2,
                                "to": 3,
                                "transitionKey": "2_to_3",
                                "effort": 6,
                                "explanation": "Bloquant",
                            }
                        ],
                        "recommendation": "Améliorer",
                    }
                ],
            },
            {
                "priority": 2,
                "domainId": "DG",
                "domainName": "Data Governance",
                "domainWeight": 11.75,
                "currentDomainScore": 2,
                "targetDomainScore": 3,
                "domainScoreGain": 1,
                "globalScoreGain": dg_gain,
                "totalEffort": 4,
                "efficiencyRatio": 0.1,
                "questionsToImprove": [
                    {
                        "questionCode": "DG.MQ.2",
                        "questionText": "Politiques ?",
                        "currentScore": 2,
                        "targetScore": 3,
                        "totalQuestionEffort": 4,
                        "transitions": [
                            {
                                "from": 2,
                                "to": 3,
                                "transitionKey": "2_to_3",
                                "effort": 4,
                                "explanation": "Bloquant",
                            }
                        ],
                        "recommendation": "Améliorer",
                    }
                ],
            },
        ],
        "calculationValidation": {
            "formula": "scoreGlobalFinalEstimated = scoreGlobalInitial + sum(globalScoreGain)",
            "scoreGlobalInitial": 2.0,
            "totalGainFromBestPath": round(dq_gain + dg_gain, 2),
            "scoreGlobalFinalEstimated": round(2.0 + dq_gain + dg_gain, 2),
            "scoreGlobalTarget": 3.0,
            "targetReached": True,
        },
        "summary": {
            "optimizationLogic": "Combine domains",
            "selectedDomainsReason": "DQ and DG",
            "effortInterpretation": "Moderate effort",
            "finalValidation": "Target reached",
        },
        "warnings": [],
    }

    is_valid, errors, _ = validate_best_path_result(
        result,
        target_score=3.0,
        score_global_initial=2.0,
        framework=framework,
        current_scores=current_scores,
    )
    assert is_valid is True, errors


def test_validate_rejects_short_global_score_gains_response():
    result = {
        "globalScoreGains": {"DC": 0.14, "FOI": 0.04},
        "gainTotal": 0.18,
        "calculatedFinalScore": 3.82,
    }
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any(
        "missing required fields scoreGlobalFinalEstimated and bestPath" in error
        for error in errors
    )


def test_validate_rejects_gain_total_mismatch():
    result = _valid_result()
    result["gainTotal"] = 0.5
    is_valid, errors, _ = validate_best_path_result(
        result, target_score=3.48, score_global_initial=2.48
    )
    assert is_valid is False
    assert any("gainTotal" in error and "globalScoreGain" in error for error in errors)
