import json
from pathlib import Path

from app.models.recommendation_models import NDIFramework
from app.services.framework_map import build_framework_map, compute_current_domain_score
from app.services.response_validator import (
    normalize_best_path_result,
    rebuild_best_path_from_llm_selection,
    validate_best_path_result,
)


def _framework() -> NDIFramework:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "ndi_framework.json"
    framework_raw = json.loads(path.read_text(encoding="utf-8"))
    return NDIFramework.model_validate(framework_raw), framework_raw


def _slim_llm_selection() -> dict:
    return {
        "bestPath": [
            {
                "priority": 1,
                "domainId": "DC",
                "targetDomainScore": 3,
                "questionsToImprove": [
                    {
                        "questionCode": "DC.MQ.1",
                        "targetScore": 3,
                        "recommendation": "Renforcer le plan de classification.",
                    }
                ],
            }
        ],
        "professionalAnalysis": {
            "executiveSummary": "Résumé",
            "bestPathExplanation": "Explication",
            "detailedActionPlan": "Plan",
            "finalValidation": "Validation",
            "strategicConclusion": "Conclusion",
        },
        "warnings": [],
    }


def test_framework_map_contains_official_dc_metadata():
    framework, framework_raw = _framework()
    framework_map = build_framework_map(framework_raw)
    assert framework_map["DC"]["domainName"] == "Data Classification"
    assert framework_map["DC"]["weight"] == 6.84
    assert "DC.MQ.1" in framework_map["DC"]["questions"]


def test_current_domain_score_is_min_of_answered_questions():
    framework, _ = _framework()
    current_scores = {"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4}
    assert (
        compute_current_domain_score(framework, "DC", current_scores) == 2
    )


def test_validator_rejects_hallucinated_question_code():
    framework, _ = _framework()
    result = _slim_llm_selection()
    result["bestPath"][0]["questionsToImprove"][0]["questionCode"] = "DC.CA.2"

    _, errors = normalize_best_path_result(
        result=result,
        framework=framework,
        current_scores={"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4},
        score_global_initial=2.48,
        target_score=2.6,
    )

    assert any("DC.CA.2 does not exist in NDI framework" in error for error in errors)


def test_validator_rejects_decimal_effort_from_llm():
    framework, _ = _framework()
    result = _slim_llm_selection()
    result["bestPath"][0]["questionsToImprove"][0]["effort"] = 5.96

    _, errors = normalize_best_path_result(
        result=result,
        framework=framework,
        current_scores={"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4},
        score_global_initial=2.48,
        target_score=2.6,
    )

    assert any("cannot be a decimal" in error for error in errors)


def test_backend_rebuilds_official_numeric_fields():
    framework, _ = _framework()
    current_scores = {"DC.MQ.1": 2, "DC.MQ.2": 2, "DC.MQ.3": 4}

    llm_result = {
        "bestPath": [
            {
                "priority": 1,
                "domainId": "DC",
                "domainName": "Data Collection",
                "domainWeight": 11.93,
                "currentDomainScore": 3,
                "targetDomainScore": 3,
                "globalScoreGain": 0.773,
                "questionsToImprove": [
                    {
                        "questionCode": "DC.MQ.1",
                        "questionText": "Invented text",
                        "targetScore": 3,
                        "effort": 5.96,
                        "explanation": "Invented explanation",
                        "recommendation": "Corriger DC.MQ.1",
                    }
                ],
            }
        ],
        "professionalAnalysis": {},
        "warnings": [],
    }

    rebuilt = rebuild_best_path_from_llm_selection(
        result=llm_result,
        framework=framework,
        current_scores=current_scores,
        score_global_initial=2.48,
        target_score=2.6,
    )

    domain = rebuilt["bestPath"][0]
    assert domain["domainName"] == "Data Classification"
    assert domain["domainWeight"] == 6.84
    assert domain["currentDomainScore"] == 2
    assert domain["globalScoreGain"] != 0.773
    assert domain["questionsToImprove"][0]["effort"] == 3
    assert domain["questionsToImprove"][0]["questionText"].startswith("Has the entity established")
    assert rebuilt["scoreGlobalFinalEstimated"] == round(2.48 + rebuilt["gainTotal"], 2)


def test_backend_rebuilt_response_passes_validation_when_target_reached():
    framework, _ = _framework()
    current_scores = {
        "DG.MQ.1": 3,
        "DG.MQ.2": 2,
        "DQ.MQ.1": 2,
        "DQ.MQ.2": 2,
        "DQ.MQ.3": 3,
        "DQ.MQ.4": 1,
    }

    llm_result = {
        "bestPath": [
            {
                "priority": 1,
                "domainId": "DQ",
                "targetDomainScore": 3,
                "questionsToImprove": [
                    {
                        "questionCode": "DQ.MQ.4",
                        "targetScore": 3,
                        "recommendation": "Améliorer DQ.MQ.4",
                    }
                ],
            },
            {
                "priority": 2,
                "domainId": "DG",
                "targetDomainScore": 3,
                "questionsToImprove": [
                    {
                        "questionCode": "DG.MQ.2",
                        "targetScore": 3,
                        "recommendation": "Améliorer DG.MQ.2",
                    }
                ],
            },
        ],
        "professionalAnalysis": {},
        "warnings": [],
    }

    rebuilt, errors = normalize_best_path_result(
        result=llm_result,
        framework=framework,
        current_scores=current_scores,
        score_global_initial=2.48,
        target_score=2.6,
    )
    assert errors == []

    is_valid, validation_errors, _ = validate_best_path_result(
        rebuilt,
        target_score=2.6,
        score_global_initial=2.48,
    )
    assert is_valid is True, validation_errors
