import logging
from typing import Any

from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.framework_loader import FrameworkLoader
from app.services.optimizer import find_best_path
from app.services.response_validator import validate_best_path_result
from app.services.score_calculator import (
    compute_global_score,
    get_transition_explanations,
    round_score,
)

logger = logging.getLogger(__name__)


class BestPathOptimizerError(Exception):
    """Raised when the deterministic Best Path cannot be computed."""


class BestPathOptimizer:
    def __init__(self, framework_loader: FrameworkLoader | None = None) -> None:
        self.framework_loader = framework_loader or FrameworkLoader()

    def compute_best_path(
        self,
        framework: NDIFramework,
        request: BestPathRequest,
    ) -> dict[str, Any]:
        score_global_initial = (
            request.scoreGlobalActual
            if request.scoreGlobalActual is not None
            else compute_global_score(framework, request.currentScores)
        )

        raw_result = find_best_path(
            framework=framework,
            current_scores=request.currentScores,
            target_score=request.targetScore,
        )

        enriched = self._enrich_result(
            raw_result=raw_result,
            framework=framework,
            score_global_initial=score_global_initial,
            target_score=request.targetScore,
        )

        if enriched["bestPath"]:
            is_valid, errors, _ = validate_best_path_result(
                enriched,
                request.targetScore,
                score_global_initial=score_global_initial,
            )
            if not is_valid:
                logger.warning("Best path validation warnings after optimization: %s", errors)

        logger.info(
            "Deterministic best path | initial=%s | target=%s | final=%s | effort=%s | domains=%s",
            enriched["scoreGlobalInitial"],
            enriched["scoreGlobalTarget"],
            enriched["scoreGlobalFinalEstimated"],
            enriched["effortTotal"],
            len(enriched["bestPath"]),
        )

        return enriched

    def _enrich_result(
        self,
        *,
        raw_result: dict[str, Any],
        framework: NDIFramework,
        score_global_initial: float,
        target_score: float,
    ) -> dict[str, Any]:
        best_path: list[dict[str, Any]] = []
        priority = 1

        for domain_item in raw_result.get("bestPath", []):
            if not isinstance(domain_item, dict):
                continue

            current_domain_score = int(domain_item["currentDomainScore"])
            target_domain_score = int(domain_item["targetDomainScore"])
            questions: list[dict[str, Any]] = []

            for question_item in domain_item.get("questionsToImprove", []):
                if not isinstance(question_item, dict):
                    continue
                question_code = question_item["questionCode"]
                current_score = int(question_item["currentScore"])
                question_target = int(question_item["targetScore"])
                explanations = get_transition_explanations(
                    framework=framework,
                    question_id=question_code,
                    current_score=current_score,
                    target_score=question_target,
                )
                questions.append(
                    {
                        "questionCode": question_code,
                        "questionText": question_item["questionText"],
                        "currentScore": current_score,
                        "targetScore": question_target,
                        "effort": int(question_item["effort"]),
                        "explanation": " | ".join(explanations),
                        "recommendation": "",
                    }
                )

            total_effort = int(domain_item.get("totalEffort", sum(q["effort"] for q in questions)))
            global_gain = float(domain_item.get("globalScoreGain", 0.0))
            efficiency_ratio = (
                round_score(global_gain / total_effort, 4) if total_effort > 0 else 0.0
            )

            best_path.append(
                {
                    "priority": priority,
                    "domainId": domain_item["domainId"],
                    "domainName": domain_item["domainName"],
                    "domainWeight": float(domain_item["domainWeight"]),
                    "currentDomainScore": current_domain_score,
                    "targetDomainScore": target_domain_score,
                    "domainScoreGain": target_domain_score - current_domain_score,
                    "globalScoreGain": global_gain,
                    "totalEffort": total_effort,
                    "efficiencyRatio": efficiency_ratio,
                    "questionsToImprove": questions,
                }
            )
            priority += 1

        final_estimated = float(raw_result.get("scoreGlobalFinalEstimated", score_global_initial))
        gain_total = round_score(final_estimated - score_global_initial)
        effort_total = int(raw_result.get("effortTotal", sum(d["totalEffort"] for d in best_path)))
        target_reached = final_estimated >= target_score

        return {
            "scoreGlobalInitial": round_score(score_global_initial),
            "scoreGlobalTarget": round_score(target_score),
            "scoreGlobalFinalEstimated": round_score(final_estimated),
            "gainTotal": gain_total,
            "effortTotal": effort_total,
            "targetReached": target_reached,
            "bestPath": best_path,
            "calculationValidation": {
                "formula": "scoreGlobalFinalEstimated = scoreGlobalInitial + sum(globalScoreGain)",
                "scoreGlobalInitial": round_score(score_global_initial),
                "totalGainFromBestPath": gain_total,
                "scoreGlobalFinalEstimated": round_score(final_estimated),
                "scoreGlobalTarget": round_score(target_score),
                "targetReached": target_reached,
            },
            "warnings": [],
        }
