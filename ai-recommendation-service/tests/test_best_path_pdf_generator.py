import json
from pathlib import Path

import pytest

from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.best_path_pdf_generator import (
    BestPathPDFError,
    UnicodeFontNotFoundError,
    generate_best_path_pdf,
)
from app.services.best_path_response_formatter import format_best_path_response
from app.services.candidate_action_builder import (
    build_candidate_actions,
    find_minimum_overgain_selection_ids,
    rebuild_best_path_from_selection,
)


@pytest.fixture
def framework() -> NDIFramework:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "ndi_framework.json"
    return NDIFramework.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _sample_scores() -> dict[str, int]:
    return {
        "DQ.MQ.1": 1, "DQ.MQ.2": 1, "DQ.MQ.3": 1, "DQ.MQ.4": 1,
        "DG.MQ.1": 2, "DG.MQ.2": 2, "DG.MQ.3": 2, "DG.MQ.4": 2,
        "RMD.MQ.1": 1, "RMD.MQ.2": 1, "RMD.MQ.3": 1, "RMD.MQ.4": 1,
        "MCM.MQ.1": 4, "MCM.MQ.2": 4, "MCM.MQ.3": 4, "MCM.MQ.4": 4,
        "PDP.MQ.1": 3, "PDP.MQ.2": 3, "PDP.MQ.3": 3, "PDP.MQ.4": 4,
        "DSI.MQ.1": 2, "DSI.MQ.2": 2, "DSI.MQ.3": 2, "DSI.MQ.4": 2,
        "OD.MQ.1": 4, "OD.MQ.2": 4, "OD.MQ.3": 4, "OD.MQ.4": 4,
        "DAM.MQ.1": 2, "DAM.MQ.2": 2, "DAM.MQ.3": 2, "DAM.MQ.4": 2,
        "DVR.MQ.1": 2, "DVR.MQ.2": 2, "DVR.MQ.3": 2, "DVR.MQ.4": 2,
    }


def _build_sample_report(framework: NDIFramework) -> dict:
    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores=_sample_scores(),
    )
    actions, actions_by_id = build_candidate_actions(framework, request.currentScores)
    minimum = find_minimum_overgain_selection_ids(actions, target_gap=1.0)
    assert minimum is not None
    selected_ids, _, _, _ = minimum
    rebuilt = rebuild_best_path_from_selection(
        selected_ids,
        actions_by_id,
        score_global_initial=2.48,
        target_score=3.48,
        candidate_actions=actions,
    )
    rebuilt["success"] = True
    response = format_best_path_response(rebuilt)
    report = response.model_dump()
    report["framework"] = framework.framework
    report["generationDate"] = "13/07/2026 17:00"
    return report


def test_generate_best_path_pdf_returns_valid_pdf_bytes(framework):
    report = _build_sample_report(framework)
    pdf_bytes = generate_best_path_pdf(report)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 5000


def test_generate_best_path_pdf_handles_missing_sections():
    minimal_report = {
        "success": True,
        "status": {"targetReached": True, "message": "OK"},
        "scoreSummary": {
            "scoreGlobalInitial": 2.0,
            "scoreGlobalTarget": 3.0,
            "targetGap": 1.0,
            "gainTotal": 1.0,
            "scoreGlobalFinalEstimated": 3.0,
            "overGain": 0.0,
            "effortTotal": 10,
        },
        "optimizationSummary": {
            "strategy": "Test",
            "selectedDomainsCount": 0,
            "selectedQuestionsCount": 0,
            "whyThisPath": "Test path",
            "effortExplanation": "Test effort",
        },
        "bestPathTable": [],
        "detailedActions": [],
        "mathematicalValidation": {
            "formula": "scoreGlobalFinalEstimated = scoreGlobalInitial + gainTotal",
            "calculation": "2.0 + 1.0 = 3.0 >= target 3.0",
            "targetReached": True,
        },
        "warnings": [],
    }

    pdf_bytes = generate_best_path_pdf(minimal_report)
    assert pdf_bytes.startswith(b"%PDF")


def test_generate_best_path_pdf_rejects_invalid_report():
    with pytest.raises(BestPathPDFError):
        generate_best_path_pdf([])  # type: ignore[arg-type]


def test_generate_best_path_pdf_omits_warnings_section():
    """warnings stay in the JSON payload for validation; the PDF must still generate without a warnings section."""
    report = {
        "success": False,
        "status": {"targetReached": False, "message": "Failed"},
        "scoreSummary": {
            "scoreGlobalInitial": 2.0,
            "scoreGlobalTarget": 3.0,
            "targetGap": 1.0,
            "gainTotal": 0.5,
            "scoreGlobalFinalEstimated": 2.5,
            "overGain": 0.0,
            "effortTotal": 5,
        },
        "optimizationSummary": {
            "strategy": "Test",
            "selectedDomainsCount": 1,
            "selectedQuestionsCount": 1,
            "whyThisPath": "Chemin partiel",
            "effortExplanation": "Effort partiel",
        },
        "bestPathTable": [],
        "detailedActions": [],
        "mathematicalValidation": {
            "formula": "scoreGlobalFinalEstimated = scoreGlobalInitial + gainTotal",
            "calculation": "2.0 + 0.5 = 2.5 < target 3.0",
            "targetReached": False,
        },
        "warnings": ["Avertissement avec accents : élévation ≥ 3 → 4, Σ total"],
    }

    pdf_bytes = generate_best_path_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")
    assert "warnings" in report
    # Source-level guarantee: generator must not append a warnings section.
    from app.services import best_path_pdf_generator as pdf_mod
    source = Path(pdf_mod.__file__).read_text(encoding="utf-8")
    assert "G. Avertissements" not in source
    assert "Aucun avertissement" not in source
