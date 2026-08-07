import logging
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

from app.core.config import settings
from app.models.recommendation_models import (
    BestPathRequest,
    BestPathResponse,
    GenerateReportRequest,
)
from app.services.best_path_pdf_generator import (
    BestPathPDFError,
    UnicodeFontNotFoundError,
    generate_best_path_pdf,
)
from app.services.best_path_response_formatter import format_best_path_response
from app.services.ai_recommendation_service import (
    AIRecommendationService,
    AIRecommendationServiceError,
)
from app.services.framework_loader import FrameworkLoader, FrameworkLoaderError
from app.services.score_code_normalizer import normalize_current_scores

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recommendations",
    tags=["recommendations"],
)

framework_loader = FrameworkLoader()
ai_service = AIRecommendationService()


def _prepare_request(request: BestPathRequest, framework) -> BestPathRequest:
    normalized_scores = normalize_current_scores(framework, request.currentScores)
    return request.model_copy(update={"currentScores": normalized_scores})


def _run_best_path(request: BestPathRequest) -> BestPathResponse:
    try:
        framework = framework_loader.load()
        logger.info("framework domains loaded=%s", len(framework.domains))
    except FrameworkLoaderError as exc:
        logger.exception("Framework loading failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    prepared = _prepare_request(request, framework)
    if not prepared.currentScores:
        raise HTTPException(
            status_code=400,
            detail=(
                "Aucun score NDI valide n'a été fourni. "
                "Vérifiez les codes questions (ex. DG.MQ.1 ou ndi_dg_01)."
            ),
        )

    try:
        result = ai_service.generate_best_path(framework=framework, request=prepared)
        logger.info(
            "Best path result success=%s | targetReached=%s",
            getattr(result, "success", None),
            getattr(result.status, "targetReached", None),
        )
        return result
    except AIRecommendationServiceError as exc:
        logger.exception("AI recommendation service failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (TypeError, AttributeError) as exc:
        logger.exception("Best path route failed with pipeline error")
        return format_best_path_response(
            {
                "success": False,
                "scoreGlobalInitial": prepared.scoreGlobalActual or 0.0,
                "scoreGlobalTarget": prepared.targetScore,
                "scoreGlobalFinalEstimated": prepared.scoreGlobalActual or 0.0,
                "gainTotal": 0.0,
                "effortTotal": 0,
                "overGain": 0.0,
                "targetReached": False,
                "bestPath": [],
                "warnings": [f"Best Path pipeline error: {exc}"],
                "failureMeta": {
                    "insufficient_selection": False,
                    "auto_complete_disabled": not settings.AUTO_COMPLETE_BEST_PATH,
                },
            }
        )


@router.post(
    "/best-path",
    response_model=BestPathResponse,
    summary=(
        "Calculer le Best Path via l'optimiseur déterministe du backend, "
        "puis enrichir les explications via le LLM si activé."
    ),
)
def compute_best_path(
    request: BestPathRequest,
) -> BestPathResponse:
    logger.info("POST /api/recommendations/best-path received")
    logger.info("targetScore=%s | currentScores count=%s", request.targetScore, len(request.currentScores))
    logger.info("USE_OLLAMA=%s | model=%s", settings.USE_OLLAMA, settings.OLLAMA_MODEL)
    return _run_best_path(request)


@router.post(
    "/generate-report",
    summary="Calculer le Best Path et retourner le rapport PDF.",
    response_class=Response,
)
def generate_recommendation_report(
    request: GenerateReportRequest = Body(...),
) -> Response:
    logger.info("POST /api/recommendations/generate-report received")
    logger.info(
        "targetScore=%s | currentScores count=%s | scoreGlobalActual=%s",
        request.targetScore,
        len(request.currentScores or {}),
        request.scoreGlobalActual,
    )

    result = _run_best_path(request)
    report = result.model_dump(by_alias=True)
    report["framework"] = (request.framework or "NDI").strip() or "NDI"
    report["generationDate"] = (
        request.generationDate
        or datetime.now().strftime("%d/%m/%Y %H:%M")
    )
    if request.projectName:
        report["projectName"] = request.projectName
    if request.clientName:
        report["clientName"] = request.clientName
    if request.versionNumber is not None:
        report["versionNumber"] = request.versionNumber
    if request.submittedAt:
        report["submittedAt"] = request.submittedAt

    try:
        pdf_bytes = generate_best_path_pdf(report)
    except UnicodeFontNotFoundError as exc:
        logger.exception("PDF font unavailable")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except BestPathPDFError as exc:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=500,
            detail="La génération du rapport PDF a produit un fichier invalide.",
        )

    filename = "rapport-recommandations.pdf"
    project_slug = "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "-"
        for ch in (request.projectName or "projet").strip()
    ).strip("-") or "projet"
    version_part = (
        f"-version-{request.versionNumber}"
        if request.versionNumber is not None
        else ""
    )
    filename = f"rapport-recommandations-{project_slug}{version_part}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
