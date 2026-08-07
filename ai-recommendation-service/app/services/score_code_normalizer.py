"""Normalize backend / Excel question codes to NDI knowledge-base IDs."""

from __future__ import annotations

from app.models.recommendation_models import NDIFramework
from app.services.client_excel_loader import (
    build_legacy_question_code_map,
    normalize_question_code,
)


def normalize_current_scores(
    framework: NDIFramework,
    current_scores: dict[str, int],
) -> dict[str, int]:
    """Map legacy codes such as ``ndi_dg_01`` to ``DG.MQ.1`` when needed."""
    if not current_scores:
        return {}

    legacy_map = build_legacy_question_code_map(framework)
    normalized: dict[str, int] = {}
    for raw_code, score in current_scores.items():
        mapped = normalize_question_code(str(raw_code), framework, legacy_map)
        if mapped is None:
            continue
        try:
            value = int(score)
        except (TypeError, ValueError):
            continue
        if 0 <= value <= 5:
            normalized[mapped] = value
    return normalized
