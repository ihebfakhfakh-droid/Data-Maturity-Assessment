import logging
from typing import Any

from app.models.recommendation_models import NDIFramework
from app.services.score_calculator import (
    compute_expected_global_gain,
    round_score,
)

logger = logging.getLogger(__name__)

REQUIRED_TOP_LEVEL_FIELDS = (
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

REQUIRED_DOMAIN_FIELDS = (
    "priority",
    "domainId",
    "domainName",
    "domainWeight",
    "currentDomainScore",
    "targetDomainScore",
    "domainScoreGain",
    "globalScoreGain",
    "totalEffort",
    "efficiencyRatio",
    "questionsToImprove",
)

REQUIRED_QUESTION_FIELDS = (
    "questionCode",
    "questionText",
    "currentScore",
    "targetScore",
    "totalQuestionEffort",
    "transitions",
    "recommendation",
)

SUMMARY_REQUIRED_FIELDS = (
    "optimizationLogic",
    "selectedDomainsReason",
    "effortInterpretation",
    "finalValidation",
)

SCORE_TOLERANCE = 0.02
WEIGHT_TOLERANCE = 0.01


class BestPathValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def calculate_final_score_from_gains(
    score_global_initial: float, best_path: list[dict[str, Any]]
) -> float:
    gain_sum = sum(float(item.get("globalScoreGain", 0)) for item in best_path)
    return round_score(score_global_initial + gain_sum)


def calculate_gain_total_from_best_path(best_path: list[dict[str, Any]]) -> float:
    return round_score(sum(float(item.get("globalScoreGain", 0)) for item in best_path))


def _is_short_invalid_response(result: dict[str, Any]) -> bool:
    has_global_score_gains_only = (
        "globalScoreGains" in result
        and "bestPath" not in result
        and "scoreGlobalFinalEstimated" not in result
    )
    has_calculated_final_only = (
        "calculatedFinalScore" in result
        and "scoreGlobalFinalEstimated" not in result
        and "bestPath" not in result
    )
    return has_global_score_gains_only or has_calculated_final_only


def _validate_required_schema(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if _is_short_invalid_response(result):
        errors.append(
            "Invalid LLM response: missing required fields scoreGlobalFinalEstimated "
            "and bestPath, and inconsistent final score calculation."
        )
        return errors

    missing_fields = [
        field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in result
    ]
    if missing_fields:
        errors.append(
            "Invalid LLM response: missing required fields "
            + ", ".join(missing_fields)
        )

    if "professionalAnalysis" in result:
        errors.append(
            "Invalid LLM response: professionalAnalysis is deprecated; use summary instead."
        )

    if "summary" in result and isinstance(result.get("summary"), str):
        errors.append("summary must be an object, not a string.")

    if "globalScoreGains" in result and "bestPath" not in result:
        errors.append(
            "Invalid LLM response: globalScoreGains without detailed bestPath is forbidden"
        )

    return errors


def _validate_domain_weights_and_gains(
    best_path: list[dict[str, Any]],
    framework: NDIFramework,
    current_scores: dict[str, int],
) -> list[str]:
    errors: list[str] = []
    domain_weights = {domain.domain_id: domain.weight for domain in framework.domains}

    if not domain_weights:
        errors.append("NDI framework contains no domain weights")
        return errors

    if sum(domain_weights.values()) <= 0:
        errors.append("NDI framework domain weights sum must be greater than 0")

    for index, domain_item in enumerate(best_path):
        if not isinstance(domain_item, dict):
            continue

        domain_id = domain_item.get("domainId")
        if not isinstance(domain_id, str) or domain_id not in domain_weights:
            errors.append(
                f"bestPath[{index}] uses unknown or missing domainId '{domain_id}'"
            )
            continue

        if "domainWeight" not in domain_item:
            errors.append(
                f"bestPath[{index}] is missing mandatory field 'domainWeight'"
            )
        elif domain_item.get("domainWeight") in (None, ""):
            errors.append(
                f"bestPath[{index}].domainWeight is empty; weighted gain proof is required"
            )

        if "globalScoreGain" not in domain_item:
            errors.append(
                f"bestPath[{index}] is missing mandatory field 'globalScoreGain'"
            )
        elif domain_item.get("globalScoreGain") in (None, ""):
            errors.append(
                f"bestPath[{index}].globalScoreGain is empty; weighted gain proof is required"
            )

        if "efficiencyRatio" not in domain_item:
            errors.append(
                f"bestPath[{index}] is missing mandatory field 'efficiencyRatio'"
            )
        elif domain_item.get("efficiencyRatio") in (None, ""):
            errors.append(
                f"bestPath[{index}].efficiencyRatio is empty"
            )

        expected_weight = domain_weights[domain_id]
        try:
            declared_weight = float(domain_item.get("domainWeight", 0))
        except (TypeError, ValueError):
            errors.append(f"bestPath[{index}].domainWeight is not a valid number")
            continue

        if declared_weight <= 0:
            errors.append(
                f"bestPath[{index}].domainWeight must be greater than 0 "
                "(domain weights are mandatory)"
            )

        if abs(declared_weight - expected_weight) > WEIGHT_TOLERANCE:
            errors.append(
                f"bestPath[{index}].domainWeight ({declared_weight}) does not match "
                f"NDI framework weight ({expected_weight})"
            )

        try:
            current_domain_score = int(domain_item["currentDomainScore"])
            target_domain_score = int(domain_item["targetDomainScore"])
            declared_gain = float(domain_item["globalScoreGain"])
        except (KeyError, TypeError, ValueError):
            errors.append(
                f"bestPath[{index}] has invalid domain scores or globalScoreGain"
            )
            continue

        expected_gain = compute_expected_global_gain(
            framework=framework,
            current_scores=current_scores,
            domain_id=domain_id,
            current_domain_score=current_domain_score,
            target_domain_score=target_domain_score,
        )

        if abs(declared_gain - expected_gain) > SCORE_TOLERANCE:
            errors.append(
                f"bestPath[{index}].globalScoreGain ({declared_gain}) does not match "
                f"weighted formula ({expected_gain}) using domain weight "
                f"{expected_weight}"
            )

    return errors


def validate_best_path_result(
    result: dict[str, Any],
    target_score: float,
    *,
    score_global_initial: float | None = None,
    require_non_empty_path: bool | None = None,
    framework: NDIFramework | None = None,
    current_scores: dict[str, int] | None = None,
) -> tuple[bool, list[str], float | None]:
    errors = _validate_required_schema(result)

    if "scoreGlobalFinalEstimated" not in result:
        if not any("scoreGlobalFinalEstimated" in error for error in errors):
            errors.append("scoreGlobalFinalEstimated is missing")
        final_estimated: float | None = None
    else:
        try:
            final_estimated = float(result["scoreGlobalFinalEstimated"])
        except (TypeError, ValueError):
            errors.append("scoreGlobalFinalEstimated is not a valid number")
            final_estimated = None

    if "bestPath" not in result:
        if not any("bestPath" in error for error in errors):
            errors.append("bestPath is missing")
        best_path: list[dict[str, Any]] = []
    elif not isinstance(result.get("bestPath"), list):
        errors.append("bestPath must be a list")
        best_path = []
    else:
        best_path = result["bestPath"]

    if not best_path:
        errors.append("bestPath must not be empty")

    if "effortTotal" not in result:
        errors.append("effortTotal is missing")

    if "gainTotal" not in result:
        errors.append("gainTotal is missing")

    initial = score_global_initial
    if initial is None and "scoreGlobalInitial" in result:
        try:
            initial = float(result["scoreGlobalInitial"])
        except (TypeError, ValueError):
            errors.append("scoreGlobalInitial is not a valid number")

    declared_gain_total: float | None = None
    if "gainTotal" in result:
        try:
            declared_gain_total = float(result["gainTotal"])
        except (TypeError, ValueError):
            errors.append("gainTotal is not a valid number")

    gain_total_from_path = calculate_gain_total_from_best_path(best_path)
    if declared_gain_total is not None and abs(declared_gain_total - gain_total_from_path) > SCORE_TOLERANCE:
        errors.append(
            f"gainTotal ({declared_gain_total}) does not match sum of globalScoreGain "
            f"in bestPath ({gain_total_from_path})"
        )

    if "effortTotal" in result:
        try:
            declared_effort_total = int(result["effortTotal"])
            expected_effort_total = sum(int(item.get("totalEffort", 0)) for item in best_path)
            if declared_effort_total != expected_effort_total:
                errors.append(
                    f"effortTotal ({declared_effort_total}) does not match sum of totalEffort "
                    f"in bestPath ({expected_effort_total})"
                )
        except (TypeError, ValueError):
            errors.append("effortTotal is not a valid integer")

    target_reached = result.get("targetReached")
    if final_estimated is not None and final_estimated < target_score:
        errors.append(
            f"scoreGlobalFinalEstimated ({final_estimated}) < targetScore ({target_score})"
        )

    if target_reached is True and final_estimated is not None and final_estimated < target_score:
        errors.append(
            "targetReached is true but scoreGlobalFinalEstimated is below targetScore"
        )

    if target_reached is not True and final_estimated is not None and final_estimated >= target_score:
        errors.append(
            "targetReached must be true when scoreGlobalFinalEstimated >= scoreGlobalTarget"
        )

    needs_improvements = (
        require_non_empty_path
        if require_non_empty_path is not None
        else initial is not None and initial < target_score
    )
    if needs_improvements and not best_path:
        errors.append("bestPath must not be empty when target score is not yet reached")

    for index, domain_item in enumerate(best_path):
        if not isinstance(domain_item, dict):
            errors.append(f"bestPath[{index}] must be an object")
            continue

        if "domainWeight" not in domain_item:
            errors.append(
                f"bestPath[{index}] is missing mandatory field 'domainWeight'"
            )
        if "globalScoreGain" not in domain_item:
            errors.append(
                f"bestPath[{index}] is missing mandatory field 'globalScoreGain'"
            )
        if "efficiencyRatio" not in domain_item:
            errors.append(
                f"bestPath[{index}] is missing mandatory field 'efficiencyRatio'"
            )

        for field in REQUIRED_DOMAIN_FIELDS:
            if field not in domain_item:
                errors.append(f"bestPath[{index}] is missing required field '{field}'")
        questions = domain_item.get("questionsToImprove", [])
        if not isinstance(questions, list) or not questions:
            errors.append(f"bestPath[{index}].questionsToImprove must be a non-empty list")
            continue
        for q_index, question in enumerate(questions):
            if not isinstance(question, dict):
                errors.append(
                    f"bestPath[{index}].questionsToImprove[{q_index}] must be an object"
                )
                continue
            for field in REQUIRED_QUESTION_FIELDS:
                if field not in question:
                    errors.append(
                        f"bestPath[{index}].questionsToImprove[{q_index}] "
                        f"is missing required field '{field}'"
                    )

    if framework is not None and current_scores is not None and best_path:
        errors.extend(
            _validate_domain_weights_and_gains(
                best_path=best_path,
                framework=framework,
                current_scores=current_scores,
            )
        )

    calculated_final: float | None = None
    if initial is not None:
        calculated_final = calculate_final_score_from_gains(initial, best_path)
        if calculated_final < target_score:
            errors.append(
                f"calculatedFinalScore ({calculated_final}) < targetScore ({target_score})"
            )
        if final_estimated is not None and abs(calculated_final - final_estimated) > SCORE_TOLERANCE:
            errors.append(
                "scoreGlobalFinalEstimated ("
                f"{final_estimated}) differs from calculatedFinalScore ({calculated_final})"
            )

        expected_final_from_gain_total = round_score(initial + gain_total_from_path)
        if final_estimated is not None and abs(expected_final_from_gain_total - final_estimated) > SCORE_TOLERANCE:
            errors.append(
                "scoreGlobalFinalEstimated ("
                f"{final_estimated}) is inconsistent with scoreGlobalInitial + gainTotal "
                f"({expected_final_from_gain_total})"
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
