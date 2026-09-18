import logging
from typing import Any

from app.core.config import settings
from app.core.prompts import load_system_prompt
from app.models.recommendation_models import (
    BestPathRequest,
    BestPathResponse,
    NDIFramework,
)
from app.services.best_path_response_formatter import format_best_path_response
from app.services.candidate_action_builder import save_candidate_actions_debug, save_allowed_action_ids_debug, build_candidate_actions
from app.services.exact_path_optimizer import (
    OptimizationInputError,
    OptimizationValidationError,
    optimize_best_path,
)
from app.services.explanation_merger import (
    apply_framework_explanations,
    merge_llm_explanations,
    normalize_explanation_response,
)
from app.services.grounded_recommendation import apply_grounded_recommendations
from app.services.explanation_prompt_builder import build_explanation_user_prompt
from app.services.framework_loader import FrameworkLoader
from app.services.llm_response_parser import LLMResponseParseError, parse_llm_json
from app.services.ollama_service import OllamaService, OllamaServiceError
from app.services.score_calculator import compute_global_score, compute_total_framework_weight, round_score

logger = logging.getLogger(__name__)

LLM_EXPLANATION_FAILURE_WARNING = (
    "LLM explanation enrichment failed; framework transition explanations were used instead."
)


class AIRecommendationServiceError(Exception):
    """Raised when the recommendation pipeline fails."""


class AIRecommendationService:
    def __init__(
        self,
        api_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        framework_loader: FrameworkLoader | None = None,
        ollama_service: OllamaService | None = None,
    ) -> None:
        self.framework_loader = framework_loader or FrameworkLoader()
        self.ollama_service = ollama_service or OllamaService(
            api_url=api_url,
            model=model,
            timeout_seconds=timeout_seconds,
        )

    def generate_best_path(
        self,
        framework: NDIFramework,
        request: BestPathRequest,
    ) -> BestPathResponse:
        score_global_initial = (
            request.scoreGlobalActual
            if request.scoreGlobalActual is not None
            else compute_global_score(framework, request.currentScores)
        )
        total_weights = request.totalWeights or compute_total_framework_weight(framework)
        candidate_actions, _ = build_candidate_actions(
            framework=framework,
            current_scores=request.currentScores,
            total_weights=total_weights,
        )
        save_candidate_actions_debug(
            score_global_actual=score_global_initial,
            target_score=request.targetScore,
            candidate_actions=candidate_actions,
        )
        save_allowed_action_ids_debug(
            score_global_actual=score_global_initial,
            target_score=request.targetScore,
            candidate_actions=candidate_actions,
        )

        try:
            validated = optimize_best_path(
                framework=framework,
                current_scores=request.currentScores,
                target_score=request.targetScore,
            )
        except OptimizationInputError as exc:
            raise AIRecommendationServiceError(str(exc)) from exc
        except OptimizationValidationError as exc:
            raise AIRecommendationServiceError(f"Best Path validation failed: {exc}") from exc

        validated = apply_grounded_recommendations(validated)

        if settings.USE_OLLAMA:
            validated = self._enrich_with_llm_explanations(validated)
        else:
            validated = apply_framework_explanations(validated)

        return format_best_path_response(validated)

    def _enrich_with_llm_explanations(self, validated_path: dict[str, Any]) -> dict[str, Any]:
        if not validated_path.get("bestPath"):
            return validated_path

        system_prompt = load_system_prompt()
        user_prompt = build_explanation_user_prompt(validated_path)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            raw_response = self.ollama_service._call_ollama(messages)
            parsed = normalize_explanation_response(parse_llm_json(raw_response))
            return merge_llm_explanations(validated_path, parsed)
        except (OllamaServiceError, LLMResponseParseError, TypeError, ValueError, RuntimeError) as exc:
            logger.warning("LLM explanation enrichment failed: %s", exc)

        fallback = apply_framework_explanations(validated_path)
        warnings = list(fallback.get("warnings", []))
        warnings.append(LLM_EXPLANATION_FAILURE_WARNING)
        fallback["warnings"] = warnings
        return fallback

    def _format_internal_result(self, result: dict[str, Any]) -> BestPathResponse:
        return format_best_path_response(result)
