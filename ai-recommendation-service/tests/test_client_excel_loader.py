import json
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.models.recommendation_models import NDIFramework
from app.services.client_excel_loader import (
    build_client_assessment_payload,
    build_legacy_question_code_map,
    normalize_question_code,
    parse_client_scores_from_excel,
)
from app.services.score_calculator import compute_global_score


@pytest.fixture
def framework() -> NDIFramework:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "ndi_framework.json"
    return NDIFramework.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_normalize_question_code_supports_framework_and_legacy_codes(framework):
    legacy_map = build_legacy_question_code_map(framework)
    assert normalize_question_code("DG.MQ.1", framework) == "DG.MQ.1"
    assert normalize_question_code("ndi_dg_01", framework, legacy_map) == "DG.MQ.1"


def test_parse_long_format_excel(framework):
    dataframe = pd.DataFrame(
        {
            "questionCode": ["DG.MQ.1", "DG.MQ.2", "DQ.MQ.1"],
            "score": [4, 3, 2],
        }
    )
    buffer = BytesIO()
    dataframe.to_excel(buffer, index=False)
    scores = parse_client_scores_from_excel(buffer.getvalue(), framework)
    assert scores == {"DG.MQ.1": 4, "DG.MQ.2": 3, "DQ.MQ.1": 2}


def test_build_client_assessment_payload_matches_backend_formula(framework):
    current_scores = {"DG.MQ.1": 4, "DG.MQ.2": 3, "DG.MQ.3": 4, "DG.MQ.4": 3}
    payload = build_client_assessment_payload(framework, current_scores)
    assert payload["scoreGlobalActual"] == compute_global_score(framework, current_scores)
    assert payload["domainScores"]["DG"] == 3
    assert payload["currentScores"] == current_scores
    assert payload["totalWeights"] > 0
